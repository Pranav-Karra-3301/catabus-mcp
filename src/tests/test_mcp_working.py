"""Working FastMCP tests with proper result handling."""

import pytest
import asyncio
from unittest.mock import patch, Mock
from datetime import datetime, timezone

from fastmcp import Client
from catabus_mcp.server import mcp
from catabus_mcp.ingest.static_loader import GTFSData, Route, Stop
from catabus_mcp.ingest.realtime_poll import RealtimeData, VehiclePosition


def extract_result(result):
    """Extract actual data from FastMCP CallToolResult."""
    import json
    
    if hasattr(result, 'content'):
        content = result.content
        # Handle list of TextContent objects
        if isinstance(content, list) and len(content) > 0:
            text_content = content[0]
            if hasattr(text_content, 'text'):
                try:
                    return json.loads(text_content.text)
                except json.JSONDecodeError:
                    return text_content.text
            return text_content
        return content
    elif hasattr(result, 'data'):
        return result.data  
    else:
        return result


@pytest.fixture
def mock_gtfs_data():
    """Create test GTFS data."""
    data = GTFSData()
    
    data.routes = {
        "BL": Route("BL", "BL", "Blue Loop", 3, "0000FF"),
        "WL": Route("WL", "WL", "White Loop", 3, "FFFFFF"),  
        "N": Route("N", "N", "Campus Loop North", 3, "00FF00")
    }
    
    data.stops = {
        "HUB": Stop("HUB", "HUB-Robeson Center", 40.7982, -77.8599),
        "CURTIN": Stop("CURTIN", "Curtin Rd at BJC", 40.8123, -77.8456)
    }
    
    data.last_updated = datetime.now(timezone.utc)
    return data


@pytest.fixture  
def mock_realtime_data():
    """Create test realtime data."""
    data = RealtimeData()
    
    data.vehicle_positions["BUS_001"] = VehiclePosition(
        vehicle_id="BUS_001",
        route_id="BL",
        latitude=40.7982,
        longitude=-77.8599,
        bearing=90.0,
        speed=10.5,
        timestamp=datetime.now(timezone.utc)
    )
    
    return data


class TestMCPBasicFunctionality:
    """Basic MCP server functionality tests."""
    
    @pytest.mark.asyncio
    async def test_server_connects(self):
        """Test server connection and tool listing."""
        client = Client(mcp)
        async with client:
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]
            
            expected = ["list_routes_tool", "search_stops_tool", "next_arrivals_tool", 
                       "vehicle_positions_tool", "trip_alerts_tool", "health_check"]
            
            for tool in expected:
                assert tool in tool_names
    
    @pytest.mark.asyncio
    async def test_list_routes_with_mocked_data(self, mock_gtfs_data):
        """Test list routes with mocked data."""
        with patch('catabus_mcp.server_v2.gtfs_data', mock_gtfs_data):
            with patch('catabus_mcp.server_v2.initialized', True):
                client = Client(mcp)
                async with client:
                    result = await client.call_tool("list_routes_tool", {})
                    routes = extract_result(result)
                    
                    assert isinstance(routes, list)
                    assert len(routes) == 3
                    
                    # Check Blue Loop exists
                    bl = next((r for r in routes if r["short_name"] == "BL"), None)
                    assert bl is not None
                    assert bl["long_name"] == "Blue Loop"
    
    @pytest.mark.asyncio
    async def test_search_stops(self, mock_gtfs_data):
        """Test stop search."""
        with patch('catabus_mcp.server_v2.gtfs_data', mock_gtfs_data):
            with patch('catabus_mcp.server_v2.initialized', True):
                client = Client(mcp)
                async with client:
                    result = await client.call_tool("search_stops_tool", {"query": "HUB"})
                    stops = extract_result(result)
                    
                    assert isinstance(stops, list)
                    assert len(stops) == 1
                    assert stops[0]["stop_id"] == "HUB"
                    assert "HUB" in stops[0]["name"]
    
    @pytest.mark.asyncio 
    async def test_vehicle_positions(self, mock_realtime_data):
        """Test vehicle positions."""
        with patch('catabus_mcp.server_v2.realtime_poller') as mock_poller:
            with patch('catabus_mcp.server_v2.initialized', True):
                mock_poller.data = mock_realtime_data
                
                client = Client(mcp)
                async with client:
                    result = await client.call_tool("vehicle_positions_tool", {"route_id": "BL"})
                    vehicles = extract_result(result)
                    
                    assert isinstance(vehicles, list)
                    assert len(vehicles) == 1
                    assert vehicles[0]["vehicle_id"] == "BUS_001"
                    assert vehicles[0]["lat"] == 40.7982
    
    @pytest.mark.asyncio
    async def test_health_check(self, mock_gtfs_data):
        """Test health check endpoint."""
        with patch('catabus_mcp.server_v2.gtfs_data', mock_gtfs_data):
            with patch('catabus_mcp.server_v2.initialized', True):
                client = Client(mcp)
                async with client:
                    result = await client.call_tool("health_check", {})
                    health = extract_result(result)
                    
                    assert isinstance(health, dict)
                    assert health["status"] == "healthy"
                    assert health["routes_loaded"] == 3
                    assert health["stops_loaded"] == 2


