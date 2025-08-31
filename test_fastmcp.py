#!/usr/bin/env python3
"""Test the CATA Bus FastMCP server."""

import asyncio
from fastmcp import Client

# Import the server module
from src.catabus_mcp.server_v2 import mcp


async def test_server():
    """Test the CATA Bus MCP server using FastMCP client."""
    print("🚌 Testing CATA Bus MCP Server with FastMCP Client\n")
    
    # Create a client that connects to our server
    client = Client(mcp)
    
    async with client:
        print("✅ Connected to server\n")
        
        # Test 1: List all routes
        print("1. Listing all bus routes:")
        print("-" * 40)
        try:
            result = await client.call_tool("list_routes_tool", {})
            # FastMCP returns result as a list directly or wrapped in content
            routes = result if isinstance(result, list) else result
            
            # Show first 5 routes and look for Blue Loop
            blue_loop = None
            for i, route in enumerate(routes):
                if i < 5:
                    print(f"  • {route['short_name']}: {route['long_name']}")
                    if route.get('color'):
                        print(f"    Color: {route['color']}")
                if route['short_name'] == 'BL':
                    blue_loop = route
            
            if blue_loop:
                print(f"\n  ✅ Found Blue Loop (BL): {blue_loop['long_name']}")
                if blue_loop.get('color'):
                    print(f"    Color: {blue_loop['color']}")
            
            print(f"\n  Total routes loaded: {len(routes)}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # Test 2: Search for stops
        print("\n2. Searching for stops containing 'Atherton':")
        print("-" * 40)
        try:
            result = await client.call_tool("search_stops_tool", {"query": "Atherton"})
            stops = result.content
            
            if stops:
                for stop in stops[:3]:
                    print(f"  • {stop['name']} (ID: {stop['stop_id']})")
                    print(f"    Location: ({stop['lat']:.6f}, {stop['lon']:.6f})")
                print(f"\n  Found {len(stops)} stops matching 'Atherton'")
                
                # Save stop ID for next test
                test_stop_id = stops[0]['stop_id']
            else:
                print("  No stops found")
                test_stop_id = "PSU_HUB"  # Fallback
        except Exception as e:
            print(f"  ❌ Error: {e}")
            test_stop_id = "PSU_HUB"
        
        # Test 3: Get Blue Loop vehicle positions
        print("\n3. Getting Blue Loop (BL) vehicle positions:")
        print("-" * 40)
        try:
            result = await client.call_tool("vehicle_positions_tool", {"route_id": "BL"})
            vehicles = result.content
            
            if vehicles:
                for vehicle in vehicles:
                    print(f"  • Vehicle {vehicle['vehicle_id']}:")
                    print(f"    Location: ({vehicle['lat']:.6f}, {vehicle['lon']:.6f})")
                    if vehicle.get('speed_mps') is not None:
                        speed_mph = vehicle['speed_mps'] * 2.237
                        print(f"    Speed: {speed_mph:.1f} mph")
                    if vehicle.get('bearing') is not None:
                        print(f"    Heading: {vehicle['bearing']}°")
            else:
                print("  No Blue Loop vehicles currently active")
                print("  (This is normal outside of service hours)")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # Test 4: Get next arrivals
        print(f"\n4. Getting next arrivals at {test_stop_id}:")
        print("-" * 40)
        try:
            result = await client.call_tool("next_arrivals_tool", {
                "stop_id": test_stop_id,
                "horizon_minutes": 60
            })
            arrivals = result.content
            
            if arrivals:
                for arrival in arrivals[:5]:
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
                if len(arrivals) > 5:
                    print(f"\n  ... and {len(arrivals) - 5} more arrivals")
            else:
                print("  No arrivals in the next 60 minutes")
                print("  (This is normal outside of service hours)")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # Test 5: Get service alerts
        print("\n5. Getting service alerts:")
        print("-" * 40)
        try:
            result = await client.call_tool("trip_alerts_tool", {})
            alerts = result.content
            
            if alerts:
                for alert in alerts[:3]:
                    print(f"  • {alert['header']}")
                    if alert.get('description'):
                        print(f"    {alert['description']}")
                    print(f"    Severity: {alert['severity']}")
                    if alert.get('affected_routes'):
                        print(f"    Affected routes: {', '.join(alert['affected_routes'])}")
                if len(alerts) > 3:
                    print(f"\n  ... and {len(alerts) - 3} more alerts")
            else:
                print("  No active service alerts")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # Test 6: Health check
        print("\n6. Server health check:")
        print("-" * 40)
        try:
            result = await client.call_tool("health_check", {})
            health = result.content
            
            print(f"  • Status: {health['status']}")
            print(f"  • Routes loaded: {health['routes_loaded']}")
            print(f"  • Stops loaded: {health['stops_loaded']}")
            if health.get('last_static_update'):
                print(f"  • Last static update: {health['last_static_update']}")
            if health.get('last_vehicle_update'):
                print(f"  • Last vehicle update: {health['last_vehicle_update']}")
            print(f"  • Server time: {health['server_time']}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n✅ All tests complete!")


if __name__ == "__main__":
    asyncio.run(test_server())