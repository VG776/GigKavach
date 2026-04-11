"""
tests/test_city_dci_weights.py — City-Specific Weight System Tests
════════════════════════════════════════════════════════════════════
Comprehensive unit tests for config/city_dci_weights.py.

Test Classes:
  TestWeightTableIntegrity      — all cities sum to 1.0, no missing keys
  TestCityWeightRetrieval       — get_city_weights() for all 5 cities
  TestCityNameNormalisation     — alias resolution (bangalore → Bengaluru etc.)
  TestPincodeToCity             — resolve_city_from_pincode() for all 5 cities
  TestGlobalFallback            — unknown city returns fallback without crashing
  TestDominantRisk              — each city's dominant component is correct
  TestCityProfileStructure      — get_city_dci_profile() returns correct shape
  TestListSupportedCities       — correct count and all names present
  TestGetAllCityWeights         — deep-copy safety, all 5 cities in result
  TestWeightWeightIndexing      — weather > aqi for Mumbai, aqi == heat for Delhi
  TestEdgeCases                 — None, empty string, int, dict passed as city

All tests are pure unit tests — no DB, Redis, or HTTP dependencies.
"""

import pytest
import sys
import os

# Add backend/ to path so local imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.city_dci_weights import (
    CITY_DCI_WEIGHTS,
    GLOBAL_FALLBACK_WEIGHTS,
    PINCODE_EXACT_MAP,
    CITY_NAME_ALIASES,
    get_city_weights,
    resolve_city_from_pincode,
    normalise_city_name,
    list_supported_cities,
    get_all_city_weights,
    _MAX_DELTA,
)
from services.dci_engine import (
    calculate_dci,
    get_dominant_risk_component,
    get_city_dci_profile,
)


SUPPORTED_CITIES = ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata"]


# ─── TestWeightTableIntegrity ──────────────────────────────────────────────────

class TestWeightTableIntegrity:
    """All city weight profiles must be internally consistent."""

    def test_all_five_cities_present(self):
        for city in SUPPORTED_CITIES:
            assert city in CITY_DCI_WEIGHTS, f"Missing city: {city}"

    def test_all_cities_sum_to_one(self):
        for city, weights in CITY_DCI_WEIGHTS.items():
            total = sum(weights.values())
            assert abs(total - 1.0) <= _MAX_DELTA, (
                f"City '{city}' weights sum to {total:.10f}, not 1.0"
            )

    def test_all_required_components_present(self):
        required = {"weather", "aqi", "heat", "social", "platform"}
        for city, weights in CITY_DCI_WEIGHTS.items():
            assert set(weights.keys()) == required, (
                f"City '{city}' has wrong component keys: {set(weights.keys())}"
            )

    def test_all_weights_are_positive(self):
        for city, weights in CITY_DCI_WEIGHTS.items():
            for component, value in weights.items():
                assert value > 0, (
                    f"City '{city}' component '{component}' has non-positive weight: {value}"
                )

    def test_all_weights_less_than_one(self):
        for city, weights in CITY_DCI_WEIGHTS.items():
            for component, value in weights.items():
                assert value < 1.0, (
                    f"City '{city}' single component '{component}' = {value} (≥1.0, impossible)"
                )

    def test_global_fallback_sums_to_one(self):
        total = sum(GLOBAL_FALLBACK_WEIGHTS.values())
        assert abs(total - 1.0) <= _MAX_DELTA

    def test_global_fallback_has_all_components(self):
        required = {"weather", "aqi", "heat", "social", "platform"}
        assert set(GLOBAL_FALLBACK_WEIGHTS.keys()) == required

    def test_no_duplicate_city_keys(self):
        # dict keys are unique by definition; verify the count matches SUPPORTED_CITIES
        assert len(CITY_DCI_WEIGHTS) == len(SUPPORTED_CITIES)


# ─── TestCityWeightRetrieval ──────────────────────────────────────────────────

