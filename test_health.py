"""
Tests for health check endpoints and startup behavior.
These tests validate that the /healthz endpoint properly reflects
application startup state to prevent startup probe failures.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


# Mock the external dependencies before importing app
@pytest.fixture(autouse=True)
def mock_external_deps():
    """Mock external dependencies that require environment setup"""
    with patch('app.get_rentcast_mcp_tool', new_callable=AsyncMock) as mock_rentcast, \
         patch('app.get_analytics_backend') as mock_analytics:
        # Configure mocks
        mock_rentcast.return_value = AsyncMock()
        mock_analytics.return_value = None  # Analytics backend not required for health checks
        yield


@pytest.fixture
def client():
    """Create a test client for the FastAPI app with lifespan context"""
    # Import app after mocks are set up
    from app import app
    # Use context manager to ensure lifespan events run
    with TestClient(app) as client:
        yield client


def test_healthz_endpoint_after_startup(client):
    """Test that /healthz returns 200 after successful startup"""
    response = client.get("/healthz")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["startup_complete"] is True
    assert "mcp_connected" in data


def test_healthz_endpoint_returns_json(client):
    """Test that /healthz returns proper JSON structure"""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    data = response.json()
    assert "status" in data
    assert "startup_complete" in data
    assert "mcp_connected" in data


def test_health_endpoint_backward_compatibility(client):
    """Test that legacy /health endpoint still works"""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "startup_complete" in data
    assert "mcp_connected" in data


def test_health_endpoint_during_startup():
    """Test that /health endpoint returns appropriate status before lifespan runs"""
    # Import app module to check initial state
    import app as app_module
    from app import app
    
    # Before lifespan runs (no TestClient context), startup should not be complete
    # This simulates the state between app creation and startup event
    original_state = app_module.startup_complete
    try:
        app_module.startup_complete = False
        
        # Create client without context manager to avoid running lifespan
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/health")
        
        # /health should still return 200 but with "starting" status
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "starting"
        assert data["startup_complete"] is False
    finally:
        # Restore original state
        app_module.startup_complete = original_state


def test_healthz_endpoint_during_startup():
    """Test that /healthz returns 503 when startup is not complete"""
    # Import app module to manipulate startup state
    import app as app_module
    from app import app
    
    # Temporarily set startup_complete to False to simulate startup
    original_state = app_module.startup_complete
    try:
        app_module.startup_complete = False
        
        # Create client without context manager to avoid running lifespan
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/healthz")
        
        # /healthz should return 503 during startup
        assert response.status_code == 503
        assert "Application is starting up" in response.json()["detail"]
    finally:
        # Restore original state
        app_module.startup_complete = original_state


def test_root_endpoint_returns_html(client):
    """Test that root endpoint returns HTML chat interface"""
    response = client.get("/")
    # Should return HTML (200 if template exists, 404 if not)
    assert response.status_code in [200, 404]
    # Response should be HTML
    assert "text/html" in response.headers.get("content-type", "")


def test_adelante_endpoint_returns_html(client):
    """Test that /adelante endpoint returns HTML"""
    response = client.get("/adelante")
    # Should return HTML (200 if template exists, 404 if not)
    assert response.status_code in [200, 404]
    # Response should be HTML
    assert "text/html" in response.headers.get("content-type", "")


def test_dashboard_endpoint_returns_html(client):
    """Test that /dashboard endpoint returns HTML"""
    response = client.get("/dashboard")
    # Should return HTML (200 if template exists, 404 if not)
    assert response.status_code in [200, 404]
    # Response should be HTML
    assert "text/html" in response.headers.get("content-type", "")


def test_api_sessions_endpoint(client):
    """Test that /api/sessions endpoint returns session info"""
    response = client.get("/api/sessions")
    assert response.status_code == 200
    
    data = response.json()
    assert "active_sessions" in data
    assert "sessions" in data
    assert isinstance(data["active_sessions"], int)
    assert isinstance(data["sessions"], list)
