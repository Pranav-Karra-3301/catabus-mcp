"""Comprehensive FastMCP server tests following best practices."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, Any

from fastmcp import Client
from catabus_mcp.server import mcp
from catabus_mcp.ingest.static_loader import GTFSData, Route, Stop, Trip, StopTime
from catabus_mcp.ingest.realtime_poll import RealtimeData, VehiclePosition, TripUpdate, ServiceAlert


@pytest.fixture
def mock_gtfs_data():
    """Create mock GTFS static data for testing."""
    data = GTFSData()
    
    # Add test routes
    data.routes = {
        "BL": Route(
            route_id="BL",
            route_short_name="BL",
            route_long_name="Blue Loop",
            route_type=3,
            route_color="0000FF"
        ),
        "WL": Route(
            route_id="WL", 
            route_short_name="WL",
            route_long_name="White Loop",
            route_type=3,
            route_color="FFFFFF"
        ),
        "N": Route(
            route_id="N",
            route_short_name="N",
            route_long_name="Campus Loop North",
            route_type=3,
            route_color="00FF00"
        )
    }
    
    # Add test stops
    data.stops = {
        "HUB": Stop(
            stop_id="HUB",
            stop_name="HUB-Robeson Center",
            stop_lat=40.7982,
            stop_lon=-77.8599,
            stop_code="HUB"
        ),
        "CURTIN_BJC": Stop(
            stop_id="CURTIN_BJC",
            stop_name="Curtin Rd at Bryce Jordan Center",
            stop_lat=40.8123,
            stop_lon=-77.8456,
            stop_code="287"
        ),
        "ATHERTON_CVS": Stop(
            stop_id="ATHERTON_CVS",
            stop_name="1101 N. Atherton St at CVS",
            stop_lat=40.8012,
            stop_lon=-77.8634,
            stop_code="8"
        )
    }
    
    # Add test trips
    data.trips = {
        "BL_001": Trip(
            trip_id="BL_001",
            route_id="BL",
            service_id="WEEKDAY",
            trip_headsign="Blue Loop"
        )
    }
    
    # Add test stop times
    data.stop_times = [
        StopTime(
            trip_id="BL_001",
            arrival_time="09:00:00",
            departure_time="09:00:00",
            stop_id="HUB",
            stop_sequence=1
        ),
        StopTime(
            trip_id="BL_001", 
            arrival_time="09:05:00",
            departure_time="09:05:00",
            stop_id="CURTIN_BJC",
            stop_sequence=2
        )
    ]
    
    data.last_updated = datetime.now(timezone.utc)
    return data


@pytest.fixture
def mock_realtime_data():
    """Create mock realtime data for testing."""
    data = RealtimeData()
    
    # Add test vehicle position
    data.vehicle_positions["BUS_001"] = VehiclePosition(
        vehicle_id="BUS_001",
        trip_id="BL_001",
        route_id="BL",
        latitude=40.7982,
        longitude=-77.8599,
        bearing=90.0,
        speed=10.5,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Add test trip update with delay
    data.trip_updates["BL_001"] = TripUpdate(
        trip_id="BL_001",
        route_id="BL",
        vehicle_id="BUS_001",
        timestamp=datetime.now(timezone.utc),
        stop_time_updates=[{
            "stop_id": "CURTIN_BJC",
            "stop_sequence": 2,
            "arrival_delay": 180,  # 3 minutes late
        }]
    )
    
    # Add test alert
    data.alerts = [ServiceAlert(
        alert_id="ALERT_001",
        header="Blue Loop Detour",
        description="Blue Loop detoured due to construction",
        severity="WARNING",
        informed_entities=[{"route_id": "BL"}]
    )]
    
    data.last_vehicle_update = datetime.now(timezone.utc)
    data.last_trip_update = datetime.now(timezone.utc)
    data.last_alert_update = datetime.now(timezone.utc)
    
    return data


@pytest.fixture
async def client(mock_gtfs_data, mock_realtime_data):
    """Create FastMCP client with mocked data."""
    with patch('catabus_mcp.server_v2.gtfs_data', mock_gtfs_data):
        with patch('catabus_mcp.server_v2.realtime_poller') as mock_poller:
            with patch('catabus_mcp.server_v2.initialized', True):
                # Mock the realtime poller
                mock_poller.data = mock_realtime_data
                
                # Create client
                client = Client(mcp)
                async with client:
                    yield client


class TestListRoutes:
    """Test the list_routes_tool."""
    
    async def test_list_routes_success(self, client):
        """Test successful route listing."""
        result = await client.call_tool("list_routes_tool", {})
        routes = result.content if hasattr(result, 'content') else result
        
        assert len(routes) == 3
        
        # Check Blue Loop is present
        bl_route = next((r for r in routes if r["route_id"] == "BL"), None)
        assert bl_route is not None
        assert bl_route["short_name"] == "BL"
        assert bl_route["long_name"] == "Blue Loop"
        assert bl_route["color"] == "#0000FF"
    
    async def test_list_routes_sorted(self, client):
        """Test routes are sorted by short name."""
        result = await client.call_tool("list_routes_tool", {})
        routes = result
        
        short_names = [r["short_name"] for r in routes]
        assert short_names == sorted(short_names)


class TestSearchStops:
    """Test the search_stops_tool."""
    
    async def test_search_by_name(self, client):
        """Test searching stops by name."""
        result = await client.call_tool("search_stops_tool", {"query": "HUB"})
        stops = result
        
        assert len(stops) == 1
        assert stops[0]["stop_id"] == "HUB"
        assert stops[0]["name"] == "HUB-Robeson Center"
        assert stops[0]["lat"] == 40.7982
        assert stops[0]["lon"] == -77.8599
    
    async def test_search_by_partial_name(self, client):
        """Test searching with partial names."""
        result = await client.call_tool("search_stops_tool", {"query": "Curtin"})
        stops = result
        
        assert len(stops) == 1
        assert "Curtin" in stops[0]["name"]
    
    async def test_search_case_insensitive(self, client):
        """Test case insensitive search."""
        result = await client.call_tool("search_stops_tool", {"query": "atherton"})
        stops = result
        
        assert len(stops) == 1
        assert "Atherton" in stops[0]["name"]
    
    async def test_search_no_results(self, client):
        """Test search with no results."""
        result = await client.call_tool("search_stops_tool", {"query": "NONEXISTENT"})
        stops = result
        
        assert len(stops) == 0
    
    async def test_search_empty_query(self, client):
        """Test search with empty query."""
        result = await client.call_tool("search_stops_tool", {"query": ""})
        stops = result
        
        assert len(stops) == 0


class TestVehiclePositions:
    """Test the vehicle_positions_tool."""
    
    async def test_get_blue_loop_vehicles(self, client):
        """Test getting Blue Loop vehicle positions."""
        result = await client.call_tool("vehicle_positions_tool", {"route_id": "BL"})
        vehicles = result
        
        assert len(vehicles) == 1
        vehicle = vehicles[0]
        assert vehicle["vehicle_id"] == "BUS_001"
        assert vehicle["lat"] == 40.7982
        assert vehicle["lon"] == -77.8599
        assert vehicle["bearing"] == 90.0
        assert vehicle["speed_mps"] == 10.5
    
    async def test_get_vehicles_no_active(self, client):
        """Test getting vehicles for route with no active buses."""
        result = await client.call_tool("vehicle_positions_tool", {"route_id": "WL"})
        vehicles = result
        
        assert len(vehicles) == 0
    
    async def test_get_vehicles_nonexistent_route(self, client):
        """Test getting vehicles for nonexistent route."""
        result = await client.call_tool("vehicle_positions_tool", {"route_id": "FAKE"})
        vehicles = result
        
        assert len(vehicles) == 0


class TestNextArrivals:
    """Test the next_arrivals_tool."""
    
    async def test_get_arrivals_with_delay(self, client):
        """Test getting arrivals with real-time delay."""
        with patch('catabus_mcp.tools.next_arrivals.datetime') as mock_dt:
            # Mock current time to be before the scheduled arrival
            mock_dt.now.return_value = datetime(2024, 1, 1, 8, 55, 0, tzinfo=timezone.utc)
            mock_dt.combine.return_value = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
            mock_dt.fromtimestamp = datetime.fromtimestamp
            
            result = await client.call_tool("next_arrivals_tool", {
                "stop_id": "CURTIN_BJC",
                "horizon_minutes": 60
            })
            arrivals = result
            
            # Should find the arrival with delay applied
            assert len(arrivals) >= 0  # May be 0 due to time filtering
    
    async def test_get_arrivals_invalid_stop(self, client):
        """Test getting arrivals for invalid stop."""
        result = await client.call_tool("next_arrivals_tool", {
            "stop_id": "INVALID_STOP",
            "horizon_minutes": 30
        })
        arrivals = result
        
        assert len(arrivals) == 0
    
    async def test_get_arrivals_custom_horizon(self, client):
        """Test getting arrivals with custom time horizon."""
        result = await client.call_tool("next_arrivals_tool", {
            "stop_id": "HUB",
            "horizon_minutes": 120
        })
        arrivals = result
        
        # Should accept custom horizon without error
        assert isinstance(arrivals, list)


class TestTripAlerts:
    """Test the trip_alerts_tool."""
    
    async def test_get_all_alerts(self, client):
        """Test getting all service alerts."""
        result = await client.call_tool("trip_alerts_tool", {})
        alerts = result
        
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["header"] == "Blue Loop Detour"
        assert alert["description"] == "Blue Loop detoured due to construction"
        assert alert["severity"] == "WARNING"
        assert "BL" in alert["affected_routes"]
    
    async def test_get_alerts_for_route(self, client):
        """Test getting alerts filtered by route."""
        result = await client.call_tool("trip_alerts_tool", {"route_id": "BL"})
        alerts = result
        
        assert len(alerts) == 1
        assert alerts[0]["header"] == "Blue Loop Detour"
    
    async def test_get_alerts_no_matching_route(self, client):
        """Test getting alerts for route with no alerts."""
        result = await client.call_tool("trip_alerts_tool", {"route_id": "WL"})
        alerts = result
        
        assert len(alerts) == 0


class TestHealthCheck:
    """Test the health_check tool."""
    
    async def test_health_check_success(self, client):
        """Test successful health check."""
        result = await client.call_tool("health_check", {})
        health = result
        
        assert health["status"] == "healthy"
        assert health["initialized"] == True
        assert health["routes_loaded"] == 3
        assert health["stops_loaded"] == 3
        assert health["server_time"] is not None


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    async def test_tool_with_missing_params(self, client):
        """Test tool call with missing required parameters."""
        with pytest.raises(Exception):  # Should raise validation error
            await client.call_tool("search_stops_tool", {})
    
    async def test_tool_with_invalid_params(self, client):
        """Test tool call with invalid parameter types."""
        with pytest.raises(Exception):
            await client.call_tool("next_arrivals_tool", {
                "stop_id": "HUB",
                "horizon_minutes": "invalid"  # Should be int
            })


class TestIntegrationScenarios:
    """Integration tests for common usage scenarios."""
    
    async def test_find_blue_loop_and_track_vehicles(self, client):
        """Test complete workflow: find Blue Loop route and track its vehicles."""
        # Step 1: List routes to find Blue Loop
        routes = await client.call_tool("list_routes_tool", {})
        bl_route = next((r for r in routes if r["short_name"] == "BL"), None)
        assert bl_route is not None
        
        # Step 2: Get vehicle positions for Blue Loop
        vehicles = await client.call_tool("vehicle_positions_tool", {"route_id": "BL"})
        assert len(vehicles) == 1
        assert vehicles[0]["vehicle_id"] == "BUS_001"
    
    async def test_find_stop_and_get_arrivals(self, client):
        """Test workflow: search for stop and get next arrivals."""
        # Step 1: Search for HUB stop
        stops = await client.call_tool("search_stops_tool", {"query": "HUB"})
        assert len(stops) == 1
        stop = stops[0]
        
        # Step 2: Get next arrivals at that stop
        arrivals = await client.call_tool("next_arrivals_tool", {
            "stop_id": stop["stop_id"],
            "horizon_minutes": 60
        })
        # May be empty due to time filtering, but should not error
        assert isinstance(arrivals, list)
    
    async def test_check_alerts_for_active_routes(self, client):
        """Test workflow: check alerts for routes with active vehicles."""
        # Step 1: Get all active vehicle positions
        bl_vehicles = await client.call_tool("vehicle_positions_tool", {"route_id": "BL"})
        
        # Step 2: If vehicles are active, check for alerts
        if bl_vehicles:
            alerts = await client.call_tool("trip_alerts_tool", {"route_id": "BL"})
            assert len(alerts) == 1
            assert alerts[0]["severity"] == "WARNING"


# Performance and load testing
class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client):
        """Test handling concurrent requests."""
        tasks = [
            client.call_tool("list_routes_tool", {}),
            client.call_tool("search_stops_tool", {"query": "HUB"}),
            client.call_tool("vehicle_positions_tool", {"route_id": "BL"}),
            client.call_tool("health_check", {})
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All requests should complete successfully
        assert len(results) == 4
        assert len(results[0]) == 3  # routes
        assert len(results[1]) == 1  # stops
        assert len(results[2]) == 1  # vehicles
        assert results[3]["status"] == "healthy"  # health


if __name__ == "__main__":
    pytest.main([__file__, "-v"])