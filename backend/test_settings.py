import os
import sys
from pathlib import Path

# Add backend to path
BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))

# Force reload settings
from config.settings import settings

print(f"PROJECT_ROOT in settings: {settings.PROJECT_ROOT if hasattr(settings, 'PROJECT_ROOT') else 'N/A'}")
print(f"SUPABASE_URL in settings: '{settings.SUPABASE_URL}'")
print(f"SUPABASE_SERVICE_ROLE_KEY length: {len(settings.SUPABASE_SERVICE_ROLE_KEY) if settings.SUPABASE_SERVICE_ROLE_KEY else 0}")
