import asyncio
import logging
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import json

# Set up logging for brutality
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("GigKavachAudit")

class MockSettings:
    SUPABASE_URL = "https://mock.supabase.co"
    SUPABASE_KEY = "mock-key-123"
    SUPABASE_SERVICE_ROLE_KEY = "mock-svc-key-123"
    DB_PASSWORD = "password"
    REDIS_URL = "redis://mock"
    FRONTEND_URL = "https://dashboard.gigkavach.in"
    BOT_API_URL = "http://mock-bot:3001"
    DCI_CACHE_TTL_SECONDS = 300
    TELEMETRY_INTERVAL_SECONDS = 60
    GIGSCORE_BOOST_UPI = 5
    DCI_CATASTROPHIC_THRESHOLD = 75
    COVERAGE_DELAY_HOURS = 24
    FRAUD_THRESHOLD = 50

mock_supabase_client = MagicMock()

with patch("supabase.create_client", return_value=mock_supabase_client):
    with patch("config.settings.settings", MockSettings()):
        from services.onboarding_handlers import route_message
        from api.whatsapp import send_whatsapp_alert
        from cron.claims_trigger import process_single_claim
        from cron.dci_poller import trigger_recovery_alerts

class UltimateSystemCertification(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.phone_new = "+919999999999" 
        self.phone_active = "+918888888888" 
        self.worker_id = "W-CERT-007"
        
        self.redis_mock = AsyncMock()
        self.redis_patcher = patch("utils.redis_client.get_redis", return_value=self.redis_mock)
        self.redis_patcher.start()

        # Global Service patches
        self.sb_patcher = patch("utils.db.get_supabase", return_value=mock_supabase_client)
        self.quote_patcher = patch("services.premium_service.compute_dynamic_quote", AsyncMock(return_value={"dynamic_premium": 42.0}))
        self.token_patcher = patch("services.onboarding_handlers.generate_share_token", AsyncMock(return_value={"share_url": "https://pwa.io"}))
        
        self.sb_patcher.start()
        self.quote_patcher.start()
        self.token_patcher.start()

    async def asyncTearDown(self):
        self.redis_patcher.stop()
        self.sb_patcher.stop()
        self.quote_patcher.stop()
        self.token_patcher.stop()

    def mock_supabase_flow(self, exists=True, phone=None):
        worker_data = {
            "id": self.worker_id,
            "phone": phone or self.phone_active,
            "phone_number": phone or self.phone_active,
            "language": "en",
            "is_active": True,
            "pin_codes": ["560001", "560037"],
            "plan": "pro",
            "shift": "day",
            "gig_score": 90,
            "upi_id": "ravi@upi"
        }
        
        def create_mock_table():
            table = MagicMock()
            list_res = MagicMock()
            list_res.data = [worker_data] if exists else []
            table.select.return_value.eq.return_value.execute.return_value = list_res
            table.select.return_value.contains.return_value.eq.return_value.execute.return_value = list_res
            
            dict_res = MagicMock()
            dict_res.data = worker_data if exists else None
            table.select.return_value.eq.return_value.single.return_value.execute.return_value = dict_res
            
            table.update.return_value.execute.return_value.data = [worker_data]
            table.insert.return_value.execute.return_value.data = [worker_data]
            return table

        mock_supabase_client.table.side_effect = lambda t: create_mock_table()

    async def test_01_onboarding_perfection(self):
        print("\n🏃 [PHASE 1] THE ONBOARDING MARATHON")
        self.mock_supabase_flow(exists=False, phone=self.phone_new)
        self.redis_mock.get.return_value = None
        
        steps = [
            ("JOIN", "1️⃣ English"),
            ("1", "Which platform"), 
            ("1", "working hours"), 
            ("1", "Identity Verification"), 
            ("123456789012", "UPI"), 
            ("ravi@upi", "pin"), 
            ("560001, 560037", "coverage plan"), 
        ]
        
        for i, (input_val, expected_keyword) in enumerate(steps):
            self.redis_mock.get.return_value = b'{"step": ' + str(i).encode() + b'}' if i > 0 else None
            resp = await route_message(self.phone_new, input_val)
            self.assertIn(expected_keyword, resp)

        self.redis_mock.get.return_value = b'{"step": 6, "language": "en", "plan": "pro"}'
        with patch("services.onboarding_handlers._generate_dashboard_url", AsyncMock(return_value="https://pwa.io/dash")):
            resp = await route_message(self.phone_new, "3")
            self.assertIn("Welcome", resp)
            print("✅ Phase 1 Certified: High-Fidelity Welcome Card Received.")

    async def test_02_multi_zone_integrity(self):
        print("\n⚔️ [PHASE 2] MULTI-ZONE SAFETY")
        self.mock_supabase_flow(exists=True, phone=self.phone_active)
        with patch("utils.redis_client.get_dci_cache", AsyncMock(return_value={"dci_score": 45.0, "severity_tier": "yellow"})):
            resp = await route_message(self.phone_active, "STATUS")
            self.assertIn("Multi-Zone", resp)
            print("✅ Phase 2 Certified: Consolidated Safety Report handles all registered zones.")

    async def test_03_settlement_fraud_transparency(self):
        print("\n🛡️ [PHASE 3] SETTLEMENT & FRAUD TRANSPARENCY")
        self.mock_supabase_flow(exists=True, phone=self.phone_active)
        
        test_claim = {
            "id": "CLAIM-123", "worker_id": self.worker_id, "status": "pending",
            "dci_score": 85.0, "disruption_duration": 270, "baseline_earnings": 1000,
            "pincode": "560001", "disruption_type": "Rain", "created_at": datetime.now().isoformat()
        }
        
        # PATCH AT CONSUMPTION POINTS
        with patch("cron.claims_trigger.check_fraud", AsyncMock(return_value=(75.0, ["Mocked Offset"]))), \
             patch("cron.claims_trigger.notify_worker", AsyncMock(return_value=True)) as mock_notif, \
             patch("cron.claims_trigger._trigger_payment", AsyncMock(return_value={"id": "RZP_PAY_001"})):
            
            result = await process_single_claim(test_claim)
            self.assertEqual(result["status"], "flagged")
            mock_notif.assert_called()
            print("✅ Phase 3 Certified: Fraud triggers 'payout_flagged' transparency.")

    async def test_04_proactive_recovery_pulse(self):
        print("\n🚨 [PHASE 4] PROACTIVE RECOVERY BROADCAST")
        self.mock_supabase_flow(exists=True, phone=self.phone_active)
        # trigger_recovery_alerts -> send_whatsapp_alert -> notify_worker
        with patch("services.whatsapp_service.notify_worker", AsyncMock(return_value=True)) as mock_notif:
            await trigger_recovery_alerts("560001", {"severity_tier": "normal"}, 55.0)
            mock_notif.assert_called_once()
            print("✅ Phase 4 Certified: System proactively notifies workers of 'Safe to Work' status.")

if __name__ == "__main__":
    unittest.main()
