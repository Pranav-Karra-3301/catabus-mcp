#!/usr/bin/env python3
"""Test FastMCP HTTP endpoints."""

import asyncio
import subprocess
import sys
import time
import requests
import json

async def test_fastmcp_endpoints():
    """Test FastMCP HTTP endpoints for cloud deployment."""
    print("🌐 Testing FastMCP HTTP Endpoints")
    print("=" * 50)
    
    # Start server process
    cmd = [sys.executable, "-m", "uvicorn", "src.catabus_mcp.server:app", "--host", "0.0.0.0", "--port", "8081"]
    print(f"Starting server on port 8081...")
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for server to start
        time.sleep(4)
        
        # Test health check tool via HTTP
        print("\n1. Testing health_check tool...")
        try:
            response = requests.post(
                "http://localhost:8081/v1/mcp/call-tool",
                headers={"Content-Type": "application/json"},
                json={
                    "name": "health_check",
                    "arguments": {}
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Health check successful: {response.status_code}")
                print(f"   Response: {json.dumps(result, indent=2)[:200]}...")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Health check request failed: {e}")
        
        # Test tool listing
        print("\n2. Testing tool listing...")
        try:
            response = requests.post(
                "http://localhost:8081/v1/mcp/list-tools",
                headers={"Content-Type": "application/json"},
                json={},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                tools = result.get('tools', [])
                print(f"✅ Tool listing successful: {len(tools)} tools found")
                for tool in tools[:3]:
                    print(f"   • {tool.get('name', 'Unknown')}")
            else:
                print(f"❌ Tool listing failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Tool listing request failed: {e}")
            
    finally:
        # Clean up
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(test_fastmcp_endpoints())