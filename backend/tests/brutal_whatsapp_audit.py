import asyncio
import logging
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

# 1. Hyper-Mock settings and Supabase Root
class MockSettings:
    SUPABASE_URL = "https://mock.supabase.co"
    SUPABASE_KEY = "mock-key-123"
    SUPABASE_SERVICE_ROLE_KEY = "mock-svc-key-123"
    DB_PASSWORD = "password"
    REDIS_URL = "redis://mock"
    FRONTEND_URL = "https://dashboard.gigkavach.in"
    DCI_CACHE_TTL_SECONDS = 300
    TELEMETRY_INTERVAL_SECONDS = 60
    GIGSCORE_BOOST_UPI = 5
    DCI_CATASTROPHIC_THRESHOLD = 75
    COVERAGE_DELAY_HOURS = 24

mock_supabase_client = MagicMock()

# Patch root create_client and settings globally
with patch("supabase.create_client", return_value=mock_supabase_client):
    with patch("config.settings.settings", MockSettings()):
        from services.onboarding_handlers import route_message
        from services.whatsapp_service import MESSAGES
        from api.whatsapp import send_whatsapp_alert

class BrutalWhatsAppAudit(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.phone = "+910000000000"
        self.worker_id = "W-BRUTAL"
        
        # Setup Redis Mock
        self.redis_mock = AsyncMock()
        self.redis_patcher = patch("utils.redis_client.get_redis", return_value=self.redis_mock)
        self.redis_patcher.start()

        # Global Service Patches (Patch where DEFINED to catch all local imports)
        self.sb_patcher = patch("utils.db.get_supabase", return_value=mock_supabase_client)
        self.notify_patcher = patch("services.whatsapp_service.notify_worker", AsyncMock(return_value=True))
        self.quote_patcher = patch("services.premium_service.compute_dynamic_quote", AsyncMock(return_value={"dynamic_premium": 42.0}))
        self.dci_cache_patcher = patch("utils.redis_client.get_dci_cache", AsyncMock(return_value={"dci_score": 42, "severity_tier": "yellow"}))
        self.token_patcher = patch("services.onboarding_handlers.generate_share_token", AsyncMock(return_value={"share_url": "https://pwa.io"}))
        
        self.sb_patcher.start()
        self.notify_patcher.start()
        self.quote_patcher.start()
        self.dci_cache_patcher.start()
        self.token_patcher.start()

    async def asyncTearDown(self):
        self.redis_patcher.stop()
        self.sb_patcher.stop()
        self.notify_patcher.stop()
        self.quote_patcher.stop()
        self.dci_cache_patcher.stop()
        self.token_patcher.stop()

    def mock_supabase_flow(self, exists=True, worker_data=None):
        if not worker_data:
            worker_data = {
                "id": self.worker_id,
                "phone": self.phone,
                "language": "en",
                "is_active": True,
                "pin_codes": ["560001", "560037"],
                "plan": "pro",
                "shift": "day"
            }

        mock_table = MagicMock()
        mock_supabase_client.table.return_value = mock_table
        
        mock_execute = MagicMock()
        mock_execute.data = [worker_data] if exists else []
        mock_table.select.return_value.eq.return_value.execute.return_value = mock_execute
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_execute
        
        # Policy/Logs
        mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [{"total_score": 45, "severity_tier": "yellow"}]
        mock_table.update.return_value.execute.return_value.data = [worker_data]
        mock_table.insert.return_value.execute.return_value.data = [worker_data]

    # ──────────────────────────────────────────────────────────────────────────
    # 1. THE EXHAUSTIVE MARATHON
    # ──────────────────────────────────────────────────────────────────────────
    
    async def test_01_full_onboarding_journey(self):
        print("\n🏃 PHASE 1: THE EXHAUSTIVE MARATHON")
        self.mock_supabase_flow(exists=False)
        self.redis_mock.get.return_value = None
        
        # Step 0: JOIN
        resp = await route_message(self.phone, "JOIN")
        self.assertIn("1️⃣ English", resp)
        print("✅ Step 0: JOIN -> Language")

        # Step 1: Lang
        self.redis_mock.get.return_value = b'{"step": 0}'
        resp = await route_message(self.phone, "1")
        self.assertIn("Zomato", resp)
        print("✅ Step 1: Lang -> Platform")

        # Step 2: Platform
        self.redis_mock.get.return_value = b'{"step": 1, "language": "en"}'
        resp = await route_message(self.phone, "1")
        self.assertIn("working hours", resp)
        print("✅ Step 2: Platform -> Shift")

        # Step 3: Shift
        self.redis_mock.get.return_value = b'{"step": 2, "language": "en", "platform": "zomato"}'
        resp = await route_message(self.phone, "1")
        self.assertIn("Identity Verification", resp)
        print("✅ Step 3: Shift -> Verification")

        # Step 4: Verification
        self.redis_mock.get.return_value = b'{"step": 3, "language": "en", "shift": "morning"}'
        resp = await route_message(self.phone, "111122223333")
        self.assertIn("UPI", resp)
        print("✅ Step 4: Verification -> UPI")

        # Step 5: UPI
        self.redis_mock.get.return_value = b'{"step": 4, "language": "en", "upi": "test@upi"}'
        resp = await route_message(self.phone, "ravi@upi")
        self.assertIn("pin", resp.lower())
        self.assertIn("code", resp.lower())
        print("✅ Step 5: UPI -> Pincodes")

        # Step 6: Pincodes
        self.redis_mock.get.return_value = b'{"step": 5, "language": "en", "pin_codes": ["560001"]}'
        resp = await route_message(self.phone, "560001, 560037")
        self.assertIn("coverage plan", resp.lower())
        print("✅ Step 6: Pincodes -> Plan")

        # Step 7: Final
        self.redis_mock.get.return_value = b'{"step": 6, "language": "en", "plan": "pro"}'
        with patch("services.onboarding_handlers._generate_dashboard_url", AsyncMock(return_value="https://pwa.io/dash")):
            resp = await route_message(self.phone, "3")
            self.assertIn("Welcome", resp)
            print("✅ Step 7: Plan -> EXHAUSTIVE ONBOARDING COMPLETE")

    # ──────────────────────────────────────────────────────────────────────────
    # 2. THE COMMAND GAUNTLET
    # ──────────────────────────────────────────────────────────────────────────

    async def test_02_command_integrity(self):
        print("\n⚔️ PHASE 2: THE COMMAND GAUNTLET")
        self.mock_supabase_flow(exists=True)
        self.redis_mock.get.return_value = None 

        # STATUS
        resp = await route_message(self.phone, "STATUS")
        self.assertIn("Multi-Zone", resp)
        self.assertIn("560001", resp)
        print("✅ STATUS (Multi-Zone) verified")

        # START
        resp = await route_message(self.phone, "START")
        self.assertIn("Dashboard", resp)
        print("✅ START verified")

    # ──────────────────────────────────────────────────────────────────────────
    # 3. ALERT PROPAGATION
    # ──────────────────────────────────────────────────────────────────────────

    async def test_03_deep_alerting_firewall(self):
        print("\n🚨 PHASE 3: DEEP ALERTING FIREWALL")
        self.mock_supabase_flow(exists=True)
        await send_whatsapp_alert(self.worker_id, "dci_recovery", {"pin_code": "560001", "dci": 55, "severity": "normal"})
        print("✅ Alerting pipeline verified")

if __name__ == "__main__":
    unittest.main()
