"""
Regression tests for the city-aware DCI and payout pipeline.

Covers:
- Static DCI routes are not shadowed by the generic pincode route
- Feature ordering in the XGBoost input array matches saved metadata
- Model loader metadata schema matches the saved v3 artifact
- Pincode prefix fallback resolves valid-but-unlisted zones
- Payout model predictions stay within expected clamp bounds
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from config.city_dci_weights import resolve_city_from_pincode
from ml.xgboost_loader import (
    extract_features,
    get_feature_names,
    get_model_info,
    predict_multiplier,
)
from services.payout_service import calculate_payout


client = TestClient(app)


class _DummyQuery:
    def __init__(self, data):
        self.data = data

    def select(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        return self


class _DummySupabase:
    def table(self, name):
        if name == "dci_events":
            return _DummyQuery([
                {
                    "pin_code": "400001",
                    "city": "Mumbai",
                    "dci_score": 78,
                    "triggered_at": "2026-04-11T00:00:00Z",
                }
            ])
        return _DummyQuery([])


def test_latest_alerts_route_is_not_shadowed(monkeypatch):
    import api.dci as dci_module

    monkeypatch.setattr(dci_module, "get_supabase", lambda: _DummySupabase())

    response = client.get("/api/v1/dci/latest-alerts")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload[0]["pincode"] == "400001"
    assert payload[0]["area_name"] == "Mumbai"


def test_feature_order_matches_metadata():
    features = extract_features(
        dci_score=78,
        baseline_earnings=850,
        hour_of_day=19,
        day_of_week=4,
        city="Mumbai",
        zone_density="Mid",
        shift="Night",
        disruption_type="Rain",
    )

    assert list(features.keys()) == get_feature_names()


def test_model_info_matches_saved_v3_schema():
    info = get_model_info()

    assert info["name"] == "XGBoost Payout Model v3 (Enhanced)"
    assert info["test_r2"] > 0.80
    assert info["cv_r2"] > 0.75
    assert "subsample" in info["hyperparameters"]


def test_city_prefix_fallback_and_prediction_clamp():
    assert resolve_city_from_pincode("560999") == "Bengaluru"

    features = extract_features(
        dci_score=95,
        baseline_earnings=2500,
        hour_of_day=21,
        day_of_week=5,
        city="Bengaluru",
        zone_density="Low",
        shift="Night",
        disruption_type="Flood",
    )

    multiplier = predict_multiplier(features)
    assert 1.0 <= multiplier <= 5.0

    payout = calculate_payout(
        baseline_earnings=2500,
        disruption_duration=480,
        dci_score=95,
        worker_id="dummy-worker",
        city="Bangalore",
        zone_density="Low",
        shift="Night",
        disruption_type="Flood",
        hour_of_day=21,
        day_of_week=5,
        include_confidence=False,
    )

    assert payout["breakdown"]["city"] == "Bengaluru"
    assert payout["multiplier"] <= 5.0
    assert payout["payout"] >= 0
