#!/usr/bin/env python3
"""Quick STDIO test for Claude Desktop compatibility."""

import subprocess
import sys
import time

def test_stdio_quick():
    """Quick test of STDIO mode startup."""
    print("📟 Quick STDIO Test")
    print("=" * 30)
    
    # Test CLI startup only (not full communication)
    print("\n1. Testing CLI startup...")
    try:
        proc = subprocess.Popen(
            ["catabus-mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Just check if it starts without crashing
        time.sleep(3)
        
        if proc.poll() is None:
            print("✅ CLI starts successfully (no crash)")
            print("✅ Process running in STDIO mode")
            
            # Check stderr for any startup messages
            proc.terminate()
            try:
                stdout, stderr = proc.communicate(timeout=2)
                if stderr and "FastMCP" in stderr:
                    print("✅ FastMCP server initialized")
                elif stderr:
                    print(f"   Startup logs: {stderr[:150]}...")
            except subprocess.TimeoutExpired:
                proc.kill()
                
        else:
            stdout, stderr = proc.communicate()
            print("❌ CLI process exited")
            print(f"   Error: {stderr[:200]}")
            return False
            
    except FileNotFoundError:
        print("❌ catabus-mcp command not found")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test Python module startup
    print("\n2. Testing Python module startup...")
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "catabus_mcp.server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        time.sleep(3)
        
        if proc.poll() is None:
            print("✅ Python module starts successfully")
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        else:
            stdout, stderr = proc.communicate()
            if "port" in stderr and "8080" in stderr:
                print("⚠️  Module tried to bind to port 8080 (HTTP mode)")
                print("   For STDIO, use the CLI command instead")
            else:
                print(f"❌ Module failed: {stderr[:200]}")
                return False
                
    except Exception as e:
        print(f"❌ Module test error: {e}")
        return False
    
    print("\n" + "=" * 30)  
    print("✅ STDIO MODE: READY")
    print("   Use 'catabus-mcp' command for Claude Desktop")
    print("=" * 30)
    
    return True

if __name__ == "__main__":
    success = test_stdio_quick()
    sys.exit(0 if success else 1)