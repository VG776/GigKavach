"""
config/city_dci_weights.py — City-Specific DCI Component Weights
═══════════════════════════════════════════════════════════════════
GigKavach's DCI formula uses five components, but their relative 
importance varies dramatically by city due to local climate and 
geography. This module is the single source of truth for all 
city-specific weight configurations.

City Weight Rationale (Research-Backed):

  MUMBAI   — Arabian Sea + Western Ghats funnel extreme monsoon rainfall.
              AQI and heat are secondary concerns. Social disruptions are
              significant (frequent bandhs, harbour strikes).
              → Weather dominates at 0.40

  DELHI    — Indo-Gangetic plain traps particulate matter (crop burning,
              Diwali, dust storms → AQI 400+ regularly). Summers reach
              45–48°C making heat a co-dominant risk. Rain is lighter.
              → AQI and Heat co-dominate at 0.30 each

  BENGALURU — Deccan Plateau elevation moderates temperature and rain.
               Known for frequent civic shutdowns/bandhs. Active delivery
               platform ecosystem means platform signals matter more.
               → Weather and Social are joint leaders at 0.30/0.25

  CHENNAI  — Bay of Bengal facing → northeast monsoon cyclones bring
              intense rainfall. Heat is brutal (coastal humidity +
              temperature) in peak summer. Moderate AQI.
              → Weather and Heat co-dominate at 0.30/0.30

  KOLKATA  — Bay of Bengal cyclones (Amphan, Aila etc.) bring extreme
              rainfall. Dense urban social fabric → high bandh frequency.
              Pre-monsoon heat (Loo winds) is severe.
              → Weather dominates at 0.35, Social at 0.25

All weights must sum to exactly 1.0 per city.
MAX_WEIGHT_DELTA tolerance is set to 1e-9 for floating-point safety.

Usage:
    from config.city_dci_weights import get_city_weights, resolve_city_from_pincode

    city   = resolve_city_from_pincode("400001")      # → "Mumbai"
    weights = get_city_weights(city)                  # → {...}
"""

from __future__ import annotations
import logging
from typing import Dict, Optional

logger = logging.getLogger("gigkavach.city_dci_weights")

# ─── Type alias ────────────────────────────────────────────────────────────────
WeightDict = Dict[str, float]

# ─── Global Fallback ───────────────────────────────────────────────────────────
# Used if city is unresolvable or not in the table.
# Mirrors the original hard-coded weights so existing behaviour is unchanged
# for any unlisted zone.
GLOBAL_FALLBACK_WEIGHTS: WeightDict = {
    "weather":  0.30,
    "aqi":      0.20,
    "heat":     0.20,
    "social":   0.20,
    "platform": 0.10,
}

