import pytest
import random
from unittest.mock import MagicMock, patch
from services.onboarding_handlers import route_message

@pytest.mark.asyncio
async def test_whatsapp_routing_random_phone():
    phone = f"+9199{random.randint(10000000, 99999999)}"
    with patch("services.onboarding_handlers.get_supabase") as mock_get_sb:
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_sb.table().select().eq().execute.return_value.data = []
        
        resp = await route_message(phone, "JOIN")
        assert "language" in resp.lower() or "English" in resp
