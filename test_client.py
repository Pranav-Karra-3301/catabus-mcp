#!/usr/bin/env python3
"""Test client for CATA Bus MCP server."""

import asyncio
import json
from typing import Any, Dict

import httpx


class CATABusClient:
    def __init__(self, base_url: str = "http://localhost:8765/mcp"):
        self.base_url = base_url
        self.session_id = None
        self.client = httpx.AsyncClient()

    async def initialize(self):
        """Initialize session with the server."""
        response = await self.client.post(
            self.base_url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "1.0",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0"
                    }
                },
                "id": 1
            }
        )
        
        # Extract session ID from response headers or create one
        self.session_id = response.headers.get("x-session-id", "test-session")
        return response.json()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None):
        """Call a tool on the server."""
        if not self.session_id:
            await self.initialize()
        
        response = await self.client.post(
            self.base_url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "x-session-id": self.session_id,
            },
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {}
                },
                "id": 2
            }
        )
        return response.json()

    async def close(self):
        """Close the client."""
        await self.client.aclose()


async def main():
    """Test the CATA Bus MCP server."""
    client = CATABusClient()
    
    try:
        print("🚌 Testing CATA Bus MCP Server\n")
        
        # List all routes
        print("1. Listing all bus routes:")
        print("-" * 40)
        result = await client.call_tool("list_routes_tool")
        if "result" in result:
            routes = result["result"]
            # Look for Blue Loop (BL)
            for route in routes[:10]:  # Show first 10 routes
                print(f"  • {route['short_name']}: {route['long_name']}")
                if route['color']:
                    print(f"    Color: {route['color']}")
            print(f"  ... and {len(routes) - 10} more routes\n")
        else:
            print(f"  Error: {result}\n")
        
        # Search for stops containing "HUB"
        print("2. Searching for stops containing 'HUB':")
        print("-" * 40)
        result = await client.call_tool("search_stops_tool", {"query": "HUB"})
        if "result" in result:
            stops = result["result"]
            for stop in stops[:5]:
                print(f"  • {stop['name']} (ID: {stop['stop_id']})")
                print(f"    Location: {stop['lat']}, {stop['lon']}")
            if len(stops) > 5:
                print(f"  ... and {len(stops) - 5} more stops\n")
        else:
            print(f"  Error: {result}\n")
        
        # Get Blue Loop vehicle positions
        print("3. Getting Blue Loop (BL) vehicle positions:")
        print("-" * 40)
        result = await client.call_tool("vehicle_positions_tool", {"route_id": "BL"})
        if "result" in result:
            vehicles = result["result"]
            if vehicles:
                for vehicle in vehicles:
                    print(f"  • Vehicle {vehicle['vehicle_id']}:")
                    print(f"    Location: {vehicle['lat']}, {vehicle['lon']}")
                    if vehicle.get('speed_mps'):
                        print(f"    Speed: {vehicle['speed_mps'] * 2.237:.1f} mph")
                    if vehicle.get('bearing'):
                        print(f"    Heading: {vehicle['bearing']}°")
            else:
                print("  No Blue Loop vehicles currently active")
        else:
            print(f"  Error: {result}\n")
        
        # Get next arrivals at a stop
        print("\n4. Getting next arrivals at PSU HUB:")
        print("-" * 40)
        result = await client.call_tool("next_arrivals_tool", {
            "stop_id": "PSU_HUB",
            "horizon_minutes": 60
        })
        if "result" in result:
            arrivals = result["result"]
            if arrivals:
                for arrival in arrivals[:10]:
                    print(f"  • Route {arrival['route_id']} - Trip {arrival['trip_id']}")
                    print(f"    Arrival: {arrival['arrival_time_iso']}")
                    if arrival.get('delay_sec'):
                        delay_min = arrival['delay_sec'] / 60
                        if delay_min > 0:
                            print(f"    Status: {delay_min:.1f} minutes late")
                        elif delay_min < 0:
                            print(f"    Status: {-delay_min:.1f} minutes early")
                        else:
                            print("    Status: On time")
            else:
                print("  No arrivals in the next 60 minutes")
        else:
            print(f"  Error: {result}\n")
        
        # Get service alerts
        print("\n5. Getting service alerts:")
        print("-" * 40)
        result = await client.call_tool("trip_alerts_tool")
        if "result" in result:
            alerts = result["result"]
            if alerts:
                for alert in alerts[:5]:
                    print(f"  • {alert['header']}")
                    if alert.get('description'):
                        print(f"    {alert['description']}")
                    print(f"    Severity: {alert['severity']}")
                    if alert.get('affected_routes'):
                        print(f"    Affected routes: {', '.join(alert['affected_routes'])}")
            else:
                print("  No active service alerts")
        else:
            print(f"  Error: {result}\n")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())