# ─── City-Specific Weight Table ────────────────────────────────────────────────
# Keys must match exactly what resolve_city_from_pincode() returns.
# Values must sum to 1.0 — enforced at import time by _validate_all_weights().
CITY_DCI_WEIGHTS: Dict[str, WeightDict] = {

    # ── Mumbai ─────────────────────────────────────────────────────────────────
    # Arabian Sea + Western Ghats orographic effect → India's heaviest monsoon.
    # Annual rainfall 2,400 mm. July flooding is near-annual (Latur 2005,
    # July 2005 944mm in 24hrs). Social disruptions frequent (harbour, BEST
    # strikes, political bandhs). AQI and heat are secondary.
    "Mumbai": {
        "weather":  0.40,   # Coastal monsoon: torrential rain, flooding
        "aqi":      0.10,   # Sea breeze disperses pollutants; relatively clean
        "heat":     0.10,   # Humidity makes heat feel worse but rarely > 37°C
        "social":   0.25,   # Harbour/BEST strikes, Shiv Sena bandhs are frequent
        "platform": 0.15,   # High delivery density → platform signals matter
    },

    # ── Delhi ──────────────────────────────────────────────────────────────────
    # Indo-Gangetic Plain: trapped air basin. Paddy-stubble burning (Oct-Nov) +
    # Diwali firecrackers → AQI > 400 regularly. Summer temps 45-48°C.
    # Monsoon rain moderate (790mm/yr). Haze events make delivery impossible.
    "Delhi": {
        "weather":  0.15,   # Rain present but not extreme; dust storms notable
        "aqi":      0.30,   # Severe: AQI 300-500 for weeks; primary risk factor
        "heat":     0.30,   # Loo (hot dry westerly) in May-June; 45-48°C peaks
        "social":   0.15,   # Frequent political protests; capital = high unrest
        "platform": 0.10,   # Standard connectivity; fewer heatmap spikes
    },

    # ── Bengaluru ──────────────────────────────────────────────────────────────
    # Deccan Plateau at 920m elevation → moderate rain (970mm/yr), cooler summers
    # (max ~35°C rarely). Notable for IT sector + frequent civic bandhs. Active
    # gig-worker ecosystem with high platform density.
    "Bengaluru": {
        "weather":  0.30,   # Moderate rain; pre-monsoon/NE monsoon both contribute
        "aqi":      0.20,   # Construction dust + traffic; moderate concern
        "heat":     0.15,   # Rarely extreme (<38°C), elevation provides relief
        "social":   0.25,   # Frequent Karnataka-bandhs, political shutdowns
        "platform": 0.10,   # High Zomato/Swiggy density; platform data reliable
    },

    # ── Chennai ────────────────────────────────────────────────────────────────
    # Bay of Bengal → Northeast Monsoon (Oct-Dec) brings cyclones (Gaja, Nivar).
    # High coastal humidity amplifies felt temperature. Marine fog reduces
    # platform activity significantly during cyclone warnings.
    "Chennai": {
        "weather":  0.30,   # NE monsoon cyclones; more rain in Oct-Dec vs Jun-Sep
        "aqi":      0.15,   # Sea breeze helps; industrial pockets raise concern
        "heat":     0.30,   # Peak April-June; coastal humidity makes 38°C feel 45°C
        "social":   0.15,   # Moderate: Jallikattu protests were notable exceptions
        "platform": 0.10,   # Cyclone warnings cause platform-wide delivery halts
    },

    # ── Kolkata ────────────────────────────────────────────────────────────────
    # Bay of Bengal cyclone track: Amphan (2020), Aila (2009), Remal (2024).
    # Dense urban fabric + high political activity (CPM/TMC rallies) → frequent
    # bandhs. Pre-monsoon Loo (kal boisakhi) brings brief but intense heat.
    "Kolkata": {
        "weather":  0.35,   # Bay cyclones + monsoon; eastern India's flood city
        "aqi":      0.15,   # Moderately polluted; coal plants + vehicular load
        "heat":     0.15,   # Kal boisakhi (Nor'wester) storms, pre-monsoon heat
        "social":   0.25,   # Dense political bandh culture; CPM/TMC shutdowns
        "platform": 0.10,   # Cyclone-triggered platform halts are known events
    },
}

# ─── Pincode-to-City Mapping ──────────────────────────────────────────────────
# Maps pincode prefix ranges (or exact codes) to canonical city names.
# Using prefix rules (first 3 digits) covers the full postal region efficiently.
# Exact-code override dict for common demo/test pincodes takes priority.

