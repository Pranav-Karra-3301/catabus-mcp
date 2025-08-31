"""Static GTFS feed loader for CATA bus data."""

import csv
import io
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import aiohttp

logger = logging.getLogger(__name__)

GTFS_STATIC_URL = "https://catabus.com/wp-content/uploads/google_transit.zip"
CACHE_DIR = Path("cache")


@dataclass
class Stop:
    stop_id: str
    stop_name: str
    stop_lat: float
    stop_lon: float
    stop_code: Optional[str] = None
    stop_desc: Optional[str] = None


@dataclass
class Route:
    route_id: str
    route_short_name: str
    route_long_name: str
    route_type: int
    route_color: Optional[str] = None
    route_text_color: Optional[str] = None


@dataclass
class Trip:
    trip_id: str
    route_id: str
    service_id: str
    trip_headsign: Optional[str] = None
    direction_id: Optional[int] = None
    shape_id: Optional[str] = None


@dataclass
class StopTime:
    trip_id: str
    arrival_time: str
    departure_time: str
    stop_id: str
    stop_sequence: int
    pickup_type: Optional[int] = None
    drop_off_type: Optional[int] = None


@dataclass
class GTFSData:
    routes: Dict[str, Route] = field(default_factory=dict)
    stops: Dict[str, Stop] = field(default_factory=dict)
    trips: Dict[str, Trip] = field(default_factory=dict)
    stop_times: List[StopTime] = field(default_factory=list)
    shapes: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    last_updated: Optional[datetime] = None


class StaticGTFSLoader:
    def __init__(self):
        self.data = GTFSData()
        CACHE_DIR.mkdir(exist_ok=True)

    async def download_feed(self) -> bytes:
        """Download the static GTFS feed."""
        async with aiohttp.ClientSession() as session:
            async with session.get(GTFS_STATIC_URL) as response:
                response.raise_for_status()
                return await response.read()

    def parse_csv(self, content: str) -> List[Dict[str, str]]:
        """Parse CSV content into list of dictionaries."""
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)

    async def load_feed(self, force_refresh: bool = False) -> GTFSData:
        """Load and parse the GTFS static feed."""
        cache_file = CACHE_DIR / "google_transit.zip"
        
        # Check cache
        if not force_refresh and cache_file.exists():
            # Check if cache is less than 24 hours old
            age = datetime.now().timestamp() - cache_file.stat().st_mtime
            if age < 86400:  # 24 hours
                logger.info("Using cached GTFS feed")
                async with aiofiles.open(cache_file, "rb") as f:
                    feed_data = await f.read()
            else:
                logger.info("Cache expired, downloading fresh feed")
                feed_data = await self.download_feed()
                async with aiofiles.open(cache_file, "wb") as f:
                    await f.write(feed_data)
        else:
            logger.info("Downloading GTFS feed")
            feed_data = await self.download_feed()
            async with aiofiles.open(cache_file, "wb") as f:
                await f.write(feed_data)

        # Parse the feed
        with zipfile.ZipFile(io.BytesIO(feed_data)) as zf:
            # Load routes
            if "routes.txt" in zf.namelist():
                content = zf.read("routes.txt").decode("utf-8-sig")
                for row in self.parse_csv(content):
                    route = Route(
                        route_id=row["route_id"],
                        route_short_name=row.get("route_short_name", ""),
                        route_long_name=row.get("route_long_name", ""),
                        route_type=int(row.get("route_type", 3)),
                        route_color=row.get("route_color"),
                        route_text_color=row.get("route_text_color"),
                    )
                    self.data.routes[route.route_id] = route

            # Load stops
            if "stops.txt" in zf.namelist():
                content = zf.read("stops.txt").decode("utf-8-sig")
                for row in self.parse_csv(content):
                    stop = Stop(
                        stop_id=row["stop_id"],
                        stop_name=row["stop_name"],
                        stop_lat=float(row["stop_lat"]),
                        stop_lon=float(row["stop_lon"]),
                        stop_code=row.get("stop_code"),
                        stop_desc=row.get("stop_desc"),
                    )
                    self.data.stops[stop.stop_id] = stop

            # Load trips
            if "trips.txt" in zf.namelist():
                content = zf.read("trips.txt").decode("utf-8-sig")
                for row in self.parse_csv(content):
                    trip = Trip(
                        trip_id=row["trip_id"],
                        route_id=row["route_id"],
                        service_id=row["service_id"],
                        trip_headsign=row.get("trip_headsign"),
                        direction_id=int(row["direction_id"]) if row.get("direction_id") else None,
                        shape_id=row.get("shape_id"),
                    )
                    self.data.trips[trip.trip_id] = trip

            # Load stop times
            if "stop_times.txt" in zf.namelist():
                content = zf.read("stop_times.txt").decode("utf-8-sig")
                for row in self.parse_csv(content):
                    stop_time = StopTime(
                        trip_id=row["trip_id"],
                        arrival_time=row["arrival_time"],
                        departure_time=row["departure_time"],
                        stop_id=row["stop_id"],
                        stop_sequence=int(row["stop_sequence"]),
                        pickup_type=int(row["pickup_type"]) if row.get("pickup_type") else None,
                        drop_off_type=int(row["drop_off_type"]) if row.get("drop_off_type") else None,
                    )
                    self.data.stop_times.append(stop_time)

            # Load shapes (optional)
            if "shapes.txt" in zf.namelist():
                content = zf.read("shapes.txt").decode("utf-8-sig")
                for row in self.parse_csv(content):
                    shape_id = row["shape_id"]
                    if shape_id not in self.data.shapes:
                        self.data.shapes[shape_id] = []
                    self.data.shapes[shape_id].append({
                        "lat": float(row["shape_pt_lat"]),
                        "lon": float(row["shape_pt_lon"]),
                        "sequence": int(row["shape_pt_sequence"]),
                    })

        self.data.last_updated = datetime.now()
        logger.info(f"Loaded {len(self.data.routes)} routes, {len(self.data.stops)} stops, "
                   f"{len(self.data.trips)} trips, {len(self.data.stop_times)} stop times")
        
        return self.data