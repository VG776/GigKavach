import sys
import os
import pytest
from unittest.mock import MagicMock

# Add the backend directory to sys.path so tests can import main, api, services, etc.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def mock_supabase_for_whatsapp(monkeypatch):
    mock_sb = MagicMock()
    # By default, pretend no user exists (data=[]) so we can test "not registered" 
    # and "new user onboarding".
    mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = type('obj', (object,), {'data': []})()
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = type('obj', (object,), {'data': []})()
    mock_sb.table.return_value.insert.return_value.execute.return_value = type('obj', (object,), {'data': [{'id': 'W123'}]})()
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = type('obj', (object,), {'data': [{'id': 'W123'}]})()
    
    # Patch in onboarding_handlers
    try:
        monkeypatch.setattr("services.onboarding_handlers.get_supabase", lambda: mock_sb)
    except Exception:
        pass
