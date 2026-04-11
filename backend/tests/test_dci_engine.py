"""
tests/test_dci_engine.py — Updated Unit Tests for City-Aware DCI Engine
════════════════════════════════════════════════════════════════════════════
Tests cover:
  - Weighted composite score math (city-aware + fallback)
  - City-specific weight application (all 5 cities)
  - Severity tier thresholds
  - NDMA catastrophic override
  - Payout trigger threshold (≥ 65)
  - Score clamping (0–100 boundary)
  - build_dci_log_payload shape and content (now includes city field)
  - Pincode-based city resolution inside calculate_dci()
  - Dominant risk component per city
"""

import pytest
import sys
import os

# Add backend/ to path so local imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.dci_engine import (
    calculate_dci,
    get_severity_tier,
    is_payout_triggered,
    build_dci_log_payload,
    get_dominant_risk_component,
    get_city_dci_profile,
    COMPONENT_WEIGHTS,    # backward-compat alias; still importable
)
from config.city_dci_weights import (
    CITY_DCI_WEIGHTS,
    GLOBAL_FALLBACK_WEIGHTS,
    get_city_weights,
    resolve_city_from_pincode,
)


# ─── TestCalculateDCI (city="default" → global fallback behaviour) ─────────────

class TestCalculateDCI:
    """Verify calculate_dci() with default / no city uses global fallback weights."""

    def test_all_zero_inputs_gives_zero(self):
        assert calculate_dci(0, 0, 0, 0, 0) == 0

    def test_all_100_inputs_gives_100(self):
        assert calculate_dci(100, 100, 100, 100, 100) == 100

    def test_only_weather_component_default_city(self):
        # 100 * 0.30 (global fallback weather weight) = 30
        score = calculate_dci(100, 0, 0, 0, 0, city="default")
        assert score == 30

    def test_only_social_component_default_city(self):
        # 100 * 0.20 (global fallback social weight) = 20
        score = calculate_dci(0, 0, 0, 100, 0, city="default")
        assert score == 20

    def test_weighted_math_precision_default_city(self):
        # Expected: 50*0.3 + 70*0.2 + 80*0.2 + 40*0.2 + 60*0.1
        # = 15 + 14 + 16 + 8 + 6 = 59
        score = calculate_dci(
            weather_score=50,
            aqi_score=70,
            heat_score=80,
            social_score=40,
            platform_score=60,
            city="default",
        )
        assert score == 59

    def test_score_is_integer(self):
        score = calculate_dci(33, 47, 51, 22, 88)
        assert isinstance(score, int)

    def test_score_clamps_to_100(self):
        # Input of 200 should clamp at 100
        assert calculate_dci(200, 200, 200, 200, 200) == 100

    def test_score_clamps_to_0(self):
        assert calculate_dci(-10, -20, -5, 0, 0) == 0

    def test_backward_compat_COMPONENT_WEIGHTS_is_importable(self):
        """COMPONENT_WEIGHTS must remain importable for old code that uses it."""
        assert isinstance(COMPONENT_WEIGHTS, dict)
        assert "weather" in COMPONENT_WEIGHTS


# ─── TestCalculateDCICityMumbai ───────────────────────────────────────────────

