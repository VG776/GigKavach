import os
import sys

# Add backend to path
BACKEND_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_ROOT)

from services.premium_service import load_ai_model

print(f"Calling load_ai_model...")
result = load_ai_model()
print(f"Result type: {type(result)}")
print(f"Result: {result}")
