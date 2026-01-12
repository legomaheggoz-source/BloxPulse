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
    from collectors.roblox import POPULAR_GAMES

    await trigger_collection()

    return {
        "status": "collection triggered",
        "games_in_list": len(POPULAR_GAMES),
    }


# Test and run monetization collection
@app.get("/api/v1/admin/collect-monetization", tags=["Admin"])
async def collect_monetization_get():
    """Run monetization collection with detailed logging."""
    import traceback
    from sqlalchemy import select
    from database import Game, GamePass
    from collectors.monetization import MonetizationCollector, categorize_pass

    debug = {"steps": []}

    try:
        async with async_session_maker() as session:
            # Step 1: Query games
            result = await session.execute(select(Game.id))
            game_ids = [row[0] for row in result.fetchall()]
            debug["steps"].append(f"Step 1: Found {len(game_ids)} games")

            if not game_ids:
                return {"status": "no_games", "debug": debug}

            # Step 2: Fetch passes for all games
            total_passes = 0

            async with MonetizationCollector() as collector:
                for i, universe_id in enumerate(game_ids):
                    passes = await collector.get_game_passes(universe_id)
                    debug["steps"].append(f"Step 2: Game {universe_id} returned {len(passes)} passes")

                    for pass_data in passes:
                        pass_id = pass_data.get("id")
                        if not pass_id:
                            debug["steps"].append(f"  - Pass skipped: no id")
                            continue

                        # Upsert
                        existing = await session.execute(
                            select(GamePass).where(GamePass.id == pass_id)
                        )
                        game_pass = existing.scalar_one_or_none()

                        if game_pass is None:
                            game_pass = GamePass(id=pass_id)
                            session.add(game_pass)

                        game_pass.game_id = universe_id
                        game_pass.name = pass_data["name"]
                        game_pass.description = pass_data.get("description")
                        game_pass.price = pass_data.get("price")
                        game_pass.is_for_sale = pass_data.get("is_for_sale", True)
                        game_pass.pass_type = categorize_pass(
                            pass_data["name"],
                            pass_data.get("description", "")
                        )

                        total_passes += 1

            debug["steps"].append(f"Step 3: Total passes processed: {total_passes}")

            await session.commit()
            debug["steps"].append("Step 4: Committed")

            # Verify
            result = await session.execute(select(GamePass).limit(5))
            saved = result.scalars().all()
            debug["saved_passes"] = [{"id": p.id, "name": p.name} for p in saved]

            return {
                "status": "success",
                "passes_collected": total_passes,
                "debug": debug,
            }
    except Exception as e:
        debug["error"] = str(e)
        debug["traceback"] = traceback.format_exc()
        return {"status": "error", "debug": debug}


# Debug: Test single game passes API
@app.get("/api/v1/admin/debug-passes/{universe_id}", tags=["Admin"])
async def debug_game_passes(universe_id: int):
    """Debug: Fetch passes for a single game and show raw response."""
    import httpx

    url = f"https://apis.roblox.com/game-passes/v1/universes/{universe_id}/game-passes"
    params = {"passView": "Full"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)
            return {
                "status_code": response.status_code,
                "url": str(response.url),
                "raw_response": response.json() if response.status_code == 200 else response.text[:500],
                "keys": list(response.json().keys()) if response.status_code == 200 else None,
            }
        except Exception as e:
            return {"error": str(e)}


# Debug: Full monetization debug
@app.get("/api/v1/admin/debug-monetization", tags=["Admin"])
async def debug_monetization():
    """Debug: Step through monetization collection."""
    from sqlalchemy import select
    from database import Game
    from collectors.monetization import MonetizationCollector

    debug_info = {}

    async with async_session_maker() as session:
        # Step 1: Get games
        result = await session.execute(select(Game.id, Game.name))
        games = result.fetchall()
        debug_info["total_games_in_db"] = len(games)
        debug_info["first_5_games"] = [{"id": g[0], "name": g[1]} for g in games[:5]]

        if not games:
            return debug_info

        # Step 2: Test fetching passes for first game
        first_game_id = games[0][0]
        debug_info["testing_game_id"] = first_game_id

        async with MonetizationCollector() as collector:
            passes = await collector.get_game_passes(first_game_id)
            debug_info["passes_found_for_first_game"] = len(passes)
            debug_info["first_3_passes"] = passes[:3] if passes else []
            debug_info["collector_last_error"] = collector.last_error

    return debug_info


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
