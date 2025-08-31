"""MCP tool for searching stops."""

from typing import Any, Dict, List

from ..ingest.static_loader import GTFSData


async def search_stops(gtfs_data: GTFSData, query: str) -> List[Dict[str, Any]]:
    """
    Search for stops by name or ID.
    
    Args:
        gtfs_data: The GTFS static data.
        query: Search query string.
    
    Returns:
        List of matching stops with id, name, latitude, and longitude.
    """
    query_lower = query.lower()
    results = []
    
    for stop_id, stop in gtfs_data.stops.items():
        # Search in stop ID, name, code, and description
        if (query_lower in stop.stop_id.lower() or
            query_lower in stop.stop_name.lower() or
            (stop.stop_code and query_lower in stop.stop_code.lower()) or
            (stop.stop_desc and query_lower in stop.stop_desc.lower())):
            
            results.append({
                "stop_id": stop.stop_id,
                "name": stop.stop_name,
                "lat": stop.stop_lat,
                "lon": stop.stop_lon,
            })
    
    # Sort by name for consistency
    results.sort(key=lambda x: x["name"])
    return results