"""MCP tool for getting next arrivals at a stop."""

from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytz

from ..ingest.realtime_poll import RealtimeData
from ..ingest.static_loader import GTFSData


def parse_gtfs_time(time_str: str) -> time:
    """Parse GTFS time format (can be > 24:00:00 for next day)."""
    parts = time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2]) if len(parts) > 2 else 0
    
    # Handle times after midnight (e.g., 25:30:00)
    days_offset = hours // 24
    hours = hours % 24
    
    return time(hours, minutes, seconds), days_offset


async def next_arrivals(
    gtfs_data: GTFSData,
    realtime_data: RealtimeData,
    stop_id: str,
    horizon_minutes: int = 30
) -> List[Dict[str, Any]]:
    """
    Get next arrivals at a specific stop.
    
    Args:
        gtfs_data: The GTFS static data.
        realtime_data: The GTFS realtime data.
        stop_id: The stop ID to query.
        horizon_minutes: How many minutes ahead to look (default 30).
    
    Returns:
        List of upcoming arrivals with trip ID, route ID, arrival time, and delay.
    """
    # Get current time in Eastern timezone (CATA operates in ET)
    eastern = pytz.timezone("America/New_York")
    now = datetime.now(eastern)
    horizon = now + timedelta(minutes=horizon_minutes)
    
    arrivals = []
    
    # First, get scheduled arrivals from static data
    scheduled = {}
    for stop_time in gtfs_data.stop_times:
        if stop_time.stop_id != stop_id:
            continue
        
        # Parse arrival time
        arrival_time, days_offset = parse_gtfs_time(stop_time.arrival_time)
        scheduled_datetime = datetime.combine(
            now.date() + timedelta(days=days_offset),
            arrival_time,
            eastern
        )
        
        # Check if within horizon
        if now <= scheduled_datetime <= horizon:
            trip = gtfs_data.trips.get(stop_time.trip_id)
            if trip:
                scheduled[stop_time.trip_id] = {
                    "trip_id": stop_time.trip_id,
                    "route_id": trip.route_id,
                    "scheduled_arrival": scheduled_datetime,
                    "stop_sequence": stop_time.stop_sequence,
                }
    
    # Apply realtime updates
    for trip_id, scheduled_info in scheduled.items():
        arrival_info = {
            "trip_id": trip_id,
            "route_id": scheduled_info["route_id"],
            "arrival_time_iso": scheduled_info["scheduled_arrival"].isoformat(),
            "delay_sec": 0,
        }
        
        # Check for realtime updates
        if trip_id in realtime_data.trip_updates:
            trip_update = realtime_data.trip_updates[trip_id]
            
            # Find the stop time update for this stop
            for stu in trip_update.stop_time_updates:
                if stu.get("stop_id") == stop_id:
                    if "arrival_delay" in stu:
                        arrival_info["delay_sec"] = stu["arrival_delay"]
                        # Adjust arrival time with delay
                        adjusted_arrival = scheduled_info["scheduled_arrival"] + timedelta(seconds=stu["arrival_delay"])
                        arrival_info["arrival_time_iso"] = adjusted_arrival.isoformat()
                    elif "arrival_time" in stu and stu["arrival_time"]:
                        # Use absolute arrival time if provided
                        arrival_dt = datetime.fromtimestamp(stu["arrival_time"], tz=timezone.utc)
                        arrival_info["arrival_time_iso"] = arrival_dt.isoformat()
                        # Calculate delay
                        arrival_info["delay_sec"] = int((arrival_dt - scheduled_info["scheduled_arrival"]).total_seconds())
                    break
        
        arrivals.append(arrival_info)
    
    # Sort by arrival time
    arrivals.sort(key=lambda x: x["arrival_time_iso"])
    
    return arrivals