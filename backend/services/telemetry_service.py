"""
services/telemetry_service.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Processes raw behavioral telemetry from the worker PWA.
Analyzes movement patterns, velocity anomalies, and GPS jumps to detect spoofing.
"""

import logging
import json
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any
from utils.redis_client import get_redis

logger = logging.getLogger("gigkavach.telemetry")

class TelemetryProcessor:
    def __init__(self):
        self.EARTH_RADIUS_KM = 6371.0

    async def save_telemetry(self, worker_id: str, coordinates: List[float], speed: float):
        """Persists raw telemetry in Redis for real-time window analysis."""
        redis = await get_redis()
        key = f"telemetry:{worker_id}"
        
        entry = {
            "lat": coordinates[0],
            "lng": coordinates[1],
            "speed": speed,
            "captured_at": datetime.now().isoformat()
        }
        
        # Keep a sliding window of the last 20 samples
        await redis.lpush(key, json.dumps(entry))
        await redis.ltrim(key, 0, 19)
        await redis.expire(key, 3600)  # 1 hour TTL

    async def analyze_movement(self, worker_id: str) -> Dict[str, Any]:
        """Performs behavioral analysis on the telemetry window."""
        redis = await get_redis()
        key = f"telemetry:{worker_id}"
        
        raw_samples = await redis.lrange(key, 0, -1)
        if not raw_samples or len(raw_samples) < 2:
            return {"status": "insufficient_data", "is_suspicious": False}
            
        samples = [json.loads(s) for s in raw_samples]
        
        # 1. Calculation: Velocity Anomalies (Teleportation)
        jumps = 0
        total_dist = 0.0
        for i in range(len(samples) - 1):
            dist = self._haversine(
                samples[i]["lat"], samples[i]["lng"],
                samples[i+1]["lat"], samples[i+1]["lng"]
            )
            total_dist += dist
            
            # Time delta
            t1 = datetime.fromisoformat(samples[i]["captured_at"])
            t2 = datetime.fromisoformat(samples[i+1]["captured_at"])
            dt_seconds = abs((t1 - t2).total_seconds())
            
            if dt_seconds > 0:
                velocity_kmh = (dist / dt_seconds) * 3600
                if velocity_kmh > 120:  # Physically impossible for a gig vehicle (delivery bike)
                    jumps += 1

        # 2. Calculation: Stationary Spoofer (No movement vs High claimed distance)
        avg_speed_measured = total_dist / max(1, len(samples))
        
        analysis = {
            "status": "active",
            "samples_analyzed": len(samples),
            "teleportation_jumps": jumps,
            "total_distance_km": total_dist,
            "is_suspicious": jumps > 2 or (total_dist < 0.01 and len(samples) > 10)
        }
        
        return analysis

    def _haversine(self, lat1, lon1, lat2, lon2):
        """Calculates distance between two points in KM."""
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2)**2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2)
        c = 2 * math.asin(math.sqrt(a))
        return self.EARTH_RADIUS_KM * c

telemetry_processor = TelemetryProcessor()