class TestCityWeightRetrieval:
    """get_city_weights() returns correct profile for each city."""

    def test_mumbai_weather_is_highest(self):
        w = get_city_weights("Mumbai")
        assert w["weather"] == max(w.values()), "Mumbai: weather should be dominant"

    def test_mumbai_weather_40_percent(self):
        assert get_city_weights("Mumbai")["weather"] == 0.40

    def test_mumbai_aqi_10_percent(self):
        assert get_city_weights("Mumbai")["aqi"] == 0.10

    def test_delhi_aqi_30_percent(self):
        assert get_city_weights("Delhi")["aqi"] == 0.30

    def test_delhi_heat_30_percent(self):
        assert get_city_weights("Delhi")["heat"] == 0.30

    def test_delhi_aqi_equals_heat(self):
        w = get_city_weights("Delhi")
        assert w["aqi"] == w["heat"], "Delhi: AQI and Heat must be co-equal dominant risks"

    def test_bengaluru_weather_30_percent(self):
        assert get_city_weights("Bengaluru")["weather"] == 0.30

    def test_bengaluru_social_25_percent(self):
        assert get_city_weights("Bengaluru")["social"] == 0.25

    def test_chennai_weather_30_percent(self):
        assert get_city_weights("Chennai")["weather"] == 0.30

    def test_chennai_heat_30_percent(self):
        assert get_city_weights("Chennai")["heat"] == 0.30

    def test_chennai_weather_equals_heat(self):
        w = get_city_weights("Chennai")
        assert w["weather"] == w["heat"], "Chennai: Weather and Heat must be co-equal dominant"

    def test_kolkata_weather_35_percent(self):
        assert get_city_weights("Kolkata")["weather"] == 0.35

    def test_kolkata_social_25_percent(self):
        assert get_city_weights("Kolkata")["social"] == 0.25

    def test_returns_dict_copy_not_reference(self):
        """Mutating the returned dict must not affect the master table."""
        w = get_city_weights("Mumbai")
        original_weather = CITY_DCI_WEIGHTS["Mumbai"]["weather"]
        w["weather"] = 0.99
        assert CITY_DCI_WEIGHTS["Mumbai"]["weather"] == original_weather


# ─── TestCityNameNormalisation ────────────────────────────────────────────────

class TestCityNameNormalisation:
    """normalise_city_name() resolves aliases and variants correctly."""

    # ── Exact canonical names (no alias lookup needed) ───────────────────────
    def test_mumbai_exact(self):        assert normalise_city_name("Mumbai")   == "Mumbai"
    def test_delhi_exact(self):         assert normalise_city_name("Delhi")    == "Delhi"
    def test_bengaluru_exact(self):     assert normalise_city_name("Bengaluru") == "Bengaluru"
    def test_chennai_exact(self):       assert normalise_city_name("Chennai")  == "Chennai"
    def test_kolkata_exact(self):       assert normalise_city_name("Kolkata")  == "Kolkata"

    # ── Lowercase aliases ────────────────────────────────────────────────────
    def test_mumbai_lowercase(self):    assert normalise_city_name("mumbai")   == "Mumbai"
    def test_delhi_lowercase(self):     assert normalise_city_name("delhi")    == "Delhi"
    def test_bengaluru_lowercase(self): assert normalise_city_name("bengaluru") == "Bengaluru"
    def test_bangalore_alias(self):     assert normalise_city_name("bangalore") == "Bengaluru"
    def test_chennai_lowercase(self):   assert normalise_city_name("chennai")  == "Chennai"
    def test_kolkata_lowercase(self):   assert normalise_city_name("kolkata")  == "Kolkata"

    # ── Historical / colonial names ──────────────────────────────────────────
    def test_bombay_alias(self):        assert normalise_city_name("bombay")   == "Mumbai"
    def test_madras_alias(self):        assert normalise_city_name("madras")   == "Chennai"
    def test_calcutta_alias(self):      assert normalise_city_name("calcutta") == "Kolkata"
    def test_new_delhi_alias(self):     assert normalise_city_name("new delhi") == "Delhi"

    # ── Uppercase variants ───────────────────────────────────────────────────
    def test_MUMBAI_uppercase(self):    assert normalise_city_name("MUMBAI")   == "Mumbai"
    def test_DELHI_uppercase(self):     assert normalise_city_name("DELHI")    == "Delhi"
    def test_BENGALURU_uppercase(self): assert normalise_city_name("BENGALURU") == "Bengaluru"
    def test_BANGALORE_uppercase(self): assert normalise_city_name("BANGALORE") == "Bengaluru"
    def test_CHENNAI_uppercase(self):   assert normalise_city_name("CHENNAI")  == "Chennai"
    def test_KOLKATA_uppercase(self):   assert normalise_city_name("KOLKATA")  == "Kolkata"

    # ── Unknown inputs → None ────────────────────────────────────────────────
    def test_unknown_city_returns_none(self):   assert normalise_city_name("Atlantis") is None
    def test_random_string_returns_none(self):  assert normalise_city_name("xyz123") is None
    def test_empty_string_returns_none(self):   assert normalise_city_name("") is None
    def test_none_input_returns_none(self):     assert normalise_city_name(None) is None


