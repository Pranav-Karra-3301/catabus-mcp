#!/usr/bin/env python3
"""Simple test for CATA Bus MCP server."""

import json
import uuid
import requests

# Create a session ID
session_id = str(uuid.uuid4())
base_url = "http://localhost:8765/mcp"

# Headers for the request
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "x-session-id": session_id
}

print("🚌 Testing CATA Bus MCP Server\n")

# Initialize session
print("Initializing session...")
response = requests.post(
    base_url,
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        },
        "id": 1
    },
    stream=True
)

# Parse streaming response
for line in response.iter_lines():
    if line and line.startswith(b"data: "):
        data = json.loads(line[6:])
        print(f"Initialized: {data.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")
        break

print("\n1. Listing all bus routes:")
print("-" * 40)

# Call list_routes_tool
response = requests.post(
    base_url,
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "list_routes_tool",
            "arguments": {}
        },
        "id": 2
    },
    stream=True
)

# Parse response
for line in response.iter_lines():
    if line and line.startswith(b"data: "):
        try:
            data = json.loads(line[6:])
            if "result" in data:
                routes = data["result"].get("content", [])
                if isinstance(routes, list):
                    # Find Blue Loop and other interesting routes
                    blue_loop = None
                    for route in routes:
                        if route.get("short_name") == "BL":
                            blue_loop = route
                        # Print first 5 routes
                        if routes.index(route) < 5:
                            print(f"  • {route['short_name']}: {route['long_name']}")
                            if route.get('color'):
                                print(f"    Color: {route['color']}")
                    
                    if blue_loop:
                        print(f"\n  ✅ Found Blue Loop (BL): {blue_loop['long_name']}")
                    
                    print(f"\n  Total routes: {len(routes)}")
                break
        except Exception as e:
            print(f"  Error parsing: {e}")

print("\n2. Getting Blue Loop vehicle positions:")
print("-" * 40)

# Get Blue Loop vehicles
response = requests.post(
    base_url,
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "vehicle_positions_tool",
            "arguments": {"route_id": "BL"}
        },
        "id": 3
    },
    stream=True
)

for line in response.iter_lines():
    if line and line.startswith(b"data: "):
        try:
            data = json.loads(line[6:])
            if "result" in data:
                vehicles = data["result"].get("content", [])
                if vehicles:
                    for vehicle in vehicles:
                        print(f"  • Vehicle {vehicle['vehicle_id']}:")
                        print(f"    Location: ({vehicle['lat']:.6f}, {vehicle['lon']:.6f})")
                        if vehicle.get('speed_mps'):
                            speed_mph = vehicle['speed_mps'] * 2.237
                            print(f"    Speed: {speed_mph:.1f} mph")
                else:
                    print("  No Blue Loop vehicles currently active")
                break
        except Exception as e:
            print(f"  Error: {e}")

print("\n3. Searching for stops with 'Atherton':")
print("-" * 40)

# Search for stops
response = requests.post(
    base_url,
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_stops_tool",
            "arguments": {"query": "Atherton"}
        },
        "id": 4
    },
    stream=True
)

stop_id = None
for line in response.iter_lines():
    if line and line.startswith(b"data: "):
        try:
            data = json.loads(line[6:])
            if "result" in data:
                stops = data["result"].get("content", [])
                if stops:
                    for stop in stops[:3]:
                        print(f"  • {stop['name']} (ID: {stop['stop_id']})")
                        print(f"    Location: ({stop['lat']:.6f}, {stop['lon']:.6f})")
                        if not stop_id:
                            stop_id = stop['stop_id']
                    print(f"\n  Found {len(stops)} stops matching 'Atherton'")
                else:
                    print("  No stops found")
                break
        except Exception as e:
            print(f"  Error: {e}")

if stop_id:
    print(f"\n4. Next arrivals at {stop_id}:")
    print("-" * 40)
    
    # Get next arrivals
    response = requests.post(
        base_url,
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "next_arrivals_tool",
                "arguments": {"stop_id": stop_id, "horizon_minutes": 30}
            },
            "id": 5
        },
        stream=True
    )
    
    for line in response.iter_lines():
        if line and line.startswith(b"data: "):
            try:
                data = json.loads(line[6:])
                if "result" in data:
                    arrivals = data["result"].get("content", [])
                    if arrivals:
                        for arrival in arrivals[:5]:
                            print(f"  • Route {arrival['route_id']}")
                            print(f"    Arrival: {arrival['arrival_time_iso']}")
                            if arrival.get('delay_sec', 0) != 0:
                                delay_min = arrival['delay_sec'] / 60
                                status = f"{abs(delay_min):.1f} min {'late' if delay_min > 0 else 'early'}"
                                print(f"    Status: {status}")
                        if len(arrivals) > 5:
                            print(f"\n  ... and {len(arrivals) - 5} more arrivals")
                    else:
                        print("  No arrivals in the next 30 minutes")
                    break
            except Exception as e:
                print(f"  Error: {e}")

print("\n✅ Test complete!")