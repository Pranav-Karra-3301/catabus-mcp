"""Integration tests for FastMCP server using best practices."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, Mock

from fastmcp import Client
from catabus_mcp.server_v2 import mcp


class TestMCPIntegration:
    """End-to-end MCP integration tests."""
    
    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test that server initializes properly with mocked data."""
        with patch('catabus_mcp.server_v2.ensure_initialized') as mock_init:
            mock_init.return_value = None
            
            client = Client(mcp)
            async with client:
                # Server should connect without errors
                tools = await client.list_tools()
                tool_names = [tool.name for tool in tools]
                
                expected_tools = [
                    "list_routes_tool",
                    "search_stops_tool", 
                    "next_arrivals_tool",
                    "vehicle_positions_tool",
                    "trip_alerts_tool",
                    "health_check"
                ]
                
                for tool in expected_tools:
                    assert tool in tool_names
    
    @pytest.mark.asyncio
    async def test_tool_schemas(self):
        """Test that all tools have proper input/output schemas."""
        client = Client(mcp)
        async with client:
            tools = await client.list_tools()
            
            # Check search_stops_tool has required query parameter
            search_tool = next(t for t in tools if t.name == "search_stops_tool")
            assert "query" in str(search_tool.inputSchema)
            
            # Check next_arrivals_tool has stop_id parameter
            arrivals_tool = next(t for t in tools if t.name == "next_arrivals_tool") 
            assert "stop_id" in str(arrivals_tool.inputSchema)
            
            # Check vehicle_positions_tool has route_id parameter
            vehicles_tool = next(t for t in tools if t.name == "vehicle_positions_tool")
            assert "route_id" in str(vehicles_tool.inputSchema)


class TestRealWorldScenarios:
    """Test real-world usage scenarios with proper mocking."""
    
    @pytest.fixture
    def mock_cata_data(self):
        """Mock real CATA data responses."""
        return {
            "routes": [
                {"route_id": "BL", "short_name": "BL", "long_name": "Blue Loop", "color": "#0000FF"},
                {"route_id": "WL", "short_name": "WL", "long_name": "White Loop", "color": "#FFFFFF"},
                {"route_id": "N", "short_name": "N", "long_name": "Campus Loop North", "color": "#00FF00"}
            ],
            "stops": [
                {"stop_id": "HUB", "name": "HUB-Robeson Center", "lat": 40.7982, "lon": -77.8599},
                {"stop_id": "ATHERTON_CURTIN", "name": "Atherton St at Curtin Rd", "lat": 40.8012, "lon": -77.8634}
            ],
            "vehicles": [
                {"vehicle_id": "BUS_001", "route_id": "BL", "lat": 40.7982, "lon": -77.8599, "bearing": 90.0, "speed_mps": 10.5}
            ]
        }
    
    @pytest.mark.asyncio
    async def test_blue_loop_tracking_scenario(self, mock_cata_data):
        """Test complete Blue Loop tracking scenario."""
        with patch('catabus_mcp.server_v2.list_routes') as mock_list_routes:
            with patch('catabus_mcp.server_v2.vehicle_positions') as mock_vehicles:
                with patch('catabus_mcp.server_v2.initialized', True):
                    
                    # Mock responses
                    mock_list_routes.return_value = mock_cata_data["routes"]
                    mock_vehicles.return_value = mock_cata_data["vehicles"]
                    
                    client = Client(mcp)
                    async with client:
                        # Step 1: User asks for all routes
                        routes = await client.call_tool("list_routes_tool", {})
                        blue_loop = next((r for r in routes if r["short_name"] == "BL"), None)
                        assert blue_loop is not None
                        assert blue_loop["long_name"] == "Blue Loop"
                        
                        # Step 2: User tracks Blue Loop vehicles
                        vehicles = await client.call_tool("vehicle_positions_tool", {"route_id": "BL"})
                        assert len(vehicles) == 1
                        assert vehicles[0]["vehicle_id"] == "BUS_001"
                        assert vehicles[0]["lat"] == 40.7982
    
    @pytest.mark.asyncio 
    async def test_stop_search_and_arrivals_scenario(self, mock_cata_data):
        """Test searching stops and getting arrivals."""
        with patch('catabus_mcp.server_v2.search_stops') as mock_search:
            with patch('catabus_mcp.server_v2.next_arrivals') as mock_arrivals:
                with patch('catabus_mcp.server_v2.initialized', True):
                    
                    # Mock responses
                    mock_search.return_value = mock_cata_data["stops"]
                    mock_arrivals.return_value = [
                        {
                            "trip_id": "BL_001",
                            "route_id": "BL",
                            "arrival_time_iso": "2024-01-01T09:15:00-05:00",
                            "delay_sec": 180
                        }
                    ]
                    
                    client = Client(mcp)
                    async with client:
                        # Step 1: Search for HUB
                        stops = await client.call_tool("search_stops_tool", {"query": "HUB"})
                        hub_stop = next((s for s in stops if "HUB" in s["name"]), None)
                        assert hub_stop is not None
                        
                        # Step 2: Get arrivals at HUB
                        arrivals = await client.call_tool("next_arrivals_tool", {
                            "stop_id": hub_stop["stop_id"],
                            "horizon_minutes": 30
                        })
                        assert len(arrivals) == 1
                        assert arrivals[0]["route_id"] == "BL"
                        assert arrivals[0]["delay_sec"] == 180  # 3 minutes late