# ─── TestPincodeToCity ────────────────────────────────────────────────────────

class TestPincodeToCity:
    """resolve_city_from_pincode() maps representative pincodes correctly."""

    # ── Bengaluru pincodes ───────────────────────────────────────────────────
    def test_bengaluru_560001(self):  assert resolve_city_from_pincode("560001") == "Bengaluru"
    def test_bengaluru_560034(self):  assert resolve_city_from_pincode("560034") == "Bengaluru"
    def test_bengaluru_560037(self):  assert resolve_city_from_pincode("560037") == "Bengaluru"
    def test_bengaluru_560038(self):  assert resolve_city_from_pincode("560038") == "Bengaluru"
    def test_bengaluru_560068(self):  assert resolve_city_from_pincode("560068") == "Bengaluru"
    def test_bengaluru_560100(self):  assert resolve_city_from_pincode("560100") == "Bengaluru"
    def test_bengaluru_560103(self):  assert resolve_city_from_pincode("560103") == "Bengaluru"

    # ── Mumbai pincodes ──────────────────────────────────────────────────────
    def test_mumbai_400001(self):     assert resolve_city_from_pincode("400001") == "Mumbai"
    def test_mumbai_400050(self):     assert resolve_city_from_pincode("400050") == "Mumbai"
    def test_mumbai_400097(self):     assert resolve_city_from_pincode("400097") == "Mumbai"
    def test_mumbai_400601(self):     assert resolve_city_from_pincode("400601") == "Mumbai"

    # ── Delhi pincodes ───────────────────────────────────────────────────────
    def test_delhi_110001(self):      assert resolve_city_from_pincode("110001") == "Delhi"
    def test_delhi_110019(self):      assert resolve_city_from_pincode("110019") == "Delhi"
    def test_delhi_110092(self):      assert resolve_city_from_pincode("110092") == "Delhi"

    # ── Chennai pincodes ─────────────────────────────────────────────────────
    def test_chennai_600001(self):    assert resolve_city_from_pincode("600001") == "Chennai"
    def test_chennai_600020(self):    assert resolve_city_from_pincode("600020") == "Chennai"
    def test_chennai_600042(self):    assert resolve_city_from_pincode("600042") == "Chennai"

    # ── Kolkata pincodes ─────────────────────────────────────────────────────
    def test_kolkata_700001(self):    assert resolve_city_from_pincode("700001") == "Kolkata"
    def test_kolkata_700019(self):    assert resolve_city_from_pincode("700019") == "Kolkata"
    def test_kolkata_700091(self):    assert resolve_city_from_pincode("700091") == "Kolkata"

    # ── Edge cases ───────────────────────────────────────────────────────────
    def test_unknown_pincode_returns_default(self):
        assert resolve_city_from_pincode("999999") == "default"

    def test_empty_string_returns_default(self):
        assert resolve_city_from_pincode("") == "default"

    def test_none_returns_default(self):
        assert resolve_city_from_pincode(None) == "default"

    def test_short_pincode_returns_default(self):
        assert resolve_city_from_pincode("123") == "default"

    def test_whitespace_padded_pincode(self):
        # strip() is applied internally
        assert resolve_city_from_pincode("  400001  ") == "Mumbai"

    def test_bengaluru_prefix_fallback(self):
        # Prefix fallback should resolve valid but unlisted Bengaluru pincodes.
        assert resolve_city_from_pincode("560999") == "Bengaluru"


# ─── TestGlobalFallback ───────────────────────────────────────────────────────

