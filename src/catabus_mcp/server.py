"""FastMCP server for CATA bus data - Cloud deployment version."""

import asyncio
import logging
import os
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
    """Lazy initialization of GTFS data with comprehensive error handling."""
    global gtfs_data, initialized
    if not initialized:
        logger.info("Starting GTFS data initialization...")
        
        # Initialize with empty data first to ensure server always works
        from .ingest.static_loader import GTFSData
        from .ingest.realtime_poll import RealtimeData
        
        try:
            # Try to load static GTFS data with aggressive timeout
            gtfs_data = await asyncio.wait_for(
                static_loader.load_feed(force_refresh=False, timeout_seconds=10),
                timeout=15.0  # Maximum 15 seconds for cloud environments
            )
            logger.info(f"GTFS data loaded: {len(gtfs_data.routes)} routes, {len(gtfs_data.stops)} stops")
            
        except asyncio.TimeoutError:
            logger.warning("GTFS data loading timed out - using empty dataset")
            gtfs_data = GTFSData()
        except Exception as e:
            logger.warning(f"GTFS data loading failed: {e} - using empty dataset")
            gtfs_data = GTFSData()
        
        # Start realtime polling (non-blocking now)
        try:
            await realtime_poller.start()
            logger.info("Real-time polling started successfully")
        except Exception as e:
            logger.warning(f"Real-time polling failed to start: {e} - continuing without real-time data")
            realtime_poller.data = RealtimeData()
        
        initialized = True
        logger.info("Server initialization completed")


def _is_cloud_environment() -> bool:
    """Detect if running in FastMCP Cloud or similar environment."""
    return (
        os.environ.get('FASTMCP_CLOUD') or
        os.environ.get('LAMBDA_RUNTIME_DIR') or
        os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or
        (os.path.exists('/tmp') and not os.path.exists(os.path.expanduser('~')))
    )


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
    """Ultra-fast health check optimized for cloud pre-flight validation."""
    is_cloud = _is_cloud_environment()
    
    # For cloud pre-flight: return immediately without any data loading
    if is_cloud:
        return {
            "status": "healthy",
            "server": "catabus-mcp",
            "version": "0.1.0",
            "environment": "cloud",
            "startup_mode": "optimized",
            "server_time": datetime.now(timezone.utc).isoformat(),
            "pre_flight": "ready"
        }
    
    # For local development: provide more detailed status
    return {
        "status": "healthy",
        "initialized": initialized,
        "routes_loaded": len(gtfs_data.routes) if gtfs_data else 0,
        "stops_loaded": len(gtfs_data.stops) if gtfs_data else 0,
        "last_static_update": gtfs_data.last_updated.isoformat() if gtfs_data and gtfs_data.last_updated else None,
        "last_vehicle_update": realtime_poller.data.last_vehicle_update.isoformat() if realtime_poller.data.last_vehicle_update else None,
        "last_trip_update": realtime_poller.data.last_trip_update.isoformat() if realtime_poller.data.last_trip_update else None,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "environment": "local",
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


# FastMCP Cloud entry point
server = mcp


def main():
    """Entry point for CLI usage via pyproject.toml scripts."""
    mcp.run()


# Standard FastMCP pattern - let FastMCP handle transport selection
if __name__ == "__main__":
    mcp.run()