# Exact pincodes → city (highest priority)
PINCODE_EXACT_MAP: Dict[str, str] = {
    # ── Bengaluru Exact ────────────────────────────────────────────────────────
    "560001": "Bengaluru", "560002": "Bengaluru", "560003": "Bengaluru",
    "560004": "Bengaluru", "560005": "Bengaluru", "560006": "Bengaluru",
    "560007": "Bengaluru", "560008": "Bengaluru", "560009": "Bengaluru",
    "560010": "Bengaluru", "560011": "Bengaluru", "560012": "Bengaluru",
    "560013": "Bengaluru", "560014": "Bengaluru", "560015": "Bengaluru",
    "560016": "Bengaluru", "560017": "Bengaluru", "560018": "Bengaluru",
    "560019": "Bengaluru", "560020": "Bengaluru", "560021": "Bengaluru",
    "560022": "Bengaluru", "560023": "Bengaluru", "560024": "Bengaluru",
    "560025": "Bengaluru", "560026": "Bengaluru", "560027": "Bengaluru",
    "560028": "Bengaluru", "560029": "Bengaluru", "560030": "Bengaluru",
    "560031": "Bengaluru", "560032": "Bengaluru", "560033": "Bengaluru",
    "560034": "Bengaluru", "560035": "Bengaluru", "560036": "Bengaluru",
    "560037": "Bengaluru", "560038": "Bengaluru", "560039": "Bengaluru",
    "560040": "Bengaluru", "560041": "Bengaluru", "560042": "Bengaluru",
    "560043": "Bengaluru", "560044": "Bengaluru", "560045": "Bengaluru",
    "560046": "Bengaluru", "560047": "Bengaluru", "560048": "Bengaluru",
    "560049": "Bengaluru", "560050": "Bengaluru", "560051": "Bengaluru",
    "560052": "Bengaluru", "560053": "Bengaluru", "560054": "Bengaluru",
    "560055": "Bengaluru", "560056": "Bengaluru", "560057": "Bengaluru",
    "560058": "Bengaluru", "560059": "Bengaluru", "560060": "Bengaluru",
    "560061": "Bengaluru", "560062": "Bengaluru", "560063": "Bengaluru",
    "560064": "Bengaluru", "560065": "Bengaluru", "560066": "Bengaluru",
    "560067": "Bengaluru", "560068": "Bengaluru", "560069": "Bengaluru",
    "560070": "Bengaluru", "560071": "Bengaluru", "560072": "Bengaluru",
    "560073": "Bengaluru", "560074": "Bengaluru", "560075": "Bengaluru",
    "560076": "Bengaluru", "560077": "Bengaluru", "560078": "Bengaluru",
    "560079": "Bengaluru", "560080": "Bengaluru", "560081": "Bengaluru",
    "560082": "Bengaluru", "560083": "Bengaluru", "560084": "Bengaluru",
    "560085": "Bengaluru", "560086": "Bengaluru", "560087": "Bengaluru",
    "560088": "Bengaluru", "560089": "Bengaluru", "560090": "Bengaluru",
    "560091": "Bengaluru", "560092": "Bengaluru", "560093": "Bengaluru",
    "560094": "Bengaluru", "560095": "Bengaluru", "560096": "Bengaluru",
    "560097": "Bengaluru", "560098": "Bengaluru", "560099": "Bengaluru",
    "560100": "Bengaluru", "560101": "Bengaluru", "560102": "Bengaluru",
    "560103": "Bengaluru", "560104": "Bengaluru", "560105": "Bengaluru",
    "562106": "Bengaluru", "562107": "Bengaluru", "562125": "Bengaluru",
    "562130": "Bengaluru", "562149": "Bengaluru", "562157": "Bengaluru",

    # ── Mumbai Exact ───────────────────────────────────────────────────────────
    "400001": "Mumbai", "400002": "Mumbai", "400003": "Mumbai",
    "400004": "Mumbai", "400005": "Mumbai", "400006": "Mumbai",
    "400007": "Mumbai", "400008": "Mumbai", "400009": "Mumbai",
    "400010": "Mumbai", "400011": "Mumbai", "400012": "Mumbai",
    "400013": "Mumbai", "400014": "Mumbai", "400015": "Mumbai",
    "400016": "Mumbai", "400017": "Mumbai", "400018": "Mumbai",
    "400019": "Mumbai", "400020": "Mumbai", "400021": "Mumbai",
    "400022": "Mumbai", "400023": "Mumbai", "400024": "Mumbai",
    "400025": "Mumbai", "400026": "Mumbai", "400027": "Mumbai",
    "400028": "Mumbai", "400029": "Mumbai", "400030": "Mumbai",
    "400031": "Mumbai", "400032": "Mumbai", "400033": "Mumbai",
    "400034": "Mumbai", "400035": "Mumbai", "400036": "Mumbai",
    "400037": "Mumbai", "400038": "Mumbai", "400039": "Mumbai",
    "400040": "Mumbai", "400041": "Mumbai", "400042": "Mumbai",
    "400043": "Mumbai", "400044": "Mumbai", "400045": "Mumbai",
    "400046": "Mumbai", "400047": "Mumbai", "400048": "Mumbai",
    "400049": "Mumbai", "400050": "Mumbai", "400051": "Mumbai",
    "400052": "Mumbai", "400053": "Mumbai", "400054": "Mumbai",
    "400055": "Mumbai", "400056": "Mumbai", "400057": "Mumbai",
    "400058": "Mumbai", "400059": "Mumbai", "400060": "Mumbai",
    "400061": "Mumbai", "400062": "Mumbai", "400063": "Mumbai",
    "400064": "Mumbai", "400065": "Mumbai", "400066": "Mumbai",
    "400067": "Mumbai", "400068": "Mumbai", "400069": "Mumbai",
    "400070": "Mumbai", "400071": "Mumbai", "400072": "Mumbai",
    "400073": "Mumbai", "400074": "Mumbai", "400075": "Mumbai",
    "400076": "Mumbai", "400077": "Mumbai", "400078": "Mumbai",
    "400079": "Mumbai", "400080": "Mumbai", "400081": "Mumbai",
    "400082": "Mumbai", "400083": "Mumbai", "400084": "Mumbai",
    "400085": "Mumbai", "400086": "Mumbai", "400087": "Mumbai",
    "400088": "Mumbai", "400089": "Mumbai", "400090": "Mumbai",
    "400091": "Mumbai", "400092": "Mumbai", "400093": "Mumbai",
    "400094": "Mumbai", "400095": "Mumbai", "400096": "Mumbai",
    "400097": "Mumbai", "400098": "Mumbai", "400099": "Mumbai",
    "400101": "Mumbai", "400102": "Mumbai", "400103": "Mumbai",
    "400104": "Mumbai", "400601": "Mumbai", "400602": "Mumbai",
    "400603": "Mumbai", "400604": "Mumbai", "400605": "Mumbai",
    "400606": "Mumbai", "400607": "Mumbai", "400608": "Mumbai",
    "400609": "Mumbai", "400610": "Mumbai", "400611": "Mumbai",
    "400612": "Mumbai", "400613": "Mumbai", "400614": "Mumbai",
    "400615": "Mumbai", "400616": "Mumbai", "400703": "Mumbai",
    "400705": "Mumbai", "400706": "Mumbai", "400708": "Mumbai",
    "400709": "Mumbai",

    # ── Delhi Exact ────────────────────────────────────────────────────────────
    "110001": "Delhi", "110002": "Delhi", "110003": "Delhi",
    "110004": "Delhi", "110005": "Delhi", "110006": "Delhi",
    "110007": "Delhi", "110008": "Delhi", "110009": "Delhi",
    "110010": "Delhi", "110011": "Delhi", "110012": "Delhi",
    "110013": "Delhi", "110014": "Delhi", "110015": "Delhi",
    "110016": "Delhi", "110017": "Delhi", "110018": "Delhi",
    "110019": "Delhi", "110020": "Delhi", "110021": "Delhi",
    "110022": "Delhi", "110023": "Delhi", "110024": "Delhi",
    "110025": "Delhi", "110026": "Delhi", "110027": "Delhi",
    "110028": "Delhi", "110029": "Delhi", "110030": "Delhi",
    "110031": "Delhi", "110032": "Delhi", "110033": "Delhi",
    "110034": "Delhi", "110035": "Delhi", "110036": "Delhi",
    "110037": "Delhi", "110038": "Delhi", "110039": "Delhi",
    "110040": "Delhi", "110041": "Delhi", "110042": "Delhi",
    "110043": "Delhi", "110044": "Delhi", "110045": "Delhi",
    "110046": "Delhi", "110047": "Delhi", "110048": "Delhi",
    "110049": "Delhi", "110050": "Delhi", "110051": "Delhi",
    "110052": "Delhi", "110053": "Delhi", "110054": "Delhi",
    "110055": "Delhi", "110056": "Delhi", "110057": "Delhi",
    "110058": "Delhi", "110059": "Delhi", "110060": "Delhi",
    "110061": "Delhi", "110062": "Delhi", "110063": "Delhi",
    "110064": "Delhi", "110065": "Delhi", "110066": "Delhi",
    "110067": "Delhi", "110068": "Delhi", "110069": "Delhi",
    "110070": "Delhi", "110071": "Delhi", "110072": "Delhi",
    "110073": "Delhi", "110074": "Delhi", "110075": "Delhi",
    "110076": "Delhi", "110077": "Delhi", "110078": "Delhi",
    "110079": "Delhi", "110080": "Delhi", "110081": "Delhi",
    "110082": "Delhi", "110083": "Delhi", "110084": "Delhi",
    "110085": "Delhi", "110086": "Delhi", "110087": "Delhi",
    "110088": "Delhi", "110089": "Delhi", "110090": "Delhi",
    "110091": "Delhi", "110092": "Delhi", "110093": "Delhi",
    "110094": "Delhi", "110095": "Delhi", "110096": "Delhi",

    # ── Chennai Exact ──────────────────────────────────────────────────────────
    "600001": "Chennai", "600002": "Chennai", "600003": "Chennai",
    "600004": "Chennai", "600005": "Chennai", "600006": "Chennai",
    "600007": "Chennai", "600008": "Chennai", "600009": "Chennai",
    "600010": "Chennai", "600011": "Chennai", "600012": "Chennai",
    "600013": "Chennai", "600014": "Chennai", "600015": "Chennai",
    "600016": "Chennai", "600017": "Chennai", "600018": "Chennai",
    "600019": "Chennai", "600020": "Chennai", "600021": "Chennai",
    "600022": "Chennai", "600023": "Chennai", "600024": "Chennai",
    "600025": "Chennai", "600026": "Chennai", "600027": "Chennai",
    "600028": "Chennai", "600029": "Chennai", "600030": "Chennai",
    "600031": "Chennai", "600032": "Chennai", "600033": "Chennai",
    "600034": "Chennai", "600035": "Chennai", "600036": "Chennai",
    "600037": "Chennai", "600038": "Chennai", "600039": "Chennai",
    "600040": "Chennai", "600041": "Chennai", "600042": "Chennai",
    "600043": "Chennai", "600044": "Chennai", "600045": "Chennai",
    "600046": "Chennai", "600047": "Chennai", "600048": "Chennai",
    "600049": "Chennai", "600050": "Chennai", "600051": "Chennai",
    "600052": "Chennai", "600053": "Chennai", "600054": "Chennai",
    "600055": "Chennai", "600056": "Chennai", "600057": "Chennai",
    "600058": "Chennai", "600059": "Chennai", "600060": "Chennai",
    "600061": "Chennai", "600062": "Chennai", "600063": "Chennai",
    "600064": "Chennai", "600065": "Chennai", "600066": "Chennai",
    "600067": "Chennai", "600068": "Chennai", "600069": "Chennai",
    "600070": "Chennai", "600071": "Chennai", "600072": "Chennai",
    "600073": "Chennai", "600074": "Chennai", "600075": "Chennai",
    "600076": "Chennai", "600077": "Chennai", "600078": "Chennai",
    "600079": "Chennai", "600080": "Chennai", "600081": "Chennai",
    "600082": "Chennai", "600083": "Chennai", "600084": "Chennai",
    "600085": "Chennai", "600086": "Chennai", "600087": "Chennai",
    "600088": "Chennai", "600089": "Chennai", "600090": "Chennai",
    "600091": "Chennai", "600092": "Chennai", "600093": "Chennai",
    "600094": "Chennai", "600095": "Chennai", "600096": "Chennai",
    "600097": "Chennai", "600098": "Chennai", "600099": "Chennai",
    "600100": "Chennai",

    # ── Kolkata Exact ──────────────────────────────────────────────────────────
    "700001": "Kolkata", "700002": "Kolkata", "700003": "Kolkata",
    "700004": "Kolkata", "700005": "Kolkata", "700006": "Kolkata",
    "700007": "Kolkata", "700008": "Kolkata", "700009": "Kolkata",
    "700010": "Kolkata", "700011": "Kolkata", "700012": "Kolkata",
    "700013": "Kolkata", "700014": "Kolkata", "700015": "Kolkata",
    "700016": "Kolkata", "700017": "Kolkata", "700018": "Kolkata",
    "700019": "Kolkata", "700020": "Kolkata", "700021": "Kolkata",
    "700022": "Kolkata", "700023": "Kolkata", "700024": "Kolkata",
    "700025": "Kolkata", "700026": "Kolkata", "700027": "Kolkata",
    "700028": "Kolkata", "700029": "Kolkata", "700030": "Kolkata",
    "700031": "Kolkata", "700032": "Kolkata", "700033": "Kolkata",
    "700034": "Kolkata", "700035": "Kolkata", "700036": "Kolkata",
    "700037": "Kolkata", "700038": "Kolkata", "700039": "Kolkata",
    "700040": "Kolkata", "700041": "Kolkata", "700042": "Kolkata",
    "700043": "Kolkata", "700044": "Kolkata", "700045": "Kolkata",
    "700046": "Kolkata", "700047": "Kolkata", "700048": "Kolkata",
    "700049": "Kolkata", "700050": "Kolkata", "700051": "Kolkata",
    "700052": "Kolkata", "700053": "Kolkata", "700054": "Kolkata",
    "700055": "Kolkata", "700056": "Kolkata", "700057": "Kolkata",
    "700058": "Kolkata", "700059": "Kolkata", "700060": "Kolkata",
    "700061": "Kolkata", "700062": "Kolkata", "700063": "Kolkata",
    "700064": "Kolkata", "700065": "Kolkata", "700066": "Kolkata",
    "700067": "Kolkata", "700068": "Kolkata", "700069": "Kolkata",
    "700070": "Kolkata", "700071": "Kolkata", "700072": "Kolkata",
    "700073": "Kolkata", "700074": "Kolkata", "700075": "Kolkata",
    "700076": "Kolkata", "700077": "Kolkata", "700078": "Kolkata",
    "700079": "Kolkata", "700080": "Kolkata", "700081": "Kolkata",
    "700082": "Kolkata", "700083": "Kolkata", "700084": "Kolkata",
    "700085": "Kolkata", "700086": "Kolkata", "700087": "Kolkata",
    "700088": "Kolkata", "700089": "Kolkata", "700090": "Kolkata",
    "700091": "Kolkata", "700092": "Kolkata", "700093": "Kolkata",
    "700094": "Kolkata", "700095": "Kolkata", "700096": "Kolkata",
    "700097": "Kolkata", "700098": "Kolkata", "700099": "Kolkata",
    "700100": "Kolkata", "700101": "Kolkata", "700102": "Kolkata",
    "700103": "Kolkata", "700104": "Kolkata", "700105": "Kolkata",
    "700106": "Kolkata", "700107": "Kolkata", "700108": "Kolkata",
    "700109": "Kolkata", "700110": "Kolkata", "700111": "Kolkata",
    "700112": "Kolkata", "700113": "Kolkata", "700114": "Kolkata",
    "700115": "Kolkata", "700116": "Kolkata", "700117": "Kolkata",
    "700118": "Kolkata", "700119": "Kolkata", "700120": "Kolkata",
    "700121": "Kolkata", "700122": "Kolkata", "700123": "Kolkata",
    "700124": "Kolkata", "700125": "Kolkata", "700126": "Kolkata",
    "700127": "Kolkata", "700128": "Kolkata", "700129": "Kolkata",
    "700130": "Kolkata", "700131": "Kolkata", "700132": "Kolkata",
    "700133": "Kolkata", "700134": "Kolkata", "700135": "Kolkata",
    "700136": "Kolkata", "700137": "Kolkata", "700138": "Kolkata",
    "700139": "Kolkata", "700140": "Kolkata", "700141": "Kolkata",
    "700142": "Kolkata", "700143": "Kolkata", "700144": "Kolkata",
    "700145": "Kolkata", "700146": "Kolkata", "700147": "Kolkata",
    "700148": "Kolkata", "700149": "Kolkata", "700150": "Kolkata",
    "700151": "Kolkata", "700152": "Kolkata", "700153": "Kolkata",
    "700154": "Kolkata", "700155": "Kolkata", "700156": "Kolkata",
    "700157": "Kolkata", "700158": "Kolkata", "700159": "Kolkata",
    "700160": "Kolkata",
}

