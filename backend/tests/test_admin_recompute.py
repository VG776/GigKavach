
import pytest
from fastapi.testclient import TestClient
from main import app
from api.auth import verify_token, verify_admin

client = TestClient(app)

# ─── Mock Data ───────────────────────────────────────────────────────────────

MOCK_ADMIN_USER = {
    "id": "admin-123",
    "email": "admin@gigkavach.com",
    "user_metadata": {"role": "admin"}
}

MOCK_REGULAR_USER = {
    "id": "user-456",
    "email": "worker@gmail.com",
    "user_metadata": {"role": "user"}
}

# ─── Mocks ───────────────────────────────────────────────────────────────────

# Mock audit logging to prevent Supabase connection errors during tests
import api.dci
api.dci.log_audit_event = lambda **kwargs: None

# Mock get_supabase to return a dummy object if needed
from unittest.mock import MagicMock
import utils.supabase_client
utils.supabase_client.get_supabase = MagicMock()

async def mock_verify_admin_token():
    return MOCK_ADMIN_USER

async def mock_verify_user_token():
    return MOCK_REGULAR_USER

# ─── Tests ───────────────────────────────────────────────────────────────────

def test_recompute_forbidden_for_regular_user():
    """Verify that role='user' gets 403 Forbidden."""
    app.dependency_overrides[verify_token] = mock_verify_user_token
    
    response = client.post(
        "/api/v1/dci/weights/recompute",
        json={"pincode": "560001", "force_recompute": True}
    )
    
    # verify_admin will throw 403 because role is not admin
    assert response.status_code == 403
    assert "Admin privileges required" in response.json()["detail"]
    
    # Cleanup
    app.dependency_overrides.clear()

def test_recompute_success_for_admin():
    """Verify that role='admin' can trigger recompute."""
    app.dependency_overrides[verify_token] = mock_verify_admin_token
    
    response = client.post(
        "/api/v1/dci/weights/recompute",
        json={"pincode": "400001", "force_recompute": True}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["pincode"] == "400001"
    assert data["city"] == "Mumbai"
    assert data["updated_weights"]["weather"] == 0.40
    assert data["status"] == "success"
    assert "timestamp" in data
    
    app.dependency_overrides.clear()

def test_recompute_invalid_pincode():
    """Verify that 6-digit regex validation still applies."""
    app.dependency_overrides[verify_token] = mock_verify_admin_token
    
    response = client.post(
        "/api/v1/dci/weights/recompute",
        json={"pincode": "123", "force_recompute": True}
    )
    
    assert response.status_code == 422
    app.dependency_overrides.clear()

def test_recompute_with_force_false():
    """Verify that force_recompute=False works as well."""
    app.dependency_overrides[verify_token] = mock_verify_admin_token
    
    response = client.post(
        "/api/v1/dci/weights/recompute",
        json={"pincode": "110001", "force_recompute": False}
    )
    
    assert response.status_code == 200
    assert response.json()["city"] == "Delhi"
    app.dependency_overrides.clear()
