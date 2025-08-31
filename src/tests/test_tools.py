"""Tests for MCP tools."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from catabus_mcp.ingest.static_loader import GTFSData, Route, Stop, Trip, StopTime
from catabus_mcp.ingest.realtime_poll import RealtimeData, VehiclePosition, TripUpdate, ServiceAlert
from catabus_mcp.tools.list_routes import list_routes
from catabus_mcp.tools.search_stops import search_stops
from catabus_mcp.tools.next_arrivals import next_arrivals
from catabus_mcp.tools.vehicle_positions import vehicle_positions
from catabus_mcp.tools.trip_alerts import trip_alerts


@pytest.fixture
def sample_gtfs_data():
    """Create sample GTFS static data for testing."""
    data = GTFSData()
    
    # Add sample routes
    data.routes["N"] = Route(
        route_id="N",
        route_short_name="N",
        route_long_name="Campus Loop North",
        route_type=3,
        route_color="003366"
    )
    data.routes["V"] = Route(
        route_id="V",
        route_short_name="V",
        route_long_name="Vairo Village",
        route_type=3,
        route_color="FF6600"
    )
    
    # Add sample stops
    data.stops["PSU_HUB"] = Stop(
        stop_id="PSU_HUB",
        stop_name="HUB-Robeson Center",
        stop_lat=40.7982,
        stop_lon=-77.8599
    )
    data.stops["PSU_ALLEN_BEAVER"] = Stop(
        stop_id="PSU_ALLEN_BEAVER",
        stop_name="Allen St at Beaver Ave",
        stop_lat=40.7950,
        stop_lon=-77.8612
    )
    
    # Add sample trips
    data.trips["TRIP_N_001"] = Trip(
        trip_id="TRIP_N_001",
        route_id="N",
        service_id="WEEKDAY",
        trip_headsign="Campus Loop North"
    )
    
    # Add sample stop times
    data.stop_times.append(StopTime(
        trip_id="TRIP_N_001",
        arrival_time="08:30:00",
        departure_time="08:30:00",
        stop_id="PSU_HUB",
        stop_sequence=1
    ))
    data.stop_times.append(StopTime(
        trip_id="TRIP_N_001",
        arrival_time="08:35:00",
        departure_time="08:35:00",
        stop_id="PSU_ALLEN_BEAVER",
        stop_sequence=2
    ))
    
    return data


@pytest.fixture
def sample_realtime_data():
    """Create sample GTFS realtime data for testing."""
    data = RealtimeData()
    
    # Add sample vehicle position
    data.vehicle_positions["BUS_001"] = VehiclePosition(
        vehicle_id="BUS_001",
        trip_id="TRIP_N_001",
        route_id="N",
        latitude=40.7982,
        longitude=-77.8599,
        bearing=90.0,
        speed=10.5,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Add sample trip update
    data.trip_updates["TRIP_N_001"] = TripUpdate(
        trip_id="TRIP_N_001",
        route_id="N",
        vehicle_id="BUS_001",
        timestamp=datetime.now(timezone.utc),
        stop_time_updates=[
            {
                "stop_id": "PSU_ALLEN_BEAVER",
                "stop_sequence": 2,
                "arrival_delay": 120,  # 2 minutes late
            }
        ]
    )
    
    # Add sample alert
    data.alerts.append(ServiceAlert(
        alert_id="ALERT_001",
        header="Route N Detour",
        description="Route N is on detour due to construction",
        severity="WARNING",
        informed_entities=[{"route_id": "N"}]
    ))
    
    return data


@pytest.mark.asyncio
async def test_list_routes(sample_gtfs_data):
    """Test listing routes."""
    routes = await list_routes(sample_gtfs_data)
    
    assert len(routes) == 2
    assert routes[0]["route_id"] == "N"
    assert routes[0]["short_name"] == "N"
    assert routes[0]["long_name"] == "Campus Loop North"
    assert routes[0]["color"] == "#003366"


@pytest.mark.asyncio
async def test_search_stops(sample_gtfs_data):
    """Test searching for stops."""
    # Search by partial name
    results = await search_stops(sample_gtfs_data, "HUB")
    assert len(results) == 1
    assert results[0]["stop_id"] == "PSU_HUB"
    assert results[0]["name"] == "HUB-Robeson Center"
    
    # Search by stop ID
    results = await search_stops(sample_gtfs_data, "PSU_ALLEN")
    assert len(results) == 1
    assert results[0]["stop_id"] == "PSU_ALLEN_BEAVER"
    
    # Search with no matches
    results = await search_stops(sample_gtfs_data, "NONEXISTENT")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_vehicle_positions(sample_realtime_data):
    """Test getting vehicle positions."""
    # Get positions for route N
    positions = await vehicle_positions(sample_realtime_data, "N")
    assert len(positions) == 1
    assert positions[0]["vehicle_id"] == "BUS_001"
    assert positions[0]["lat"] == 40.7982
    assert positions[0]["lon"] == -77.8599
    assert positions[0]["bearing"] == 90.0
    assert positions[0]["speed_mps"] == 10.5
    
    # Get positions for route with no vehicles
    positions = await vehicle_positions(sample_realtime_data, "V")
    assert len(positions) == 0


@pytest.mark.asyncio
async def test_trip_alerts(sample_realtime_data):
    """Test getting service alerts."""
    # Get all alerts
    alerts = await trip_alerts(sample_realtime_data)
    assert len(alerts) == 1
    assert alerts[0]["header"] == "Route N Detour"
    assert alerts[0]["severity"] == "WARNING"
    
    # Get alerts for specific route
    alerts = await trip_alerts(sample_realtime_data, "N")
    assert len(alerts) == 1
    
    # Get alerts for route with no alerts
    alerts = await trip_alerts(sample_realtime_data, "V")
    assert len(alerts) == 0