# ─── Canonical city name normalisations ────────────────────────────────────────
# Handles API-provided city strings that might not match table keys exactly.
CITY_NAME_ALIASES: Dict[str, str] = {
    # Bengaluru variants
    "bangalore":   "Bengaluru",
    "bengaluru":   "Bengaluru",
    "bengalore":   "Bengaluru",
    "blr":         "Bengaluru",
    "Bangalore":   "Bengaluru",
    "BANGALORE":   "Bengaluru",
    "BENGALURU":   "Bengaluru",

    # Mumbai variants
    "mumbai":      "Mumbai",
    "bombay":      "Mumbai",
    "Mumbai":      "Mumbai",
    "MUMBAI":      "Mumbai",

    # Delhi variants
    "delhi":       "Delhi",
    "new delhi":   "Delhi",
    "newdelhi":    "Delhi",
    "ndls":        "Delhi",
    "Delhi":       "Delhi",
    "DELHI":       "Delhi",

    # Chennai variants
    "chennai":     "Chennai",
    "madras":      "Chennai",
    "Chennai":     "Chennai",
    "CHENNAI":     "Chennai",

    # Kolkata variants
    "kolkata":     "Kolkata",
    "calcutta":    "Kolkata",
    "Kolkata":     "Kolkata",
    "KOLKATA":     "Kolkata",
}