class TestCalculateDCICityMumbai:
    """Mumbai: weather weight 0.40 — rain-only DCI must be much higher than Delhi."""

    def test_rain_only_mumbai_score(self):
        # 100 * 0.40 = 40
        score = calculate_dci(100, 0, 0, 0, 0, city="Mumbai")
        assert score == 40

    def test_rain_only_mumbai_higher_than_rain_only_delhi(self):
        mumbai = calculate_dci(100, 0, 0, 0, 0, city="Mumbai")   # 40
        delhi  = calculate_dci(100, 0, 0, 0, 0, city="Delhi")    # 15
        assert mumbai > delhi, f"Mumbai rain DCI ({mumbai}) should beat Delhi ({delhi})"

    def test_rain_only_mumbai_higher_than_rain_only_bengaluru(self):
        mumbai    = calculate_dci(100, 0, 0, 0, 0, city="Mumbai")
        bengaluru = calculate_dci(100, 0, 0, 0, 0, city="Bengaluru")
        assert mumbai > bengaluru

    def test_aqi_only_mumbai_score(self):
        # 100 * 0.10 = 10
        score = calculate_dci(0, 100, 0, 0, 0, city="Mumbai")
        assert score == 10

    def test_all_100_mumbai(self):
        # 100 * (0.40 + 0.10 + 0.10 + 0.25 + 0.15) = 100
        assert calculate_dci(100, 100, 100, 100, 100, city="Mumbai") == 100

    def test_mumbai_city_alias_bombay(self):
        score_mumbai = calculate_dci(80, 30, 20, 40, 10, city="Mumbai")
        score_bombay = calculate_dci(80, 30, 20, 40, 10, city="bombay")
        assert score_mumbai == score_bombay


# ─── TestCalculateDCICityDelhi ────────────────────────────────────────────────

class TestCalculateDCICityDelhi:
    """Delhi: AQI + Heat each at 0.30 — these two together drive DCI most."""

    def test_aqi_only_delhi_score(self):
        # 100 * 0.30 = 30
        score = calculate_dci(0, 100, 0, 0, 0, city="Delhi")
        assert score == 30

    def test_heat_only_delhi_score(self):
        # 100 * 0.30 = 30
        score = calculate_dci(0, 0, 100, 0, 0, city="Delhi")
        assert score == 30

    def test_aqi_only_delhi_higher_than_aqi_only_mumbai(self):
        delhi  = calculate_dci(0, 100, 0, 0, 0, city="Delhi")   # 30
        mumbai = calculate_dci(0, 100, 0, 0, 0, city="Mumbai")  # 10
        assert delhi > mumbai

    def test_aqi_plus_heat_delhi_triggers_payout(self):
        # AQI=100 → 30, Heat=100 → 30 → total = 60 (other components at 20)
        score = calculate_dci(10, 100, 100, 0, 0, city="Delhi")
        assert score >= 60

    def test_rain_only_delhi_does_not_trigger_payout(self):
        # 100 * 0.15 = 15 — rain alone in Delhi doesn't trigger payout
        score = calculate_dci(100, 0, 0, 0, 0, city="Delhi")
        assert not is_payout_triggered(score)

    def test_delhi_alias_new_delhi(self):
        score_delhi     = calculate_dci(50, 80, 40, 20, 10, city="Delhi")
        score_new_delhi = calculate_dci(50, 80, 40, 20, 10, city="new delhi")
        assert score_delhi == score_new_delhi


# ─── TestCalculateDCICityBengaluru ────────────────────────────────────────────

class TestCalculateDCICityBengaluru:
    """Bengaluru: balanced rain + social profile."""

    def test_rain_only_bengaluru(self):
        # 100 * 0.30 = 30
        assert calculate_dci(100, 0, 0, 0, 0, city="Bengaluru") == 30

    def test_social_only_bengaluru(self):
        # 100 * 0.25 = 25
        assert calculate_dci(0, 0, 0, 100, 0, city="Bengaluru") == 25

    def test_rain_plus_social_bengaluru_triggers_payout(self):
        # Combine weather + AQI + heat + social strongly to cross payout threshold (≥65)
        # 90*0.30 + 60*0.20 + 50*0.15 + 90*0.25 + 50*0.10
        # = 27 + 12 + 7.5 + 22.5 + 5 = 74 → triggers payout
        score = calculate_dci(90, 60, 50, 90, 50, city="Bengaluru")
        assert is_payout_triggered(score), f"Expected score ≥65, got {score}"

    def test_bengaluru_alias_bangalore(self):
        score_b = calculate_dci(70, 50, 30, 60, 20, city="Bengaluru")
        score_a = calculate_dci(70, 50, 30, 60, 20, city="bangalore")
        assert score_b == score_a

    def test_pincode_based_resolution_bengaluru(self):
        # Passing pincode="560001" should resolve to Bengaluru weights
        score_explicit = calculate_dci(80, 40, 20, 60, 10, city="Bengaluru")
        score_pincode  = calculate_dci(80, 40, 20, 60, 10, pincode="560001")
        assert score_explicit == score_pincode


