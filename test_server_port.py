#!/usr/bin/env python3
"""Test server port binding and startup."""

import asyncio
import subprocess
import sys
import time
import requests
from pathlib import Path

async def test_server_port():
    """Test that server starts and binds to port 8080."""
    print("🧪 Testing FastMCP Cloud Port Binding")
    print("=" * 50)
    
    # Start server process
    cmd = [sys.executable, "-m", "uvicorn", "src.catabus_mcp.server:app", "--host", "0.0.0.0", "--port", "8080"]
    print(f"Starting server: {' '.join(cmd)}")
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for server to start
        print("Waiting for server startup...")
        time.sleep(3)
        
        # Test basic HTTP response
        try:
            response = requests.get("http://localhost:8080/", timeout=5)
            print(f"✅ Server responding on port 8080")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:100]}...")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Server not responding: {e}")
            
    finally:
        # Clean up
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            
        # Show any startup output
        stdout, stderr = proc.communicate()
        if stdout:
            print("\n📋 Server stdout:")
            print(stdout[-500:])  # Last 500 chars
        if stderr:
            print("\n📋 Server stderr:")
            print(stderr[-500:])  # Last 500 chars

if __name__ == "__main__":
    asyncio.run(test_server_port())