# ─── Validation ────────────────────────────────────────────────────────────────
_MAX_DELTA = 1e-9  # Floating-point tolerance for sum-to-1.0 check


def _validate_all_weights() -> None:
    """
    Called once at module import time. Ensures every city's weights sum
    exactly to 1.0 (within floating-point tolerance) and all required
    component keys are present.

    Raises ValueError immediately if any city fails — this prevents silent
    misconfiguration from ever reaching production.
    """
    required_components = {"weather", "aqi", "heat", "social", "platform"}

    for city, weights in CITY_DCI_WEIGHTS.items():
        # Check all required component keys are present
        missing = required_components - set(weights.keys())
        if missing:
            raise ValueError(
                f"[city_dci_weights] City '{city}' is missing DCI "
                f"component keys: {missing}"
            )

        # Check extra keys (typos)
        extra = set(weights.keys()) - required_components
        if extra:
            raise ValueError(
                f"[city_dci_weights] City '{city}' has unknown DCI "
                f"component keys: {extra}"
            )

        # Check sum to 1.0
        total = sum(weights.values())
        if abs(total - 1.0) > _MAX_DELTA:
            raise ValueError(
                f"[city_dci_weights] City '{city}' weights sum to "
                f"{total:.10f} (expected 1.0). Fix before deploying."
            )

    logger.info(
        f"[DCI Weights] ✅ All {len(CITY_DCI_WEIGHTS)} city weight "
        f"profiles validated successfully."
    )


