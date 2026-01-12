"""
BloxPulse API

Main FastAPI application entry point.
Serves both the API and the static frontend.
"""

import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from database import init_db, async_session_maker
from routes import health_router, trends_router, games_router
from routes.export import router as export_router
from routes.monetization import router as monetization_router
from services.scheduler import setup_scheduler, trigger_collection
from services.data_sync import data_sync_service


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Frontend dist path
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting BloxPulse API...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Restore data from HuggingFace backup (if available)
    if data_sync_service.is_configured:
        restored = await data_sync_service.restore_from_backup()
        logger.info(f"Restored {restored} games from HuggingFace backup")

    # Setup and start scheduler
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started")

    # Run initial data collection if database is empty
    async with async_session_maker() as session:
        from sqlalchemy import select, func
        from database import Game
        result = await session.execute(select(func.count(Game.id)))
        count = result.scalar() or 0
        if count == 0:
            logger.info("Database empty, running initial data collection...")
            await trigger_collection()

    yield

    # Shutdown
    logger.info("Shutting down BloxPulse API...")
    scheduler.shutdown()

    # Sync data to HuggingFace before shutdown
    if data_sync_service.is_configured:
        await data_sync_service.upload_to_huggingface()
        logger.info("Data synced to HuggingFace")


# Create FastAPI app
app = FastAPI(
    title="BloxPulse API",
    description="Roblox Market Intelligence Engine - Track trends, analyze games, generate concepts.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers
app.include_router(health_router)
app.include_router(trends_router)
app.include_router(games_router)
app.include_router(export_router)
app.include_router(monetization_router)


# API root endpoint
@app.get("/api")
async def api_root():
    """API information endpoint."""
    return {
        "name": "BloxPulse API",
        "version": "1.0.0",
        "description": "Roblox Market Intelligence Engine",
        "docs": "/api/docs",
        "health": "/api/v1/health",
    }


# Manual collection trigger (for testing)
@app.post("/api/v1/admin/collect", tags=["Admin"])
async def manual_collect():
    """Manually trigger data collection (for testing)."""
    await trigger_collection()
    return {"status": "collection triggered"}


# GET version for easy browser testing
@app.get("/api/v1/admin/collect", tags=["Admin"])
async def manual_collect_get():
    """Manually trigger data collection (GET version for browser testing)."""
    import traceback
    from collectors.roblox import POPULAR_GAMES, run_collection
    from database import async_session_maker, Game
    from sqlalchemy import select, func

    try:
        async with async_session_maker() as session:
            # Check current count
            result = await session.execute(select(func.count(Game.id)))
            before_count = result.scalar() or 0

            # Run collection
            results = await run_collection(session)
            await session.commit()

            # Check new count
            result = await session.execute(select(func.count(Game.id)))
            after_count = result.scalar() or 0

            return {
                "status": "success",
                "games_in_list": len(POPULAR_GAMES),
                "games_before": before_count,
                "games_after": after_count,
                "collection_result": results,
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


# Refresh endpoint - triggers collection and returns status
@app.post("/api/v1/admin/refresh", tags=["Admin"])
async def refresh_data():
    """
    Refresh game data from Roblox API.

    This uses the current game list and fetches the latest CCU/stats.
    For discovering NEW games, use the GitHub Actions workflow.
    """
    from collectors.roblox import POPULAR_GAMES

    await trigger_collection()

    return {
        "status": "success",
        "message": "Data refresh triggered",
        "games_in_list": len(POPULAR_GAMES),
        "note": "New game discovery runs weekly via GitHub Actions"
    }


# Manual sync trigger
@app.post("/api/v1/admin/sync", tags=["Admin"])
async def manual_sync():
    """Manually trigger HuggingFace sync."""
    success = await data_sync_service.upload_to_huggingface()
    return {"status": "success" if success else "failed"}


# =============================================================================
# Static Frontend Serving
# =============================================================================

# Mount static files if frontend is built
if FRONTEND_DIR.exists():
    # Serve static assets
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    # Serve index.html for all non-API routes (SPA support)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA frontend for all non-API routes."""
        # Check if it's a static file
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        # Otherwise serve index.html
        return FileResponse(FRONTEND_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        """Root endpoint when frontend is not built."""
        return {
            "message": "BloxPulse API is running",
            "frontend": "Not built - run 'npm run build' in frontend/",
            "api_docs": "/api/docs",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
    )