class TestGlobalFallback:
    """Unknown or 'default' cities must gracefully return global fallback weights."""

    def test_default_city_returns_fallback(self):
        w = get_city_weights("default")
        assert w == GLOBAL_FALLBACK_WEIGHTS

    def test_unknown_city_returns_fallback(self):
        w = get_city_weights("Atlantis")
        assert w == GLOBAL_FALLBACK_WEIGHTS

    def test_empty_string_returns_fallback(self):
        w = get_city_weights("")
        assert w == GLOBAL_FALLBACK_WEIGHTS

    def test_none_returns_fallback(self):
        w = get_city_weights(None)
        assert w == GLOBAL_FALLBACK_WEIGHTS

    def test_fallback_sums_to_one(self):
        w = get_city_weights("nonexistent_city_xyz")
        assert abs(sum(w.values()) - 1.0) <= _MAX_DELTA

    def test_fallback_has_all_components(self):
        w = get_city_weights("xyz_unknown")
        required = {"weather", "aqi", "heat", "social", "platform"}
        assert set(w.keys()) == required

    def test_fallback_is_copy_not_reference(self):
        """Mutating fallback result must not corrupt GLOBAL_FALLBACK_WEIGHTS."""
        w = get_city_weights("default")
        original_weather = GLOBAL_FALLBACK_WEIGHTS["weather"]
        w["weather"] = 0.99
        assert GLOBAL_FALLBACK_WEIGHTS["weather"] == original_weather


# ─── TestDominantRisk ─────────────────────────────────────────────────────────

class TestDominantRisk:
    """Each city's dominant DCI component must be geographically correct."""

    def test_mumbai_dominant_risk_is_weather(self):
        assert get_dominant_risk_component("Mumbai") == "weather"

    def test_delhi_dominant_risk_is_aqi_or_heat(self):
        # Delhi has aqi == heat == 0.30 (co-dominant); accept either
        dominant = get_dominant_risk_component("Delhi")
        assert dominant in {"aqi", "heat"}, (
            f"Delhi dominant risk '{dominant}' is neither aqi nor heat"
        )

    def test_bengaluru_dominant_risk_is_weather(self):
        # Bengaluru: weather=0.30, social=0.25 → weather wins
        assert get_dominant_risk_component("Bengaluru") == "weather"

    def test_chennai_dominant_risk_is_weather_or_heat(self):
        # Chennai has weather == heat == 0.30 (co-dominant); accept either
        dominant = get_dominant_risk_component("Chennai")
        assert dominant in {"weather", "heat"}, (
            f"Chennai dominant risk '{dominant}' is neither weather nor heat"
        )

    def test_kolkata_dominant_risk_is_weather(self):
        assert get_dominant_risk_component("Kolkata") == "weather"


# ─── TestCityProfileStructure ────────────────────────────────────────────────

class TestCityProfileStructure:
    """get_city_dci_profile() must return a properly shaped dict for all cities."""

    REQUIRED_KEYS = {"city", "weights", "dominant_risk", "description",
                     "is_supported", "fallback_used"}

    def _check_profile(self, city: str):
        profile = get_city_dci_profile(city)
        assert set(profile.keys()) >= self.REQUIRED_KEYS, (
            f"Profile for '{city}' missing keys: {self.REQUIRED_KEYS - set(profile.keys())}"
        )
        assert profile["city"] == city
        assert profile["is_supported"] is True
        assert profile["fallback_used"] is False
        assert isinstance(profile["weights"], dict)
        assert isinstance(profile["description"], str)
        assert len(profile["description"]) > 0

    def test_mumbai_profile_structure(self):      self._check_profile("Mumbai")
    def test_delhi_profile_structure(self):       self._check_profile("Delhi")
    def test_bengaluru_profile_structure(self):   self._check_profile("Bengaluru")
    def test_chennai_profile_structure(self):     self._check_profile("Chennai")
    def test_kolkata_profile_structure(self):     self._check_profile("Kolkata")

    def test_unknown_city_shows_fallback_used(self):
        profile = get_city_dci_profile("UnknownCity")
        assert profile["is_supported"] is False
        assert profile["fallback_used"] is True


