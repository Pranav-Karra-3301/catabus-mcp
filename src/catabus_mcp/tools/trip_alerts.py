"""MCP tool for getting service alerts."""

from typing import Any, Dict, List, Optional

from ..ingest.realtime_poll import RealtimeData


async def trip_alerts(realtime_data: RealtimeData, route_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get current service alerts.
    
    Args:
        realtime_data: The GTFS realtime data.
        route_id: Optional route ID to filter alerts (if None, returns all).
    
    Returns:
        List of alerts with route ID, header, description, and severity.
    """
    alerts = []
    
    for alert in realtime_data.alerts:
        # Check if this alert is relevant to the requested route
        if route_id:
            relevant = False
            for entity in alert.informed_entities:
                if entity.get("route_id") == route_id:
                    relevant = True
                    break
            if not relevant:
                continue
        
        # Get affected route IDs
        affected_routes = []
        for entity in alert.informed_entities:
            if "route_id" in entity:
                affected_routes.append(entity["route_id"])
        
        alerts.append({
            "route_id": affected_routes[0] if len(affected_routes) == 1 else None,
            "affected_routes": affected_routes,
            "header": alert.header,
            "description": alert.description,
            "severity": alert.severity,
        })
    
    return alerts