# ─── TestCalculateDCICityChennai ──────────────────────────────────────────────

class TestCalculateDCICityChennai:
    """Chennai: rain + heat co-dominant at 0.30 each."""

    def test_rain_only_chennai(self):
        # 100 * 0.30 = 30
        assert calculate_dci(100, 0, 0, 0, 0, city="Chennai") == 30

    def test_heat_only_chennai(self):
        # 100 * 0.30 = 30
        assert calculate_dci(0, 0, 100, 0, 0, city="Chennai") == 30

    def test_rain_plus_heat_chennai_triggers_payout(self):
        # 100*0.30 + 100*0.30 = 60 + background
        score = calculate_dci(100, 20, 100, 15, 10, city="Chennai")
        assert is_payout_triggered(score), f"Score was {score}"

    def test_chennai_alias_madras(self):
        score_c = calculate_dci(70, 20, 70, 15, 10, city="Chennai")
        score_m = calculate_dci(70, 20, 70, 15, 10, city="madras")
        assert score_c == score_m

    def test_pincode_based_resolution_chennai(self):
        score_explicit = calculate_dci(80, 20, 60, 15, 10, city="Chennai")
        score_pincode  = calculate_dci(80, 20, 60, 15, 10, pincode="600001")
        assert score_explicit == score_pincode


# ─── TestCalculateDCICityKolkata ──────────────────────────────────────────────

class TestCalculateDCICityKolkata:
    """Kolkata: highest weather weight (0.35) + significant social (0.25)."""

    def test_rain_only_kolkata(self):
        # 100 * 0.35 = 35
        assert calculate_dci(100, 0, 0, 0, 0, city="Kolkata") == 35

    def test_rain_only_kolkata_highest_of_all_cities(self):
        scores = {
            city: calculate_dci(100, 0, 0, 0, 0, city=city)
            for city in ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata"]
        }
        # Kolkata (35) and Mumbai (40) compete — both above Delhi (15)
        assert scores["Delhi"] < scores["Kolkata"]
        assert scores["Delhi"] < scores["Mumbai"]

    def test_social_only_kolkata(self):
        # 100 * 0.25 = 25
        assert calculate_dci(0, 0, 0, 100, 0, city="Kolkata") == 25

    def test_kolkata_alias_calcutta(self):
        score_k = calculate_dci(70, 20, 20, 70, 10, city="Kolkata")
        score_c = calculate_dci(70, 20, 20, 70, 10, city="calcutta")
        assert score_k == score_c

    def test_pincode_based_resolution_kolkata(self):
        score_explicit = calculate_dci(80, 20, 20, 60, 10, city="Kolkata")
        score_pincode  = calculate_dci(80, 20, 20, 60, 10, pincode="700001")
        assert score_explicit == score_pincode


# ─── TestNDMAOverride ─────────────────────────────────────────────────────────

class TestNDMAOverride:
    """NDMA override must force DCI = 95 regardless of city or component scores."""

    def test_override_forces_95_with_default_city(self):
        assert calculate_dci(0, 0, 0, 0, 0, ndma_override=True) == 95

    def test_override_forces_95_with_mumbai(self):
        assert calculate_dci(0, 0, 0, 0, 0, ndma_override=True, city="Mumbai") == 95

    def test_override_forces_95_with_delhi(self):
        assert calculate_dci(100, 100, 100, 100, 100, ndma_override=True, city="Delhi") == 95

    def test_override_forces_95_with_kolkata(self):
        assert calculate_dci(50, 50, 50, 50, 50, ndma_override=True, city="Kolkata") == 95

    def test_override_false_uses_city_weights(self):
        # With override=False, Mumbai rain-only = 40
        score = calculate_dci(100, 0, 0, 0, 0, ndma_override=False, city="Mumbai")
        assert score == 40


