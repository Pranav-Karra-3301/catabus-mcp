"""Tests for the FastMCP server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from catabus_mcp.server import (
    list_routes_tool,
    search_stops_tool,
    next_arrivals_tool,
    vehicle_positions_tool,
    trip_alerts_tool,
)


@pytest.mark.asyncio
async def test_list_routes_tool_empty():
    """Test list_routes tool with no data."""
    with patch("catabus_mcp.server.gtfs_data", None):
        with patch("catabus_mcp.server.initialized", True):
            result = await list_routes_tool()
            assert result == []


@pytest.mark.asyncio
async def test_search_stops_tool_empty():
    """Test search_stops tool with no data."""
    with patch("catabus_mcp.server.gtfs_data", None):
        with patch("catabus_mcp.server.initialized", True):
            result = await search_stops_tool(query="HUB")
            assert result == []


@pytest.mark.asyncio
async def test_next_arrivals_tool_empty():
    """Test next_arrivals tool with no data."""
    with patch("catabus_mcp.server.gtfs_data", None):
        with patch("catabus_mcp.server.initialized", True):
            result = await next_arrivals_tool(stop_id="PSU_HUB", horizon_minutes=30)
            assert result == []


@pytest.mark.asyncio
async def test_vehicle_positions_tool():
    """Test vehicle_positions tool."""
    mock_realtime_data = MagicMock()
    mock_realtime_data.vehicle_positions = {}

    with patch("catabus_mcp.server.initialized", True):
        with patch("catabus_mcp.server.realtime_poller.data", mock_realtime_data):
            with patch("catabus_mcp.server.vehicle_positions", AsyncMock(return_value=[])):
                result = await vehicle_positions_tool(route_id="N")
                assert result == []


@pytest.mark.asyncio
async def test_trip_alerts_tool():
    """Test trip_alerts tool."""
    mock_realtime_data = MagicMock()
    mock_realtime_data.alerts = []

    with patch("catabus_mcp.server.initialized", True):
        with patch("catabus_mcp.server.realtime_poller.data", mock_realtime_data):
            with patch("catabus_mcp.server.trip_alerts", AsyncMock(return_value=[])):
                result = await trip_alerts_tool(route_id="N")
                assert result == []