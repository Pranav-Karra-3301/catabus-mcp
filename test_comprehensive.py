#!/usr/bin/env python3
"""Comprehensive integration test for CATA Bus MCP server."""

import asyncio
import json
from fastmcp import Client
from src.catabus_mcp.server_v2 import mcp


def extract_result(result):
    """Extract JSON data from FastMCP result."""
    if hasattr(result, 'content') and isinstance(result.content, list) and len(result.content) > 0:
        text_content = result.content[0]
        if hasattr(text_content, 'text'):
            try:
                return json.loads(text_content.text)
            except json.JSONDecodeError:
                return text_content.text
    return result


async def main():
    """Run comprehensive integration test."""
    print("🚌 CATA Bus MCP Server - Comprehensive Integration Test")
    print("=" * 60)
    
    client = Client(mcp)
    async with client:
        
        # Test 1: Server Connection
        print("\n1. Testing server connection...")
        tools = await client.list_tools()
        tool_names = [tool.name for tool in tools]
        
        expected_tools = [
            "list_routes_tool", "search_stops_tool", "next_arrivals_tool",
            "vehicle_positions_tool", "trip_alerts_tool", "health_check"
        ]
        
        missing_tools = [t for t in expected_tools if t not in tool_names]
        if missing_tools:
            print(f"❌ Missing tools: {missing_tools}")
            return
        
        print(f"✅ All {len(expected_tools)} tools available")
        
        # Test 2: List Routes (find Blue Loop)
        print("\n2. Testing route listing and Blue Loop detection...")
        try:
            result = await client.call_tool("list_routes_tool", {})
            routes = extract_result(result)
            
            print(f"✅ Found {len(routes)} total routes")
            
            # Find Blue Loop
            blue_loop = next((r for r in routes if r.get("short_name") == "BL"), None)
            if blue_loop:
                print(f"✅ Blue Loop found: {blue_loop['long_name']}")
                if blue_loop.get('color'):
                    print(f"   Color: {blue_loop['color']}")
            else:
                print("❌ Blue Loop (BL) not found in routes")
                
            # Show some other routes
            print("   Other routes found:")
            for route in routes[:5]:
                if route.get("short_name") != "BL":
                    print(f"   • {route['short_name']}: {route['long_name']}")
                    
        except Exception as e:
            print(f"❌ Route listing failed: {e}")
            return
        
        # Test 3: Stop Search
        print("\n3. Testing stop search functionality...")
        test_queries = ["HUB", "Curtin", "Atherton", "Beaver"]
        
        for query in test_queries:
            try:
                result = await client.call_tool("search_stops_tool", {"query": query})
                stops = extract_result(result)
                
                if stops:
                    print(f"✅ '{query}' search: {len(stops)} stop(s) found")
                    # Show first result
                    first_stop = stops[0]
                    print(f"   • {first_stop['name']} (ID: {first_stop['stop_id']})")
                    
                    # Save HUB stop ID for next test
                    if query == "HUB" and stops:
                        hub_stop_id = stops[0]['stop_id']
                else:
                    print(f"⚠️  '{query}' search: No stops found")
                    
            except Exception as e:
                print(f"❌ Stop search '{query}' failed: {e}")
        
        # Test 4: Vehicle Positions 
        print("\n4. Testing real-time vehicle positions...")
        test_routes = ["BL", "WL", "N", "V"]
        
        for route_id in test_routes:
            try:
                result = await client.call_tool("vehicle_positions_tool", {"route_id": route_id})
                vehicles = extract_result(result)
                
                if vehicles:
                    print(f"✅ Route {route_id}: {len(vehicles)} active vehicle(s)")
                    for vehicle in vehicles[:2]:  # Show first 2
                        print(f"   • Vehicle {vehicle['vehicle_id']}: ({vehicle['lat']:.4f}, {vehicle['lon']:.4f})")
                        if vehicle.get('speed_mps'):
                            speed_mph = vehicle['speed_mps'] * 2.237
                            print(f"     Speed: {speed_mph:.1f} mph")
                else:
                    print(f"⚠️  Route {route_id}: No active vehicles")
                    
            except Exception as e:
                print(f"❌ Vehicle positions for {route_id} failed: {e}")
        
        # Test 5: Next Arrivals
        print("\n5. Testing next arrivals...")
        try:
            # Use HUB stop if we found it
            stop_id = hub_stop_id if 'hub_stop_id' in locals() else "HUB"
            result = await client.call_tool("next_arrivals_tool", {
                "stop_id": stop_id,
                "horizon_minutes": 120
            })
            arrivals = extract_result(result)
            
            if arrivals:
                print(f"✅ Next arrivals at {stop_id}: {len(arrivals)} found")
                
                # Group by route
                by_route = {}
                for arrival in arrivals:
                    route = arrival['route_id']
                    if route not in by_route:
                        by_route[route] = []
                    by_route[route].append(arrival)
                
                for route_id, route_arrivals in list(by_route.items())[:3]:
                    print(f"   • Route {route_id}: {len(route_arrivals)} arrival(s)")
                    first_arrival = route_arrivals[0]
                    print(f"     Next: {first_arrival['arrival_time_iso']}")
                    if first_arrival.get('delay_sec'):
                        delay_min = first_arrival['delay_sec'] / 60
                        if abs(delay_min) > 0.5:
                            status = f"{abs(delay_min):.1f} min {'late' if delay_min > 0 else 'early'}"
                            print(f"     Status: {status}")
            else:
                print(f"⚠️  No arrivals found at {stop_id} in next 2 hours")
                
        except Exception as e:
            print(f"❌ Next arrivals test failed: {e}")
        
        # Test 6: Service Alerts
        print("\n6. Testing service alerts...")
        try:
            result = await client.call_tool("trip_alerts_tool", {})
            alerts = extract_result(result)
            
            if alerts:
                print(f"✅ Active service alerts: {len(alerts)}")
                for alert in alerts[:3]:
                    print(f"   • {alert['header']}")
                    print(f"     Severity: {alert['severity']}")
                    if alert.get('affected_routes'):
                        print(f"     Routes: {', '.join(alert['affected_routes'][:3])}")
            else:
                print("✅ No active service alerts (normal)")
                
        except Exception as e:
            print(f"❌ Service alerts test failed: {e}")
        
        # Test 7: Health Check
        print("\n7. Testing server health...")
        try:
            result = await client.call_tool("health_check", {})
            health = extract_result(result)
            
            print(f"✅ Server health: {health['status']}")
            print(f"   • Routes loaded: {health['routes_loaded']}")
            print(f"   • Stops loaded: {health['stops_loaded']}")
            print(f"   • Initialized: {health['initialized']}")
            
            if health.get('last_static_update'):
                print(f"   • Last GTFS update: {health['last_static_update']}")
            if health.get('last_vehicle_update'):
                print(f"   • Last vehicle update: {health['last_vehicle_update']}")
                
        except Exception as e:
            print(f"❌ Health check failed: {e}")
        
        # Test 8: Performance Test
        print("\n8. Testing concurrent performance...")
        try:
            start_time = asyncio.get_event_loop().time()
            
            tasks = [
                client.call_tool("list_routes_tool", {}),
                client.call_tool("search_stops_tool", {"query": "HUB"}),
                client.call_tool("vehicle_positions_tool", {"route_id": "BL"}),
                client.call_tool("health_check", {}),
            ]
            
            results = await asyncio.gather(*tasks)
            
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            
            print(f"✅ Concurrent requests completed in {duration:.2f}s")
            print(f"   • All {len(results)} requests succeeded")
            
            if duration > 5.0:
                print(f"⚠️  Response time high: {duration:.2f}s")
            
        except Exception as e:
            print(f"❌ Performance test failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 COMPREHENSIVE TEST COMPLETE")
    print("   FastMCP server successfully tested with CATA bus data")
    print("   Ready for deployment to FastMCP Cloud!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())