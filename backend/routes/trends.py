"""
Trends Routes

Endpoints for accessing trending games data.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from database import get_session, Game, TrendSnapshot


router = APIRouter(prefix="/api/v1/trends", tags=["Trends"])


# =============================================================================
# Response Models
# =============================================================================

class GameSummary(BaseModel):
    """Summary of a game for trend display."""

    id: int
    name: str
    creator_name: Optional[str] = None
    playing: int
    visits: int
    favorites: int
    genre: Optional[str] = None
    thumbnail_url: Optional[str] = None
    trending_rank: Optional[int] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class TrendingResponse(BaseModel):
    """Response for trending games endpoint."""

    games: list[GameSummary]
    total: int
    last_updated: Optional[datetime] = None


class TrendStats(BaseModel):
    """Overall trend statistics."""

    total_games_tracked: int
    total_players_now: int
    average_players: float
    top_genre: Optional[str] = None
    data_freshness_hours: float


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=TrendingResponse)
async def get_trending_games(
    limit: int = Query(50, ge=1, le=100, description="Number of games to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get currently trending games.

    Returns games sorted by current player count (trending).
    """
    # Build query
    query = select(Game)

    if genre:
        query = query.where(Game.genre == genre)

    query = query.order_by(desc(Game.playing)).offset(offset).limit(limit)

    # Execute
    result = await session.execute(query)
    games = result.scalars().all()

    # Get total count
    count_query = select(func.count(Game.id))
    if genre:
        count_query = count_query.where(Game.genre == genre)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Get last update time
    last_update_result = await session.execute(
        select(func.max(Game.updated_at))
    )
    last_updated = last_update_result.scalar()

    # Build response with rank
    game_summaries = []
    for i, game in enumerate(games):
        summary = GameSummary(
            id=game.id,
            name=game.name,
            creator_name=game.creator_name,
            playing=game.playing,
            visits=game.visits,
            favorites=game.favorites,
            genre=game.genre,
            thumbnail_url=game.thumbnail_url,
            trending_rank=offset + i + 1,
            updated_at=game.updated_at,
        )
        game_summaries.append(summary)

    return TrendingResponse(
        games=game_summaries,
        total=total,
        last_updated=last_updated,
    )


@router.get("/stats", response_model=TrendStats)
async def get_trend_stats(
    session: AsyncSession = Depends(get_session),
):
    """
    Get overall trend statistics.

    Returns aggregated statistics about tracked games.
    """
    # Total games
    total_result = await session.execute(select(func.count(Game.id)))
    total_games = total_result.scalar() or 0

    # Total and average players
    player_result = await session.execute(
        select(
            func.sum(Game.playing),
            func.avg(Game.playing),
        )
    )
    row = player_result.one()
    total_players = row[0] or 0
    avg_players = row[1] or 0

    # Top genre
    genre_result = await session.execute(
        select(Game.genre, func.count(Game.id).label("count"))
        .where(Game.genre.isnot(None))
        .group_by(Game.genre)
        .order_by(desc("count"))
        .limit(1)
    )
    genre_row = genre_result.first()
    top_genre = genre_row[0] if genre_row else None

    # Data freshness
    freshness_result = await session.execute(
        select(func.max(Game.updated_at))
    )
    last_update = freshness_result.scalar()
    if last_update:
        freshness_hours = (datetime.utcnow() - last_update).total_seconds() / 3600
    else:
        freshness_hours = -1

    return TrendStats(
        total_games_tracked=total_games,
        total_players_now=int(total_players),
        average_players=float(avg_players),
        top_genre=top_genre,
        data_freshness_hours=round(freshness_hours, 2),
    )


@router.get("/history/{game_id}")
async def get_game_trend_history(
    game_id: int,
    hours: int = Query(24, ge=1, le=168, description="Hours of history (max 7 days)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get historical trend data for a specific game.

    Returns snapshots over the specified time period.
    """
    # Verify game exists
    game_result = await session.execute(
        select(Game).where(Game.id == game_id)
    )
    game = game_result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Get snapshots
    since = datetime.utcnow() - timedelta(hours=hours)
    snapshots_result = await session.execute(
        select(TrendSnapshot)
        .where(TrendSnapshot.game_id == game_id)
        .where(TrendSnapshot.snapshot_at >= since)
        .order_by(TrendSnapshot.snapshot_at)
    )
    snapshots = snapshots_result.scalars().all()

    return {
        "game_id": game_id,
        "game_name": game.name,
        "hours": hours,
        "snapshots": [
            {
                "timestamp": s.snapshot_at.isoformat(),
                "playing": s.playing,
                "visits": s.visits,
                "favorites": s.favorites,
                "trending_rank": s.trending_rank,
            }
            for s in snapshots
        ],
    }


@router.get("/genres")
async def get_genres(
    session: AsyncSession = Depends(get_session),
):
    """
    Get list of all genres with game counts.
    """
    result = await session.execute(
        select(Game.genre, func.count(Game.id).label("count"))
        .where(Game.genre.isnot(None))
        .group_by(Game.genre)
        .order_by(desc("count"))
    )
    genres = result.all()

    return {
        "genres": [
            {"name": genre, "count": count}
            for genre, count in genres
        ]
    }
