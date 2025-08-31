"""MCP tool for getting vehicle positions."""

from typing import Any, Dict, List

from ..ingest.realtime_poll import RealtimeData


async def vehicle_positions(realtime_data: RealtimeData, route_id: str) -> List[Dict[str, Any]]:
    """
    Get current positions of vehicles on a specific route.
    
    Args:
        realtime_data: The GTFS realtime data.
        route_id: The route ID to filter by.
    
    Returns:
        List of vehicle positions with ID, coordinates, bearing, and speed.
    """
    vehicles = []
    
    for vehicle_id, position in realtime_data.vehicle_positions.items():
        # Filter by route if specified
        if position.route_id == route_id:
            vehicles.append({
                "vehicle_id": vehicle_id,
                "lat": position.latitude,
                "lon": position.longitude,
                "bearing": position.bearing,
                "speed_mps": position.speed,
            })
    
    return vehicles