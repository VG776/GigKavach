
import pytest
from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)

def test_weights_invalid_pincode():
    """Verify that non-6-digit pincodes are rejected with 422."""
    response = client.get("/api/v1/dci/weights/123")
    assert response.status_code == 422
    
    response = client.get("/api/v1/dci/weights/abc123")
    assert response.status_code == 422
    
    response = client.get("/api/v1/dci/weights/1234567")
    assert response.status_code == 422

def test_weights_valid_pincode_mumbai():
    """Verify Mumbai pincode returns correct weights and structure."""
    response = client.get("/api/v1/dci/weights/400001")
    assert response.status_code == 200
    data = response.json()
    
    assert data["pincode"] == "400001"
    assert data["city"] == "Mumbai"
    assert data["weights"]["weather"] == 0.40
    assert "cached_status" in data
    assert "last_updated" in data
    assert data["model_r2_score"] == 0.85
    assert data["limit_remaining"] < 100

def test_weights_valid_pincode_delhi():
    """Verify Delhi pincode returns correct weights."""
    response = client.get("/api/v1/dci/weights/110001")
    assert response.status_code == 200
    data = response.json()
    
    assert data["city"] == "Delhi"
    assert data["weights"]["aqi"] == 0.30
    assert data["weights"]["heat"] == 0.30

def test_weights_valid_pincode_fallback():
    """Verify unknown pincode returns global fallback."""
    response = client.get("/api/v1/dci/weights/999999")
    assert response.status_code == 200
    data = response.json()
    
    assert data["city"] == "default"
    assert data["weights"]["weather"] == 0.30  # global fallback

def test_weights_rate_limit():
    """
    Simulate rate limiting. 
    Note: In a test environment with MockRedis, this depends on MockRedis implementation.
    Our MockRedis doesn't support pipelines/incr perfectly in same way as real Redis,
    but let's see if the logic holds up.
    """
    # Just verify that repeated calls decrement limit_remaining
    responses = [client.get("/api/v1/dci/weights/560001") for _ in range(5)]
    limits = [r.json()["limit_remaining"] for r in responses]
    
    # Each call should decrement the limit
    for i in range(len(limits) - 1):
        assert limits[i] > limits[i+1]
