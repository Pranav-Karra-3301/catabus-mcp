"""Realtime GTFS feed poller for CATA bus data."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

import aiohttp
from google.transit import gtfs_realtime_pb2
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# GTFS-RT endpoints (without debug parameter for protobuf format)
VEHICLE_POSITIONS_URL = "https://realtime.catabus.com/InfoPoint/GTFS-Realtime.ashx?Type=VehiclePosition"
TRIP_UPDATES_URL = "https://realtime.catabus.com/InfoPoint/GTFS-Realtime.ashx?Type=TripUpdate"
ALERTS_URL = "https://realtime.catabus.com/InfoPoint/GTFS-Realtime.ashx?Type=Alert"

# Rate limit: minimum 10 seconds between requests to same endpoint
MIN_POLL_INTERVAL = 15  # seconds


class VehiclePosition(BaseModel):
    vehicle_id: str
    trip_id: Optional[str] = None
    route_id: Optional[str] = None
    latitude: float
    longitude: float
    bearing: Optional[float] = None
    speed: Optional[float] = None  # meters per second
    timestamp: datetime
    occupancy_status: Optional[str] = None


class TripUpdate(BaseModel):
    trip_id: str
    route_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    timestamp: datetime
    stop_time_updates: List[Dict] = field(default_factory=list)


class ServiceAlert(BaseModel):
    alert_id: str
    header: str
    description: Optional[str] = None
    severity: str = "UNKNOWN"
    active_periods: List[Dict] = field(default_factory=list)
    informed_entities: List[Dict] = field(default_factory=list)


@dataclass
class RealtimeData:
    vehicle_positions: Dict[str, VehiclePosition] = field(default_factory=dict)
    trip_updates: Dict[str, TripUpdate] = field(default_factory=dict)
    alerts: List[ServiceAlert] = field(default_factory=list)
    last_vehicle_update: Optional[datetime] = None
    last_trip_update: Optional[datetime] = None
    last_alert_update: Optional[datetime] = None


class RealtimeGTFSPoller:
    def __init__(self):
        self.data = RealtimeData()
        self._running = False
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        """Start the polling tasks."""
        if self._running:
            return
        
        self._running = True
        self._session = aiohttp.ClientSession()
        
        # Start three separate polling tasks with staggered starts
        asyncio.create_task(self._poll_vehicle_positions())
        await asyncio.sleep(5)  # Stagger to avoid hitting all endpoints at once
        asyncio.create_task(self._poll_trip_updates())
        await asyncio.sleep(5)
        asyncio.create_task(self._poll_alerts())

    async def stop(self):
        """Stop the polling tasks."""
        self._running = False
        if self._session:
            await self._session.close()

    async def _fetch_protobuf(self, url: str) -> Optional[bytes]:
        """Fetch protobuf data from URL."""
        if not self._session:
            return None
        
        try:
            async with self._session.get(url, timeout=30) as response:
                response.raise_for_status()
                return await response.read()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    async def _poll_vehicle_positions(self):
        """Poll vehicle positions endpoint."""
        while self._running:
            try:
                data = await self._fetch_protobuf(VEHICLE_POSITIONS_URL)
                if data:
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(data)
                    
                    positions = {}
                    for entity in feed.entity:
                        if entity.HasField('vehicle'):
                            vehicle = entity.vehicle
                            if vehicle.HasField('position'):
                                pos = VehiclePosition(
                                    vehicle_id=vehicle.vehicle.id if vehicle.vehicle.id else entity.id,
                                    trip_id=vehicle.trip.trip_id if vehicle.HasField('trip') else None,
                                    route_id=vehicle.trip.route_id if vehicle.HasField('trip') else None,
                                    latitude=vehicle.position.latitude,
                                    longitude=vehicle.position.longitude,
                                    bearing=vehicle.position.bearing if vehicle.position.HasField('bearing') else None,
                                    speed=vehicle.position.speed if vehicle.position.HasField('speed') else None,
                                    timestamp=datetime.fromtimestamp(vehicle.timestamp, tz=timezone.utc),
                                    occupancy_status=self._get_occupancy_status(vehicle.occupancy_status) if vehicle.HasField('occupancy_status') else None,
                                )
                                positions[pos.vehicle_id] = pos
                    
                    self.data.vehicle_positions = positions
                    self.data.last_vehicle_update = datetime.now(timezone.utc)
                    logger.debug(f"Updated {len(positions)} vehicle positions")
                    
            except Exception as e:
                logger.error(f"Error polling vehicle positions: {e}")
            
            await asyncio.sleep(MIN_POLL_INTERVAL)

    async def _poll_trip_updates(self):
        """Poll trip updates endpoint."""
        while self._running:
            try:
                data = await self._fetch_protobuf(TRIP_UPDATES_URL)
                if data:
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(data)
                    
                    updates = {}
                    for entity in feed.entity:
                        if entity.HasField('trip_update'):
                            trip_update = entity.trip_update
                            
                            stop_time_updates = []
                            for stu in trip_update.stop_time_update:
                                update = {
                                    "stop_id": stu.stop_id,
                                    "stop_sequence": stu.stop_sequence if stu.HasField('stop_sequence') else None,
                                }
                                
                                if stu.HasField('arrival'):
                                    update["arrival_delay"] = stu.arrival.delay if stu.arrival.HasField('delay') else 0
                                    update["arrival_time"] = stu.arrival.time if stu.arrival.HasField('time') else None
                                
                                if stu.HasField('departure'):
                                    update["departure_delay"] = stu.departure.delay if stu.departure.HasField('delay') else 0
                                    update["departure_time"] = stu.departure.time if stu.departure.HasField('time') else None
                                
                                stop_time_updates.append(update)
                            
                            update = TripUpdate(
                                trip_id=trip_update.trip.trip_id,
                                route_id=trip_update.trip.route_id if trip_update.trip.HasField('route_id') else None,
                                vehicle_id=trip_update.vehicle.id if trip_update.HasField('vehicle') else None,
                                timestamp=datetime.fromtimestamp(trip_update.timestamp, tz=timezone.utc) if trip_update.HasField('timestamp') else datetime.now(timezone.utc),
                                stop_time_updates=stop_time_updates,
                            )
                            updates[update.trip_id] = update
                    
                    self.data.trip_updates = updates
                    self.data.last_trip_update = datetime.now(timezone.utc)
                    logger.info(f"Successfully updated {len(updates)} trip updates.")
                else:
                    logger.warning("No data received from trip updates endpoint.")

            except Exception as e:
                logger.error(f"An exception occurred while polling trip updates: {e}", exc_info=True)
            
            await asyncio.sleep(MIN_POLL_INTERVAL)

    async def _poll_alerts(self):
        """Poll service alerts endpoint."""
        while self._running:
            try:
                data = await self._fetch_protobuf(ALERTS_URL)
                if data:
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(data)
                    
                    alerts = []
                    for entity in feed.entity:
                        if entity.HasField('alert'):
                            alert = entity.alert
                            
                            # Get header text (handling translations)
                            header_text = ""
                            if alert.HasField('header_text'):
                                for translation in alert.header_text.translation:
                                    if translation.language == "en" or not header_text:
                                        header_text = translation.text
                            
                            # Get description text
                            description_text = ""
                            if alert.HasField('description_text'):
                                for translation in alert.description_text.translation:
                                    if translation.language == "en" or not description_text:
                                        description_text = translation.text
                            
                            # Get active periods
                            active_periods = []
                            for period in alert.active_period:
                                active_periods.append({
                                    "start": datetime.fromtimestamp(period.start, tz=timezone.utc) if period.HasField('start') else None,
                                    "end": datetime.fromtimestamp(period.end, tz=timezone.utc) if period.HasField('end') else None,
                                })
                            
                            # Get informed entities
                            informed_entities = []
                            for entity in alert.informed_entity:
                                ie = {}
                                if entity.HasField('route_id'):
                                    ie['route_id'] = entity.route_id
                                if entity.HasField('trip'):
                                    ie['trip_id'] = entity.trip.trip_id
                                if entity.HasField('stop_id'):
                                    ie['stop_id'] = entity.stop_id
                                informed_entities.append(ie)
                            
                            service_alert = ServiceAlert(
                                alert_id=entity.id,
                                header=header_text,
                                description=description_text,
                                severity=self._get_severity(alert.severity_level) if alert.HasField('severity_level') else "UNKNOWN",
                                active_periods=active_periods,
                                informed_entities=informed_entities,
                            )
                            alerts.append(service_alert)
                    
                    self.data.alerts = alerts
                    self.data.last_alert_update = datetime.now(timezone.utc)
                    logger.debug(f"Updated {len(alerts)} alerts")
                    
            except Exception as e:
                logger.error(f"Error polling alerts: {e}")
            
            await asyncio.sleep(MIN_POLL_INTERVAL)

    def _get_occupancy_status(self, status: int) -> str:
        """Convert occupancy status enum to string."""
        mapping = {
            0: "EMPTY",
            1: "MANY_SEATS_AVAILABLE",
            2: "FEW_SEATS_AVAILABLE",
            3: "STANDING_ROOM_ONLY",
            4: "CRUSHED_STANDING_ROOM_ONLY",
            5: "FULL",
            6: "NOT_ACCEPTING_PASSENGERS",
        }
        return mapping.get(status, "UNKNOWN")

    def _get_severity(self, level: int) -> str:
        """Convert severity level enum to string."""
        mapping = {
            1: "UNKNOWN",
            2: "INFO",
            3: "WARNING",
            4: "SEVERE",
        }
        return mapping.get(level, "UNKNOWN")