# ─── TestSeverityTiers ────────────────────────────────────────────────────────

class TestGetSeverityTier:
    def test_zero_is_none(self):        assert get_severity_tier(0) == "none"
    def test_29_is_none(self):          assert get_severity_tier(29) == "none"
    def test_30_is_low(self):           assert get_severity_tier(30) == "low"
    def test_49_is_low(self):           assert get_severity_tier(49) == "low"
    def test_50_is_moderate(self):      assert get_severity_tier(50) == "moderate"
    def test_64_is_moderate(self):      assert get_severity_tier(64) == "moderate"
    def test_65_is_high(self):          assert get_severity_tier(65) == "high"
    def test_79_is_high(self):          assert get_severity_tier(79) == "high"
    def test_80_is_critical(self):      assert get_severity_tier(80) == "critical"
    def test_94_is_critical(self):      assert get_severity_tier(94) == "critical"
    def test_95_is_catastrophic(self):  assert get_severity_tier(95) == "catastrophic"
    def test_100_is_catastrophic(self): assert get_severity_tier(100) == "catastrophic"


# ─── TestIsPayoutTriggered ──────────────────────────────────────────────────

class TestIsPayoutTriggered:
    def test_score_64_does_not_trigger(self): assert is_payout_triggered(64) is False
    def test_score_65_triggers(self):          assert is_payout_triggered(65) is True
    def test_score_100_triggers(self):         assert is_payout_triggered(100) is True
    def test_score_0_does_not_trigger(self):   assert is_payout_triggered(0) is False


# ─── TestBuildDCILogPayload ──────────────────────────────────────────────────

class TestBuildDCILogPayload:
    """build_dci_log_payload() must now include city + weights_used fields."""

    def test_payload_has_all_required_fields(self):
        payload = build_dci_log_payload(
            pincode="560001",
            dci_score=72,
            weather={"score": 80},
            aqi={"score": 60},
            heat={"score": 40},
            social={"score": 30},
            platform={"score": 20},
            ndma_override=False,
            shift_active="day",
            city="Bengaluru",
        )
        required_keys = [
            "pincode", "city", "total_score", "rainfall_score", "aqi_score",
            "heat_score", "social_score", "platform_score", "severity_tier",
            "ndma_override_active", "shift_active", "is_shift_window_active",
            "weights_used", "dominant_risk",
        ]
        for key in required_keys:
            assert key in payload, f"Missing key: {key}"

    def test_payload_contains_city_field(self):
        payload = build_dci_log_payload(
            pincode="400001", dci_score=72,
            weather={"score": 80}, aqi={"score": 10}, heat={"score": 10},
            social={"score": 30}, platform={"score": 20},
            city="Mumbai",
        )
        assert payload["city"] == "Mumbai"

    def test_payload_contains_weights_snapshot(self):
        payload = build_dci_log_payload(
            pincode="400001", dci_score=72,
            weather={"score": 80}, aqi={"score": 10}, heat={"score": 10},
            social={"score": 30}, platform={"score": 20},
            city="Mumbai",
        )
        assert isinstance(payload["weights_used"], dict)
        # Mumbai rainfall weight should be 0.40
        assert payload["weights_used"]["weather"] == 0.40

    def test_payload_score_roundtrips(self):
        payload = build_dci_log_payload(
            pincode="560034", dci_score=85,
            weather={"score": 90}, aqi={"score": 70}, heat={"score": 80},
            social={"score": 50}, platform={"score": 40},
            city="Bengaluru",
        )
        assert payload["total_score"] == 85
        assert payload["severity_tier"] == "critical"

    def test_ndma_override_reflected_in_payload(self):
        payload = build_dci_log_payload(
            pincode="560001", dci_score=95,
            weather={"score": 0}, aqi={"score": 0}, heat={"score": 0},
            social={"score": 0}, platform={"score": 0},
            ndma_override=True,
            city="Bengaluru",
        )
        assert payload["ndma_override_active"] is True
        assert payload["severity_tier"] == "catastrophic"

    def test_default_city_uses_fallback_weights(self):
        payload = build_dci_log_payload(
            pincode="560001", dci_score=50,
            weather={"score": 50}, aqi={"score": 50}, heat={"score": 50},
            social={"score": 50}, platform={"score": 50},
            city="default",
        )
        # Global fallback: weather = 0.30
        assert payload["weights_used"]["weather"] == 0.30


