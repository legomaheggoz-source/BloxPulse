"""
Health Check Routes

Endpoints for monitoring application health.
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_session
from config import settings


router = APIRouter(prefix="/api/v1", tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    environment: str
    database: str
    version: str = "1.0.0"


@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_session)):
    """
    Check application health.

    Returns status of the application and its dependencies.
    """
    # Check database
    db_status = "healthy"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        timestamp=datetime.utcnow(),
        environment=settings.environment,
        database=db_status,
    )


@router.get("/ping")
async def ping():
    """Simple ping endpoint for uptime monitoring."""
    return {"ping": "pong", "timestamp": datetime.utcnow().isoformat()}
