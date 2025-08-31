"""MCP tool for listing all routes."""

from typing import Any, Dict, List

from ..ingest.static_loader import GTFSData


async def list_routes(gtfs_data: GTFSData) -> List[Dict[str, Any]]:
    """
    List all available bus routes.
    
    Returns:
        List of route information with id, short name, long name, and color.
    """
    routes = []
    for route_id, route in gtfs_data.routes.items():
        routes.append({
            "route_id": route.route_id,
            "short_name": route.route_short_name,
            "long_name": route.route_long_name,
            "color": f"#{route.route_color}" if route.route_color else None,
        })
    
    # Sort by short name for consistency
    routes.sort(key=lambda x: x["short_name"])
    return routes