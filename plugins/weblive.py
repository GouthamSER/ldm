# plugins/weblive.py

import threading
import uvicorn
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

# --- Configuration (Must match bot.py or be passed in) ---
# NOTE: We'll assume HEALTH_PORT is passed or configured centrally.
# For simplicity, we'll use a default that can be overridden by bot.py
DEFAULT_HEALTH_PORT = 8000

# --- Starlette Setup ---

async def health_endpoint(request):
    """Simple Starlette endpoint for the health check."""
    return PlainTextResponse("OK")

# Starlette routes
routes = [
    Route("/health", endpoint=health_endpoint)
]

# Starlette application
health_app = Starlette(routes=routes)

# --- Uvicorn Starter Function ---

def run_web_server(port=DEFAULT_HEALTH_PORT):
    """
    Function to run uvicorn in a blocking manner.
    Should be run in a separate thread.
    """
    try:
        uvicorn.run(
            health_app,
            host="0.0.0.0",
            port=port,
            log_level="error"  # Keep uvicorn output quiet
        )
    except Exception as e:
        print(f"❌ Uvicorn web server failed to start on port {port}: {e}")

# --- Threading Function ---

def start_web_server_thread(port):
    """Starts the Uvicorn server in a daemon thread."""
    
    # Start the Uvicorn/Starlette health check in a separate thread
    web_thread = threading.Thread(target=run_web_server, args=(port,), daemon=True)
    web_thread.start()
    print(f"🌐 Health check running on port {port} (Uvicorn/Starlette)\n")
    return web_thread
