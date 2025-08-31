#!/usr/bin/env python3
"""Test fast server startup and lazy loading."""

import asyncio
import time
import json
from fastmcp import Client
from src.catabus_mcp.server import mcp


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


async def test_fast_startup():
    """Test server startup time and lazy loading."""
    print("🚀 Testing FastMCP Cloud-Ready Startup")
    print("=" * 50)
    
    start_time = time.time()
    client = Client(mcp)
    async with client:
        startup_time = time.time() - start_time
        print(f"✅ Server connection: {startup_time:.3f}s")
        
        # Test fast health check (should not trigger data loading)
        print("\n1. Testing fast health check...")
        health_start = time.time()
        result = await client.call_tool("health_check", {})
        health = extract_result(result)
        health_time = time.time() - health_start
        
        print(f"   ⚡ Health check time: {health_time:.3f}s")
        print(f"   Status: {health['status']}")
        print(f"   Initialized: {health['initialized']}")
        print(f"   Startup mode: {health['startup_mode']}")
        
        if health_time > 1.0:
            print("   ⚠️  Health check too slow!")
        else:
            print("   ✅ Fast health check working!")
        
        # Test manual initialization trigger
        print("\n2. Testing manual data initialization...")
        init_start = time.time()
        result = await client.call_tool("initialize_data", {})
        init_data = extract_result(result)
        init_time = time.time() - init_start
        
        print(f"   ⚡ Initialization time: {init_time:.3f}s")
        print(f"   Status: {init_data['status']}")
        print(f"   Routes loaded: {init_data['routes_loaded']}")
        print(f"   Stops loaded: {init_data['stops_loaded']}")
        
        # Test that tools work after initialization
        if init_data['routes_loaded'] > 0:
            print("\n3. Testing Blue Loop detection...")
            routes_result = await client.call_tool("list_routes_tool", {})
            routes = extract_result(routes_result)
            
            blue_loop = next((r for r in routes if r.get("short_name") == "BL"), None)
            if blue_loop:
                print(f"   ✅ Blue Loop found: {blue_loop['long_name']}")
            else:
                print("   ❌ Blue Loop not found")
        
        # Final health check to show updated status
        print("\n4. Final health check...")
        result = await client.call_tool("health_check", {})
        final_health = extract_result(result)
        
        print(f"   Initialized: {final_health['initialized']}")
        print(f"   Routes: {final_health['routes_loaded']}")
        print(f"   Stops: {final_health['stops_loaded']}")
    
    total_time = time.time() - start_time
    print(f"\n🎉 Total test time: {total_time:.3f}s")
    
    # Cloud deployment readiness check
    print("\n" + "="*50)
    print("☁️  CLOUD DEPLOYMENT READINESS:")
    if startup_time < 2.0:
        print("✅ Fast startup: READY")
    else:
        print("❌ Startup too slow: NOT READY")
    
    if health_time < 0.5:
        print("✅ Fast health check: READY") 
    else:
        print("❌ Health check too slow: NOT READY")
    
    if init_data['routes_loaded'] > 0:
        print("✅ Data loading works: READY")
    else:
        print("❌ Data loading failed: CHECK NETWORK")
        
    print("="*50)


if __name__ == "__main__":
    asyncio.run(test_fast_startup())