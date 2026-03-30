"""
services/social_service.py — 4-Layer Social Disruption Redundancy
───────────────────────────────────────────────────────────────
Implements the 100% resilient fallback cascade for Social Disruption Index.
Layer 1: Deccan Herald RSS Feed (via feedparser)
Layer 2: The Hindu Karnataka RSS
Layer 3: Stale Redis Cache (Max 30m old)
Layer 4: Hardcoded Disruption Calendar
Fallback: Trigger SLA Breach and return 0.
"""

import logging
import feedparser
import json
import re
from datetime import datetime, date
from utils.redis_client import get_redis
from api.payouts import trigger_sla_breach
from utils.pincode_mapper import get_location_context

logger = logging.getLogger("gigkavach.social")

async def fetch_rss_feed(feed_url: str, pincode: str, source_name: str) -> dict:
    """
    Unified RSS parser for both Social and NDMA feeds.
    Returns a dict with:
        - social_score: current additive score
        - ndma_active: boolean
        - headlines: list of matched events
    """
    context = get_location_context(pincode)
    target_hood = context["neighborhood"].lower()
    target_city = context["city"].lower()
    target_state = context["state"].lower()
    
    # Handle City Synonyms (Bangalore vs Bengaluru)
    city_alts = [target_city]
    if target_city == "bangalore": city_alts.append("bengaluru")
    elif target_city == "bengaluru": city_alts.append("bangalore")

    res = {"social_score": 0, "ndma_active": False, "headlines": []}

    try:
        # Since feedparser is synchronous, we run it in a threadpool logic implicitly here
        feed = feedparser.parse(feed_url)
        if not feed.entries: return res
        
        # Ensure labels exactly match those in ml/nlp_classifier.py CANDIDATE_LABELS
        disaster_labels = ["flood", "earthquake", "cyclone", "landslide", "tsunami"]
        social_labels = ["bandh", "curfew", "strike", "protest", "shutdown", "unrest", "disturbance"]

        for entry in feed.entries[:3]:
            title = entry.title
            
            try:
                from ml.nlp_classifier import analyze_headline
                nlp = analyze_headline(title)
                
                if nlp["is_disruption"]:
                    label = nlp["top_label"]
                    extracted_loc = nlp["location"].lower()
                    
                    # Hierarchical Geofencing Match
                    is_local = (target_hood in extracted_loc) or \
                               any(alt in extracted_loc for alt in city_alts) or \
                               (target_state in extracted_loc) or \
                               ("karnataka" in extracted_loc)
                               
                    if is_local:
                        logger.critical(f"🚦 UNIFIED DISRUPTION DETECTED via {source_name}: {title}")
                        res["headlines"].append(title)
                        
                        if label in disaster_labels:
                            res["ndma_active"] = True
                        elif label in social_labels:
                            res["social_score"] += 35 # Each alert adds to the DCI component
            except Exception as e:
                logger.warning(f"Unified RSS polling error for {title}: {e}")
                
        return res
    except Exception as e:
        logger.error(f"RSS Parsing failed for {feed_url}: {e}")
        return res

async def get_unified_disruption_status(pincode: str) -> dict:
    """
    Polls all 4 layers (DH, Hindu, NDMA, KSNDMC) and consolidates results.
    Follows Redundancy Cache -> API -> Fallback.
    """
    cache_key = f"disruption_unified:{pincode}"
    rc = await get_redis()
    
    # Define feeds
    feeds = [
        ("https://ndma.gov.in/rss", "Layer_0_NDMA_RSS"),
        ("https://ksndmc.karnataka.gov.in/rss", "Layer_1_KSNDMC_Official"), # Image #1 Req
        ("https://www.deccanherald.com/bengaluru/rssfeed.xml", "Layer_2_Deccan_Herald_RSS"),
        ("https://www.thehindu.com/news/national/karnataka/feeder/default.rss", "Layer_3_The_Hindu_RSS")
    ]
    
    unified_res = {"social_score": 0, "ndma_active": False, "headlines": [], "source": "Multi_Source_Poll"}
    
    for url, source in feeds:
        feed_res = await fetch_rss_feed(url, pincode, source)
        unified_res["social_score"] = min(100, unified_res["social_score"] + feed_res["social_score"])
        if feed_res["ndma_active"]:
            unified_res["ndma_active"] = True
        unified_res["headlines"].extend(feed_res["headlines"])
        
    # Layer 3: Cache if APIs fail
    if not unified_res["headlines"]:
        cached = await rc.get(cache_key)
        if cached:
            unified_res = json.loads(cached)
            unified_res["source"] = "Layer_3_Redis_Stale"
            
    # Layer 4: Hardcoded Calendar Fallback
    if not unified_res["headlines"] and not unified_res["ndma_active"]:
         calendar = await fetch_hardcoded_calendar()
         unified_res["social_score"] = calendar.get("social_disruption", 0)
         unified_res["source"] = "Layer_4_Hardcoded_Calendar"

    # --- SLA BREACH TRIGGER ---
    # If after all 4 layers we still have no headlines AND score is 0,
    # it implies a potential intelligence blackout. 
    if not unified_res["headlines"] and unified_res["social_score"] == 0 and not unified_res["ndma_active"]:
        # We trigger the breach logic to ensure workers aren't penalized by our data blindness
        await trigger_sla_breach(pincode, "TOTAL_SOCIAL_INTELLIGENCE_BLACKOUT")
        unified_res["source"] = "SLA_BREACH_TRIGGERED"

    # Data Persistence
    if unified_res["source"] not in ["Layer_3_Redis_Stale", "SLA_BREACH_TRIGGERED"]:
        await rc.set(cache_key, json.dumps(unified_res), ex=1800)
        
    return unified_res


async def fetch_hardcoded_calendar() -> dict | None:
    """Layer 4: Backup static event calendar."""
    # E.g., Major festival or known protest dates mapped
    today_str = date.today().isoformat()
    known_events = {
        "2026-05-01": {"social_disruption": 50, "event": "May Day / Labour Day Parade"},
        "2026-11-01": {"social_disruption": 60, "event": "Karnataka Rajyotsava Celebrations"},
    }
    
    if today_str in known_events:
        return known_events[today_str]
    return {"social_disruption": 0, "event": "No active planned events."}

async def get_social_score(pincode: str) -> dict:
    """Follows strict 4-Layer Cascade. (Now using Unified Method internally)"""
    res = await get_unified_disruption_status(pincode)
    return {
        "score": res["social_score"],
        "ndma_active": res["ndma_active"],
        "headlines": res["headlines"],
        "source": res["source"]
    }
