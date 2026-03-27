"""Compatibility ASGI entrypoint.

Keeps legacy startup command `uvicorn server:app` working while
main application lives in main.py.
"""

from main import app
