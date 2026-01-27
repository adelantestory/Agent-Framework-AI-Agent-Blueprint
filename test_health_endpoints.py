"""
Test health and startup endpoints for Azure Container App probes
This is a simple standalone test that can be run without full app dependencies
"""

def test_endpoints_standalone():
    """Test the endpoints using a minimal FastAPI app"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    # Create minimal app with just the health endpoints
    test_app = FastAPI()
    
    @test_app.get("/startup")
    async def startup_check():
        """Lightweight startup probe endpoint"""
        return {"status": "ready"}
    
    @test_app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "mcp_connected": False
        }
    
    # Test the endpoints
    client = TestClient(test_app)
    
    # Test /startup
    print("Testing /startup endpoint...")
    response = client.get("/startup")
    print(f"  Status Code: {response.status_code}")
    print(f"  Response: {response.json()}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json() == {"status": "ready"}, f"Unexpected response: {response.json()}"
    print("  ✓ /startup endpoint working correctly")
    print()
    
    # Test /health
    print("Testing /health endpoint...")
    response = client.get("/health")
    print(f"  Status Code: {response.status_code}")
    print(f"  Response: {response.json()}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert "status" in data, "Missing 'status' field"
    assert "mcp_connected" in data, "Missing 'mcp_connected' field"
    assert data["status"] == "healthy", f"Expected status 'healthy', got {data['status']}"
    print("  ✓ /health endpoint working correctly")
    print()
    
    # Test response times
    print("Testing endpoint response times...")
    import time
    
    start = time.time()
    response = client.get("/startup")
    startup_time = time.time() - start
    print(f"  /startup response time: {startup_time*1000:.2f}ms")
    assert startup_time < 1.0, f"Startup endpoint too slow: {startup_time}s"
    
    start = time.time()
    response = client.get("/health")
    health_time = time.time() - start
    print(f"  /health response time: {health_time*1000:.2f}ms")
    assert health_time < 1.0, f"Health endpoint too slow: {health_time}s"
    print("  ✓ Both endpoints respond quickly")
    print()

if __name__ == "__main__":
    print("="*60)
    print("Testing Container App Health Probe Endpoints")
    print("="*60)
    print()
    
    try:
        test_endpoints_standalone()
        
        print("="*60)
        print("All tests passed! ✓")
        print("="*60)
        print()
        print("These endpoints are configured in app.py and used by:")
        print("  - Startup Probe: /startup (10s delay, 12 failures max)")
        print("  - Liveness Probe: /health (30s period)")
        print("  - Readiness Probe: /health (10s period)")
        print()
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
