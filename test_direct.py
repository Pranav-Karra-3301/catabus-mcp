#!/usr/bin/env python3
"""Direct test of CATA Bus server functions."""

import asyncio
import json
from src.catabus_mcp.server import (
    list_routes_tool,
    search_stops_tool,
    vehicle_positions_tool,
    next_arrivals_tool,
    trip_alerts_tool,
    health_check
)


async def main():
    """Test the server functions directly."""
    print("🚌 Testing CATA Bus MCP Server Functions Directly\n")
    
    # Test 1: List routes
    print("1. Listing all bus routes:")
    print("-" * 40)
    routes = await list_routes_tool()
    
    # Find Blue Loop
    blue_loop = None
    for route in routes[:5]:
        print(f"  • {route['short_name']}: {route['long_name']}")
        if route.get('color'):
            print(f"    Color: {route['color']}")
        if route['short_name'] == 'BL':
            blue_loop = route
    
    # Check if we found BL later in the list
    if not blue_loop:
        for route in routes:
            if route['short_name'] == 'BL':
                blue_loop = route
                break
    
    if blue_loop:
        print(f"\n  ✅ Found Blue Loop (BL): {blue_loop['long_name']}")
        if blue_loop.get('color'):
            print(f"    Color: {blue_loop['color']}")
    
    print(f"\n  Total routes: {len(routes)}")
    
    # Test 2: Search stops
    print("\n2. Searching for stops containing 'Curtin':")
    print("-" * 40)
    stops = await search_stops_tool("Curtin")
    
    for stop in stops[:3]:
        print(f"  • {stop['name']} (ID: {stop['stop_id']})")
        print(f"    Location: ({stop['lat']:.6f}, {stop['lon']:.6f})")
    
    if stops:
        print(f"\n  Found {len(stops)} stops matching 'Curtin'")
        test_stop_id = stops[0]['stop_id']
    else:
        test_stop_id = None
    
    # Test 3: Blue Loop vehicles
    print("\n3. Getting Blue Loop (BL) vehicle positions:")
    print("-" * 40)
    vehicles = await vehicle_positions_tool("BL")
    
    if vehicles:
        for vehicle in vehicles:
            print(f"  • Vehicle {vehicle['vehicle_id']}:")
            print(f"    Location: ({vehicle['lat']:.6f}, {vehicle['lon']:.6f})")
            if vehicle.get('speed_mps') is not None:
                speed_mph = vehicle['speed_mps'] * 2.237
                print(f"    Speed: {speed_mph:.1f} mph")
    else:
        print("  No Blue Loop vehicles currently active")
        print("  (Normal outside service hours)")
    
    # Test 4: Next arrivals
    if test_stop_id:
        print(f"\n4. Next arrivals at {test_stop_id}:")
        print("-" * 40)
        arrivals = await next_arrivals_tool(test_stop_id, 60)
        
        if arrivals:
            for arrival in arrivals[:5]:
                print(f"  • Route {arrival['route_id']}")
                print(f"    Arrival: {arrival['arrival_time_iso']}")
                if arrival.get('delay_sec'):
                    delay_min = arrival['delay_sec'] / 60
                    if delay_min > 0:
                        print(f"    Status: {delay_min:.1f} minutes late")
                    elif delay_min < 0:
                        print(f"    Status: {-delay_min:.1f} minutes early")
        else:
            print("  No arrivals in next 60 minutes")
    
    # Test 5: Alerts
    print("\n5. Service alerts:")
    print("-" * 40)
    alerts = await trip_alerts_tool()
    
    if alerts:
        for alert in alerts[:3]:
            print(f"  • {alert['header']}")
            if alert.get('description'):
                print(f"    {alert['description']}")
            print(f"    Severity: {alert['severity']}")
    else:
        print("  No active service alerts")
    
    # Test 6: Health check
    print("\n6. Health check:")
    print("-" * 40)
    health = await health_check()
    print(f"  • Status: {health['status']}")
    print(f"  • Routes loaded: {health['routes_loaded']}")
    print(f"  • Stops loaded: {health['stops_loaded']}")
    
    print("\n✅ All tests complete!")


if __name__ == "__main__":
    asyncio.run(main())