class TestErrorHandlingBestPractices:
    """Test error handling following FastMCP best practices."""
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test server handles data loading failures gracefully."""
        with patch('catabus_mcp.server_v2.ensure_initialized') as mock_init:
            # Simulate initialization failure
            mock_init.side_effect = Exception("GTFS download failed")
            
            client = Client(mcp)
            async with client:
                # Server should still respond but return empty data
                try:
                    routes = await client.call_tool("list_routes_tool", {})
                    # Should return empty list rather than crash
                    assert isinstance(routes, list)
                except Exception as e:
                    # Or handle error gracefully
                    assert "GTFS" in str(e)
    
    @pytest.mark.asyncio
    async def test_invalid_input_validation(self):
        """Test proper input validation."""
        with patch('catabus_mcp.server_v2.initialized', True):
            client = Client(mcp)
            async with client:
                # Test missing required parameter
                with pytest.raises(Exception):
                    await client.call_tool("search_stops_tool", {})
                
                # Test invalid parameter type
                with pytest.raises(Exception):
                    await client.call_tool("next_arrivals_tool", {
                        "stop_id": 123,  # Should be string
                        "horizon_minutes": "invalid"  # Should be int
                    })


class TestPerformanceBestPractices:
    """Performance tests following FastMCP best practices."""
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """Test server handles concurrent requests properly."""
        with patch('catabus_mcp.server_v2.initialized', True):
            with patch('catabus_mcp.server_v2.list_routes') as mock_routes:
                with patch('catabus_mcp.server_v2.search_stops') as mock_search:
                    with patch('catabus_mcp.server_v2.vehicle_positions') as mock_vehicles:
                        
                        # Mock quick responses
                        mock_routes.return_value = [{"route_id": "BL", "short_name": "BL", "long_name": "Blue Loop", "color": "#0000FF"}]
                        mock_search.return_value = [{"stop_id": "HUB", "name": "HUB-Robeson Center", "lat": 40.7982, "lon": -77.8599}]
                        mock_vehicles.return_value = []
                        
                        client = Client(mcp)
                        async with client:
                            # Make concurrent requests
                            tasks = [
                                client.call_tool("list_routes_tool", {}),
                                client.call_tool("search_stops_tool", {"query": "HUB"}),
                                client.call_tool("vehicle_positions_tool", {"route_id": "BL"}),
                                client.call_tool("health_check", {}),
                            ]
                            
                            # All should complete successfully
                            results = await asyncio.gather(*tasks, return_exceptions=True)
                            
                            # Check no exceptions occurred
                            for result in results:
                                assert not isinstance(result, Exception), f"Request failed: {result}"
    
    @pytest.mark.asyncio
    async def test_response_time_reasonable(self):
        """Test that responses come back in reasonable time."""
        with patch('catabus_mcp.server_v2.initialized', True):
            with patch('catabus_mcp.server_v2.list_routes') as mock_routes:
                mock_routes.return_value = [{"route_id": "BL", "short_name": "BL", "long_name": "Blue Loop", "color": "#0000FF"}]
                
                client = Client(mcp)
                async with client:
                    start_time = datetime.now()
                    await client.call_tool("list_routes_tool", {})
                    end_time = datetime.now()
                    
                    # Should complete in under 1 second for in-memory operations
                    duration = (end_time - start_time).total_seconds()
                    assert duration < 1.0, f"Response took too long: {duration}s"


class TestDataConsistency:
    """Test data consistency and integrity."""
    
    @pytest.mark.asyncio
    async def test_route_data_consistency(self):
        """Test that route data is consistent across tools."""
        mock_routes = [
            {"route_id": "BL", "short_name": "BL", "long_name": "Blue Loop", "color": "#0000FF"}
        ]
        
        mock_vehicles = [
            {"vehicle_id": "BUS_001", "lat": 40.7982, "lon": -77.8599, "bearing": 90.0, "speed_mps": 10.5}
        ]
        
        with patch('catabus_mcp.server_v2.initialized', True):
            with patch('catabus_mcp.server_v2.list_routes', return_value=mock_routes):
                with patch('catabus_mcp.server_v2.vehicle_positions', return_value=mock_vehicles):
                    
                    client = Client(mcp)
                    async with client:
                        # Get routes
                        routes = await client.call_tool("list_routes_tool", {})
                        bl_route = next((r for r in routes if r["route_id"] == "BL"), None)
                        assert bl_route is not None
                        
                        # Get vehicles for same route - should be consistent
                        vehicles = await client.call_tool("vehicle_positions_tool", {"route_id": "BL"})
                        # Vehicles exist for this route
                        assert len(vehicles) == 1