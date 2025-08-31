"""FastMCP server for CATA bus data - Cloud deployment version."""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from fastmcp import FastMCP

from .ingest.realtime_poll import RealtimeGTFSPoller
from .ingest.static_loader import StaticGTFSLoader
from .tools.list_routes import list_routes
from .tools.next_arrivals import next_arrivals
from .tools.search_stops import search_stops
from .tools.trip_alerts import trip_alerts
from .tools.vehicle_positions import vehicle_positions

# Configure logging for cloud environment
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("catabus-mcp", version="0.1.0")

# Global data stores
static_loader = StaticGTFSLoader()
realtime_poller = RealtimeGTFSPoller()
gtfs_data = None
initialized = False


async def ensure_initialized():
    """Lazy initialization of GTFS data - only when needed."""
    global gtfs_data, initialized
    if not initialized:
        logger.info("Starting GTFS data initialization...")
        try:
            # Load static GTFS data with timeout
            gtfs_data = await static_loader.load_feed(force_refresh=False)
            
            # Start realtime polling in background
            await realtime_poller.start()
            
            initialized = True
            logger.info(f"GTFS data loaded: {len(gtfs_data.routes)} routes, {len(gtfs_data.stops)} stops")
            
        except Exception as e:
            logger.error(f"Failed to initialize GTFS data: {e}")
            # Initialize with empty data to prevent crashes
            from .ingest.static_loader import GTFSData
            from .ingest.realtime_poll import RealtimeData
            gtfs_data = GTFSData()
            realtime_poller.data = RealtimeData()
            initialized = True
            logger.warning("Running with empty GTFS data due to initialization failure")


@mcp.tool
async def list_routes_tool() -> List[Dict[str, Any]]:
    """List all available bus routes.
    
    Returns a list of routes with their ID, short name, long name, and color.
    """
    await ensure_initialized()
    if not gtfs_data or not gtfs_data.routes:
        return []
    return await list_routes(gtfs_data)


@mcp.tool
async def search_stops_tool(query: str) -> List[Dict[str, Any]]:
    """Search for stops by name or ID.
    
    Args:
        query: Search query string to match against stop names, IDs, or descriptions
    
    Returns:
        List of matching stops with their ID, name, latitude, and longitude
    """
    await ensure_initialized()
    if not gtfs_data or not gtfs_data.stops:
        return []
    return await search_stops(gtfs_data, query)


@mcp.tool
async def next_arrivals_tool(
    stop_id: str,
    horizon_minutes: int = 30
) -> List[Dict[str, Any]]:
    """Get next arrivals at a specific stop.
    
    Args:
        stop_id: The stop ID to query
        horizon_minutes: How many minutes ahead to look (default 30)
    
    Returns:
        List of upcoming arrivals with trip ID, route ID, arrival time, and delay
    """
    await ensure_initialized()
    if not gtfs_data or not gtfs_data.stop_times:
        return []
    return await next_arrivals(
        gtfs_data,
        realtime_poller.data,
        stop_id,
        horizon_minutes
    )


@mcp.tool
async def vehicle_positions_tool(route_id: str) -> List[Dict[str, Any]]:
    """Get current positions of vehicles on a specific route.
    
    Args:
        route_id: The route ID to filter by (e.g., "BL" for Blue Loop)
    
    Returns:
        List of vehicle positions with ID, coordinates, bearing, and speed
    """
    await ensure_initialized()
    return await vehicle_positions(realtime_poller.data, route_id)


@mcp.tool
async def trip_alerts_tool(route_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get current service alerts.
    
    Args:
        route_id: Optional route ID to filter alerts (if None, returns all)
    
    Returns:
        List of alerts with route ID, header, description, and severity
    """
    await ensure_initialized()
    return await trip_alerts(realtime_poller.data, route_id)


@mcp.tool
async def health_check() -> Dict[str, Any]:
    """Fast health check without triggering data initialization."""
    return {
        "status": "healthy",
        "initialized": initialized,
        "routes_loaded": len(gtfs_data.routes) if gtfs_data else 0,
        "stops_loaded": len(gtfs_data.stops) if gtfs_data else 0,
        "last_static_update": gtfs_data.last_updated.isoformat() if gtfs_data and gtfs_data.last_updated else None,
        "last_vehicle_update": realtime_poller.data.last_vehicle_update.isoformat() if realtime_poller.data.last_vehicle_update else None,
        "last_trip_update": realtime_poller.data.last_trip_update.isoformat() if realtime_poller.data.last_trip_update else None,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "environment": "cloud",
        "startup_mode": "lazy_loading"
    }


@mcp.tool
async def initialize_data() -> Dict[str, Any]:
    """Manually trigger GTFS data initialization."""
    await ensure_initialized()
    return {
        "status": "initialized" if initialized else "failed",
        "routes_loaded": len(gtfs_data.routes) if gtfs_data else 0,
        "stops_loaded": len(gtfs_data.stops) if gtfs_data else 0,
        "message": "GTFS data has been loaded" if initialized else "Failed to load GTFS data"
    }


# Export the FastMCP server and app for FastMCP Cloud
server = mcp
app = mcp.http_app()


def main():
    """Entry point for CLI usage via pyproject.toml scripts."""
    mcp.run()


# Optional local development entry point
if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0:8080 for FastMCP Cloud compatibility
    uvicorn.run(app, host="0.0.0.0", port=8080)