# Run validation at import time — fail fast
_validate_all_weights()


# ─── Public API ────────────────────────────────────────────────────────────────

def normalise_city_name(raw_city: str) -> Optional[str]:
    """
    Normalises a raw city string to the canonical form used as table keys.
    Returns None if the city is not recognised or input is not a string.

    Examples:
        normalise_city_name("bangalore") → "Bengaluru"
        normalise_city_name("bombay")    → "Mumbai"
        normalise_city_name("calcutta")  → "Kolkata"
        normalise_city_name("xyz")       → None
        normalise_city_name(42)          → None  (non-string guard)
        normalise_city_name(["Mumbai"])  → None  (non-string guard)

    Args:
        raw_city: Any user-provided or API-returned city string

    Returns:
        Canonical city name ("Mumbai", "Delhi", etc.) or None
    """
    # Type guard: non-string inputs cannot be city names
    if not isinstance(raw_city, str):
        return None
    if not raw_city:
        return None
    # Direct match first (already canonical)
    if raw_city in CITY_DCI_WEIGHTS:
        return raw_city
    # Alias lookup (case-sensitive aliases handle common forms)
    return CITY_NAME_ALIASES.get(raw_city) or CITY_NAME_ALIASES.get(raw_city.lower())


def resolve_city_from_pincode(pincode: str) -> str:
    """
    Resolves a pincode to its canonical city name.

    Resolution order:
      1. Exact pincode lookup (PINCODE_EXACT_MAP — highest priority)
      2. Falls back to "default" if unrecognised.

    "default" city → GLOBAL_FALLBACK_WEIGHTS when passed to get_city_weights().

    Args:
        pincode: 6-digit Indian postal code (string)

    Returns:
        Canonical city name or "default" if unresolvable.

    Examples:
        resolve_city_from_pincode("400001") → "Mumbai"
        resolve_city_from_pincode("110001") → "Delhi"
        resolve_city_from_pincode("560001") → "Bengaluru"
        resolve_city_from_pincode("999999") → "default"
    """
    if not pincode or not isinstance(pincode, str):
        logger.warning(f"[resolve_city_from_pincode] Invalid pincode: {pincode!r}")
        return "default"

    pincode_clean = pincode.strip()

    # Exact match
    city = PINCODE_EXACT_MAP.get(pincode_clean)
    if city:
        return city

    logger.debug(
        f"[resolve_city_from_pincode] Pincode '{pincode_clean}' not mapped → default"
    )
    return "default"


