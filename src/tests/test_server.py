"""Tests for the FastMCP server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from catabus_mcp.server import (
    list_routes_tool,
    search_stops_tool,
    next_arrivals_tool,
    vehicle_positions_tool,
    trip_alerts_tool,
    SearchStopsRequest,
    NextArrivalsRequest,
    VehiclePositionsRequest,
    TripAlertsRequest
)


@pytest.mark.asyncio
async def test_list_routes_tool_empty():
    """Test list_routes tool with no data."""
    with patch("catabus_mcp.server.gtfs_data", None):
        result = await list_routes_tool()
        assert result == []


@pytest.mark.asyncio
async def test_search_stops_tool_empty():
    """Test search_stops tool with no data."""
    with patch("catabus_mcp.server.gtfs_data", None):
        request = SearchStopsRequest(query="HUB")
        result = await search_stops_tool(request)
        assert result == []


@pytest.mark.asyncio
async def test_next_arrivals_tool_empty():
    """Test next_arrivals tool with no data."""
    with patch("catabus_mcp.server.gtfs_data", None):
        request = NextArrivalsRequest(stop_id="PSU_HUB", horizon_minutes=30)
        result = await next_arrivals_tool(request)
        assert result == []


@pytest.mark.asyncio
async def test_vehicle_positions_tool():
    """Test vehicle_positions tool."""
    mock_realtime_data = MagicMock()
    mock_realtime_data.vehicle_positions = {}
    
    with patch("catabus_mcp.server.realtime_poller.data", mock_realtime_data):
        with patch("catabus_mcp.server.vehicle_positions", AsyncMock(return_value=[])):
            request = VehiclePositionsRequest(route_id="N")
            result = await vehicle_positions_tool(request)
            assert result == []


@pytest.mark.asyncio
async def test_trip_alerts_tool():
    """Test trip_alerts tool."""
    mock_realtime_data = MagicMock()
    mock_realtime_data.alerts = []
    
    with patch("catabus_mcp.server.realtime_poller.data", mock_realtime_data):
        with patch("catabus_mcp.server.trip_alerts", AsyncMock(return_value=[])):
            request = TripAlertsRequest(route_id="N")
            result = await trip_alerts_tool(request)
            assert result == []