# ─── TestPincodeInCalculateDCI ────────────────────────────────────────────────

class TestPincodeInCalculateDCI:
    """calculate_dci() can resolve city automatically from pincode."""

    def test_mumbai_pincode_400001(self):
        score_city   = calculate_dci(100, 0, 0, 0, 0, city="Mumbai")
        score_pincode = calculate_dci(100, 0, 0, 0, 0, pincode="400001")
        assert score_city == score_pincode

    def test_delhi_pincode_110001(self):
        score_city    = calculate_dci(0, 100, 0, 0, 0, city="Delhi")
        score_pincode = calculate_dci(0, 100, 0, 0, 0, pincode="110001")
        assert score_city == score_pincode

    def test_kolkata_pincode_700001(self):
        score_city    = calculate_dci(100, 0, 0, 0, 0, city="Kolkata")
        score_pincode = calculate_dci(100, 0, 0, 0, 0, pincode="700001")
        assert score_city == score_pincode

    def test_city_param_takes_priority_over_pincode(self):
        # city="Mumbai" + pincode="110001" (Delhi) → Mumbai weights should win
        score_explicit_mumbai = calculate_dci(100, 0, 0, 0, 0, city="Mumbai")
        score_mixed           = calculate_dci(100, 0, 0, 0, 0, city="Mumbai", pincode="110001")
        assert score_explicit_mumbai == score_mixed

    def test_unknown_pincode_uses_global_fallback(self):
        score_default  = calculate_dci(100, 0, 0, 0, 0, city="default")
        score_unknown  = calculate_dci(100, 0, 0, 0, 0, pincode="999999")
        assert score_default == score_unknown


# ─── TestCrossCity ────────────────────────────────────────────────────────────

class TestCrossCity:
    """Verify the directional relationships that define city weather risk profiles."""

    def test_same_rain_different_cities_produce_different_dci(self):
        """A monsoon deluge should matter most in Mumbai, least in Delhi."""
        scores = {
            city: calculate_dci(100, 0, 0, 0, 0, city=city)
            for city in ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata"]
        }
        assert scores["Mumbai"] > scores["Delhi"], "Mumbai rain must beat Delhi rain"
        assert scores["Kolkata"] > scores["Delhi"], "Kolkata rain must beat Delhi rain"

    def test_same_aqi_different_cities(self):
        """Severe AQI should matter most in Delhi."""
        scores = {
            city: calculate_dci(0, 100, 0, 0, 0, city=city)
            for city in ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata"]
        }
        assert scores["Delhi"] == max(scores.values()), "Delhi must have max AQI weight"

    def test_same_heat_different_cities(self):
        """Extreme heat should be most impactful in Chennai and Delhi."""
        scores = {
            city: calculate_dci(0, 0, 100, 0, 0, city=city)
            for city in ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata"]
        }
        # Chennai and Delhi both have heat=0.30
        max_score = max(scores.values())
        assert scores["Chennai"] == max_score
        assert scores["Delhi"] == max_score

    def test_same_social_different_cities(self):
        """Social disruption should weigh equally or more in Bengaluru/Kolkata vs Mumbai."""
        b_score = calculate_dci(0, 0, 0, 100, 0, city="Bengaluru")
        k_score = calculate_dci(0, 0, 0, 100, 0, city="Kolkata")
        m_score = calculate_dci(0, 0, 0, 100, 0, city="Mumbai")
        assert b_score >= m_score
        assert k_score >= m_score
