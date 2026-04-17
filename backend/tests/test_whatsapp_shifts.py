
import asyncio
import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.onboarding_handlers import route_message
from services.gigscore_service import GigScoreEvent

class TestWhatsAppShiftIntegration(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.phone = "+918074725459"
        self.worker_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
        
    @patch("services.onboarding_handlers.get_supabase")
    @patch("services.onboarding_handlers.get_redis")
    @patch("services.onboarding_handlers.update_gig_score")
    async def test_full_shift_lifecycle(self, mock_update_score, mock_get_redis, mock_get_sb):
        # 1. Mock Supabase
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        
        # Mock worker lookup
        mock_table = mock_sb.table.return_value
        mock_select = mock_table.select.return_value
        mock_eq = mock_select.eq.return_value
        mock_eq.execute.return_value = MagicMock(data=[{
            "id": self.worker_id,
            "language": "en",
            "is_active": True,
            "is_working": False
        }])
        
        # 2. Mock Redis
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis
        
        # --- TEST START COMMAND ---
        print("\n[TEST] Sending START command...")
        response = await route_message(self.phone, "START")
        print(f"RESPONSE:\n{response}")
        
        self.assertIn("Shift Started", response)
        self.assertIn("📊 *Live Dashboard:*", response)
        # Verify DB updated
        mock_sb.table("workers").update.assert_any_call({"is_working": True, "last_seen_at": unittest.mock.ANY})
        # Verify Redis key set
        mock_redis.set.assert_called_once()
        print("✅ START command handled correctly.")
        
        # --- TEST STOP COMMAND ---
        print("[TEST] Sending STOP command...")
        # Mock Redis returning a start time
        start_time = (datetime.now() - timedelta(hours=4)).isoformat()
        mock_redis.get.return_value = start_time
        
        response = await route_message(self.phone, "STOP")
        print(f"RESPONSE:\n{response}")
        
        self.assertIn("Shift Ended", response)
        self.assertIn("💹 *Check GigScore Rewards:*", response)
        self.assertIn("4h 0m", response)
        # Verify DB updated
        mock_sb.table("workers").update.assert_any_call({"is_working": False, "last_seen_at": unittest.mock.ANY})
        # Verify GigScore updated
        mock_update_score.assert_called_once_with(self.worker_id, GigScoreEvent.CLEAN_SHIFT)
        print("✅ STOP command handled correctly with GigScore boost.")

if __name__ == "__main__":
    unittest.main()