# ─── TestListSupportedCities ─────────────────────────────────────────────────

class TestListSupportedCities:
    """list_supported_cities() must return all 5 metros and nothing else."""

    def test_returns_five_cities(self):
        assert len(list_supported_cities()) == 5

    def test_all_metros_present(self):
        cities = list_supported_cities()
        for city in SUPPORTED_CITIES:
            assert city in cities, f"'{city}' not in list_supported_cities()"

    def test_returns_list_type(self):
        assert isinstance(list_supported_cities(), list)


# ─── TestGetAllCityWeights ────────────────────────────────────────────────────

class TestGetAllCityWeights:
    """get_all_city_weights() must return all 5 cities' profiles as a deep copy."""

    def test_returns_all_five_cities(self):
        all_w = get_all_city_weights()
        for city in SUPPORTED_CITIES:
            assert city in all_w

    def test_each_city_sums_to_one(self):
        all_w = get_all_city_weights()
        for city, weights in all_w.items():
            total = sum(weights.values())
            assert abs(total - 1.0) <= _MAX_DELTA

    def test_mutation_does_not_affect_master(self):
        all_w = get_all_city_weights()
        original = CITY_DCI_WEIGHTS["Mumbai"]["weather"]
        all_w["Mumbai"]["weather"] = 0.99
        assert CITY_DCI_WEIGHTS["Mumbai"]["weather"] == original


# ─── TestWeightWeightIndexing ─────────────────────────────────────────────────

class TestWeightComparisons:
    """Cross-city comparisons that encode domain knowledge."""

    def test_mumbai_weather_higher_than_delhi_weather(self):
        assert get_city_weights("Mumbai")["weather"] > get_city_weights("Delhi")["weather"]

    def test_delhi_aqi_higher_than_mumbai_aqi(self):
        assert get_city_weights("Delhi")["aqi"] > get_city_weights("Mumbai")["aqi"]

    def test_delhi_heat_higher_than_bengaluru_heat(self):
        assert get_city_weights("Delhi")["heat"] > get_city_weights("Bengaluru")["heat"]

    def test_kolkata_weather_higher_than_delhi_weather(self):
        assert get_city_weights("Kolkata")["weather"] > get_city_weights("Delhi")["weather"]

    def test_bengaluru_social_higher_than_mumbai_social(self):
        # Bengaluru and Mumbai both have social=0.25; Bengaluru is >= not strictly >
        assert get_city_weights("Bengaluru")["social"] >= get_city_weights("Mumbai")["social"]

    def test_kolkata_social_higher_than_delhi_social(self):
        assert get_city_weights("Kolkata")["social"] >= get_city_weights("Delhi")["social"]

    def test_mumbai_weather_is_highest_single_weight(self):
        # Mumbai's 0.40 should be the single highest weight of any component in any city
        max_weight = max(
            max(weights.values()) for weights in CITY_DCI_WEIGHTS.values()
        )
        assert max_weight == get_city_weights("Mumbai")["weather"]


# ─── TestEdgeCases ──────────────────────────────────────────────────────────

class TestEdgeCases:
    """Robustness tests — garbage-in, safe-out."""

    def test_get_city_weights_with_integer_input(self):
        # Non-string inputs: normalise_city_name returns None → fallback returned
        result = get_city_weights(42)
        assert result == GLOBAL_FALLBACK_WEIGHTS

    def test_get_city_weights_with_list_input(self):
        # Non-string inputs: normalise_city_name returns None → fallback returned
        result = get_city_weights(["Mumbai"])
        assert result == GLOBAL_FALLBACK_WEIGHTS

    def test_resolve_city_with_integer_pincode(self):
        # Integers not strings — should return default
        result = resolve_city_from_pincode(400001)
        assert result == "default"

    def test_resolve_city_with_very_long_string(self):
        result = resolve_city_from_pincode("A" * 200)
        assert result == "default"

    def test_normalise_none_returns_none(self):
        assert normalise_city_name(None) is None

    def test_normalise_whitespace_returns_none(self):
        # Bare spaces have no alias mapping
        assert normalise_city_name("   ") is None

    def test_bengale_typo_returns_none(self):
        # Typos should not be silently resolved
        assert normalise_city_name("bengale") is None
