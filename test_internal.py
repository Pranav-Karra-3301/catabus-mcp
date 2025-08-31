#!/usr/bin/env python3
"""Test CATA Bus server by calling the internal functions."""

import asyncio
from src.catabus_mcp.server import (
    ensure_initialized,
    list_routes,
    search_stops,
    vehicle_positions,
    next_arrivals,
    trip_alerts,
    gtfs_data,
    realtime_poller
)


async def main():
    """Test the server functions directly."""
    print("🚌 Testing CATA Bus MCP Server Internal Functions\n")
    
    # Initialize data
    print("Initializing GTFS data...")
    await ensure_initialized()
    print(f"✅ Loaded data successfully\n")
    
    # Test 1: List routes
    print("1. Listing all bus routes:")
    print("-" * 40)
    from src.catabus_mcp.server_v2 import gtfs_data
    
    if gtfs_data:
        routes = await list_routes(gtfs_data)
        
        # Find Blue Loop
        blue_loop = None
        white_loop = None
        for route in routes[:8]:
            print(f"  • {route['short_name']}: {route['long_name']}")
            if route.get('color'):
                print(f"    Color: {route['color']}")
            if route['short_name'] == 'BL':
                blue_loop = route
            elif route['short_name'] == 'WL':
                white_loop = route
        
        # Check if we found BL/WL later in the list
        if not blue_loop or not white_loop:
            for route in routes:
                if route['short_name'] == 'BL':
                    blue_loop = route
                elif route['short_name'] == 'WL':
                    white_loop = route
        
        if blue_loop:
            print(f"\n  ✅ Found Blue Loop (BL): {blue_loop['long_name']}")
            if blue_loop.get('color'):
                print(f"    Color: {blue_loop['color']}")
        
        if white_loop:
            print(f"  ✅ Found White Loop (WL): {white_loop['long_name']}")
            if white_loop.get('color'):
                print(f"    Color: {white_loop['color']}")
        
        print(f"\n  Total routes: {len(routes)}")
    
    # Test 2: Search stops
    print("\n2. Searching for stops:")
    print("-" * 40)
    
    # Search for different stop names
    search_terms = ["HUB", "Curtin", "Atherton", "Beaver"]
    
    for term in search_terms:
        stops = await search_stops(gtfs_data, term)
        if stops:
            print(f"\n  Searching for '{term}':")
            for stop in stops[:2]:
                print(f"    • {stop['name']} (ID: {stop['stop_id']})")
            print(f"    Found {len(stops)} total matches")
    
    # Get a stop ID for testing
    hub_stops = await search_stops(gtfs_data, "HUB")
    test_stop_id = hub_stops[0]['stop_id'] if hub_stops else None
    
    # Test 3: Vehicle positions for different routes
    print("\n3. Checking vehicle positions:")
    print("-" * 40)
    
    routes_to_check = ["BL", "WL", "N", "V"]
    active_routes = []
    
    for route_id in routes_to_check:
        vehicles = await vehicle_positions(realtime_poller.data, route_id)
        if vehicles:
            active_routes.append(route_id)
            print(f"\n  Route {route_id}: {len(vehicles)} vehicle(s) active")
            for vehicle in vehicles[:2]:
                print(f"    • Vehicle {vehicle['vehicle_id']}")
                print(f"      Location: ({vehicle['lat']:.6f}, {vehicle['lon']:.6f})")
                if vehicle.get('speed_mps') is not None:
                    speed_mph = vehicle['speed_mps'] * 2.237
                    print(f"      Speed: {speed_mph:.1f} mph")
    
    if not active_routes:
        print("  No vehicles currently active (normal outside service hours)")
    else:
        print(f"\n  Active routes: {', '.join(active_routes)}")
    
    # Test 4: Next arrivals
    if test_stop_id:
        print(f"\n4. Next arrivals at {test_stop_id}:")
        print("-" * 40)
        arrivals = await next_arrivals(gtfs_data, realtime_poller.data, test_stop_id, 120)
        
        if arrivals:
            # Group by route
            routes_with_arrivals = {}
            for arrival in arrivals:
                route = arrival['route_id']
                if route not in routes_with_arrivals:
                    routes_with_arrivals[route] = []
                routes_with_arrivals[route].append(arrival)
            
            print(f"  Found arrivals for {len(routes_with_arrivals)} routes:")
            for route_id, route_arrivals in list(routes_with_arrivals.items())[:5]:
                print(f"\n  Route {route_id}: {len(route_arrivals)} arrival(s)")
                for arrival in route_arrivals[:2]:
                    print(f"    • {arrival['arrival_time_iso']}")
                    if arrival.get('delay_sec'):
                        delay_min = arrival['delay_sec'] / 60
                        if abs(delay_min) > 0.5:
                            status = f"{abs(delay_min):.1f} min {'late' if delay_min > 0 else 'early'}"
                            print(f"      Status: {status}")
        else:
            print("  No arrivals in next 2 hours")
    
    # Test 5: Alerts
    print("\n5. Service alerts:")
    print("-" * 40)
    alerts = await trip_alerts(realtime_poller.data)
    
    if alerts:
        for alert in alerts[:5]:
            print(f"  • {alert['header']}")
            if alert.get('description'):
                desc = alert['description'][:100] + "..." if len(alert['description']) > 100 else alert['description']
                print(f"    {desc}")
            print(f"    Severity: {alert['severity']}")
            if alert.get('affected_routes'):
                print(f"    Routes: {', '.join(alert['affected_routes'][:5])}")
    else:
        print("  No active service alerts")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY:")
    print(f"  • Routes loaded: {len(gtfs_data.routes)}")
    print(f"  • Stops loaded: {len(gtfs_data.stops)}")
    print(f"  • Trips loaded: {len(gtfs_data.trips)}")
    print(f"  • Stop times loaded: {len(gtfs_data.stop_times)}")
    print(f"  • Active vehicles: {len(realtime_poller.data.vehicle_positions)}")
    print(f"  • Active trip updates: {len(realtime_poller.data.trip_updates)}")
    print(f"  • Active alerts: {len(realtime_poller.data.alerts)}")
    
    print("\n✅ All tests complete!")


if __name__ == "__main__":
    asyncio.run(main())