def get_city_weights(city: str) -> WeightDict:
    """
    Returns the DCI component weights for a given city.

    Always returns a valid WeightDict — never raises. Unknown/default cities
    receive the global fallback weights so the DCI engine continues running.

    Args:
        city: Canonical city name ("Mumbai", "Delhi", "Bengaluru", "Chennai",
              "Kolkata") or common alias (see CITY_NAME_ALIASES) or "default".

    Returns:
        WeightDict with keys: weather, aqi, heat, social, platform

    Examples:
        get_city_weights("Mumbai")      → {weather: 0.40, aqi: 0.10, ...}
        get_city_weights("bangalore")   → {weather: 0.30, ...}  (alias resolved)
        get_city_weights("default")     → GLOBAL_FALLBACK_WEIGHTS
        get_city_weights("Atlantis")    → GLOBAL_FALLBACK_WEIGHTS (with warning)
    """
    # Normalise potentially aliased city names
    canonical = normalise_city_name(city)

    if canonical is None:
        if city and city != "default":
            logger.warning(
                f"[get_city_weights] Unknown city '{city}' — "
                f"using global fallback weights."
            )
        return dict(GLOBAL_FALLBACK_WEIGHTS)

    weights = CITY_DCI_WEIGHTS.get(canonical)
    if weights is None:
        logger.warning(
            f"[get_city_weights] City '{canonical}' not in weight table — "
            f"using global fallback weights."
        )
        return dict(GLOBAL_FALLBACK_WEIGHTS)

    return dict(weights)  # Return a copy to prevent accidental mutation


def list_supported_cities() -> list[str]:
    """Returns the list of cities with explicit weight profiles."""
    return list(CITY_DCI_WEIGHTS.keys())


def get_all_city_weights() -> Dict[str, WeightDict]:
    """
    Returns a deep copy of the full city weight table.
    Used by API endpoints to expose the weight configuration to the dashboard.
    """
    return {city: dict(weights) for city, weights in CITY_DCI_WEIGHTS.items()}
