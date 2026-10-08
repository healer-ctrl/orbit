import sys
import os
import logging
import azure.functions as func

# Ensure backend and subdirectories are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, "backend")
parent_dir = os.path.dirname(current_dir)

for p in [current_dir, backend_dir, parent_dir]:
    if p not in sys.path and os.path.exists(p):
        sys.path.insert(0, p)

logger = logging.getLogger("orbit.functions")

try:
    from backend.main import app as fastapi_app
except ImportError:
    from main import app as fastapi_app

# Official Azure Functions Python v2 ASGI application wrapper
app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
