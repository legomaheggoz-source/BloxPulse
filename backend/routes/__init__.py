"""
BloxPulse API Routes

FastAPI route modules.
"""

from .health import router as health_router
from .trends import router as trends_router
from .games import router as games_router

__all__ = ["health_router", "trends_router", "games_router"]