class TestErrorHandling:
    """Test error cases."""
    
    @pytest.mark.asyncio
    async def test_missing_required_param(self):
        """Test missing required parameter handling."""
        client = Client(mcp)
        async with client:
            with pytest.raises(Exception):
                await client.call_tool("search_stops_tool", {})


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""
    
    @pytest.mark.asyncio
    async def test_blue_loop_workflow(self, mock_gtfs_data, mock_realtime_data):
        """Test complete Blue Loop tracking workflow."""
        with patch('catabus_mcp.server_v2.gtfs_data', mock_gtfs_data):
            with patch('catabus_mcp.server_v2.realtime_poller') as mock_poller:
                with patch('catabus_mcp.server_v2.initialized', True):
                    mock_poller.data = mock_realtime_data
                    
                    client = Client(mcp)
                    async with client:
                        # Step 1: Find Blue Loop route
                        routes_result = await client.call_tool("list_routes_tool", {})
                        routes = extract_result(routes_result)
                        
                        bl_route = next((r for r in routes if r["short_name"] == "BL"), None)
                        assert bl_route is not None
                        assert bl_route["long_name"] == "Blue Loop"
                        
                        # Step 2: Get Blue Loop vehicles
                        vehicles_result = await client.call_tool("vehicle_positions_tool", {"route_id": "BL"})
                        vehicles = extract_result(vehicles_result)
                        
                        assert len(vehicles) == 1
                        assert vehicles[0]["vehicle_id"] == "BUS_001"
                        
                        print("✅ Blue Loop workflow test passed!")
    
    @pytest.mark.asyncio
    async def test_stop_search_workflow(self, mock_gtfs_data):
        """Test stop search and arrival workflow.""" 
        with patch('catabus_mcp.server_v2.gtfs_data', mock_gtfs_data):
            with patch('catabus_mcp.server_v2.initialized', True):
                client = Client(mcp)
                async with client:
                    # Search for HUB stop
                    stops_result = await client.call_tool("search_stops_tool", {"query": "HUB"})
                    stops = extract_result(stops_result)
                    
                    assert len(stops) == 1
                    hub_stop = stops[0]
                    assert hub_stop["stop_id"] == "HUB"
                    
                    # Try to get arrivals (may be empty with mock data)
                    arrivals_result = await client.call_tool("next_arrivals_tool", {
                        "stop_id": hub_stop["stop_id"],
                        "horizon_minutes": 30
                    })
                    arrivals = extract_result(arrivals_result)
                    assert isinstance(arrivals, list)  # May be empty, but should be list
                    
                    print("✅ Stop search workflow test passed!")


class TestPerformance:
    """Performance and concurrency tests."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, mock_gtfs_data):
        """Test concurrent tool calls."""
        with patch('catabus_mcp.server_v2.gtfs_data', mock_gtfs_data):
            with patch('catabus_mcp.server_v2.initialized', True):
                client = Client(mcp)
                async with client:
                    # Make concurrent requests
                    tasks = [
                        client.call_tool("list_routes_tool", {}),
                        client.call_tool("search_stops_tool", {"query": "HUB"}),
                        client.call_tool("health_check", {})
                    ]
                    
                    results = await asyncio.gather(*tasks)
                    
                    # All should complete successfully
                    assert len(results) == 3
                    
                    # Extract and verify results
                    routes = extract_result(results[0])
                    stops = extract_result(results[1])
                    health = extract_result(results[2])
                    
                    assert len(routes) == 3
                    assert len(stops) == 1
                    assert health["status"] == "healthy"
                    
                    print("✅ Concurrent requests test passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])