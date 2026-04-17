"""
tests/test_api_endpoints.py — Unit Tests
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
import os
import pytest
import unittest.mock as mock
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, UTC

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

client = TestClient(app, raise_server_exceptions=True)

# ─── Mock Supabase Factory ────────────────────────────────────────────────────

def make_mock_sb(existing_worker=None, policy_row=None, update_result=None):
    mock_sb = MagicMock()

    workers_chain = MagicMock()
    mock_execute = MagicMock()
    mock_execute.data = [existing_worker] if existing_worker else []
    
    # Mock chain: table().select().eq().execute()
    workers_chain.select.return_value.eq.return_value.execute.return_value = mock_execute
    # Mock chain: table().insert().execute()
    workers_chain.insert.return_value.execute.return_value = MagicMock(data=[{"id": "MOCK-WORKER-ID"}])

    policies_chain = MagicMock()
    mock_policy_execute = MagicMock()
    mock_policy_execute.data = [policy_row] if policy_row else []
    policies_chain.select.return_value.eq.return_value.execute.return_value = mock_policy_execute
    policies_chain.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_policy_execute
    policies_chain.insert.return_value.execute.return_value = MagicMock(data=[{"id": "MOCK-POLICY-ID"}])
    policies_chain.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[update_result] if update_result else [])

    def table_router(table_name):
        if table_name == "workers": return workers_chain
        if table_name == "policies": return policies_chain
        return MagicMock()

    mock_sb.table.side_effect = table_router
    return mock_sb

# ─── Shared Fixtures ──────────────────────────────────────────────────────────

VALID_REGISTER_PAYLOAD = {
    "name": "Ravi Kumar",
    "phone_number": "+919876543210",
    "platform": "zomato",
    "shift": "day",
    "upi_id": "ravi@upi",
    "pin_codes": ["560047", "560034"],
    "plan": "basic",
    "language": "kn",
}

class TestRegisterWorker:

    def test_register_success_happy_path(self):
        """TC-REG-01: Valid payload → 200, returns worker_id and share_url"""
        mock_token_resp = {"share_token": "mock-token", "share_url": "http://test-url", "expires_at": "2030-01-01T00:00:00"}
        
        # Patch BOTH the worker service's DB client AND the token generator service
        with patch("api.workers.get_supabase", return_value=make_mock_sb()), \
             patch("api.workers.generate_share_token", new_callable=AsyncMock, return_value=mock_token_resp):
            
            response = client.post("/api/v1/workers/register", json=VALID_REGISTER_PAYLOAD)
        
        assert response.status_code == 200
        body = response.json()
        assert "worker_id" in body
        assert "share_url" in body

    def test_register_duplicate_phone_returns_400(self):
        """TC-REG-02: Duplicate phone number → 400 Bad Request"""
        # Mock finding an existing worker
        existing = {"id": "EXISTING-WORKER", "phone": "+919876543210"}
        with patch("api.workers.get_supabase", return_value=make_mock_sb(existing_worker=existing)):
            response = client.post("/api/v1/workers/register", json=VALID_REGISTER_PAYLOAD)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_upi_returns_422(self):
        """TC-REG-04: UPI ID without @ → 422"""
        bad_payload = {**VALID_REGISTER_PAYLOAD, "upi_id": "raviupi"}
        response = client.post("/api/v1/workers/register", json=bad_payload)
        assert response.status_code == 422

    def test_register_invalid_pin_code_returns_422(self):
        """TC-REG-05: 5-digit pin code → 422"""
        bad_payload = {**VALID_REGISTER_PAYLOAD, "pin_codes": ["56004"]}
        response = client.post("/api/v1/workers/register", json=bad_payload)
        assert response.status_code == 422

    def test_register_coverage_delay_is_24h(self):
        """TC-REG-07: coverage_active_from must be ~24 hours from now"""
        mock_token_resp = {"share_token": "mock-token", "share_url": "http://test-url", "expires_at": "2030-01-01T00:00:00"}
        with patch("api.workers.get_supabase", return_value=make_mock_sb()), \
             patch("api.workers.generate_share_token", new_callable=AsyncMock, return_value=mock_token_resp):
            response = client.post("/api/v1/workers/register", json=VALID_REGISTER_PAYLOAD)
            
        assert response.status_code == 200
        resp_json = response.json()
        coverage_from = datetime.fromisoformat(resp_json["coverage_active_from"]).replace(tzinfo=None)
        now = datetime.now(UTC).replace(tzinfo=None)
        delta = (coverage_from - now).total_seconds()
        # Should be approximately 24 hours (86400 seconds)
        assert 23 * 3600 < delta < 25 * 3600
