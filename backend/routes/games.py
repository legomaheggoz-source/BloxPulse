"""
Games Routes

Endpoints for accessing individual game data.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_session, Game, TrendSnapshot


router = APIRouter(prefix="/api/v1/games", tags=["Games"])


# =============================================================================
# Response Models
# =============================================================================

class GameDetail(BaseModel):
    """Detailed game information."""

    id: int
    name: str
    description: Optional[str] = None
    creator_name: Optional[str] = None
    creator_id: Optional[int] = None
    playing: int
    visits: int
    favorites: int
    genre: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Calculated fields
    roblox_url: str

    class Config:
        from_attributes = True


class GameSearchResult(BaseModel):
    """Search result item."""

    id: int
    name: str
    playing: int
    thumbnail_url: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/{game_id}", response_model=GameDetail)
async def get_game(
    game_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Get detailed information for a specific game.
    """
    result = await session.execute(
        select(Game).where(Game.id == game_id)
    )
    game = result.scalar_one_or_none()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return GameDetail(
        id=game.id,
        name=game.name,
        description=game.description,
        creator_name=game.creator_name,
        creator_id=game.creator_id,
        playing=game.playing,
        visits=game.visits,
        favorites=game.favorites,
        genre=game.genre,
        thumbnail_url=game.thumbnail_url,
        created_at=game.created_at,
        updated_at=game.updated_at,
        roblox_url=f"https://www.roblox.com/games/{game.id}",
    )


@router.get("", response_model=list[GameSearchResult])
async def search_games(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    """
    Search for games by name.
    """
    result = await session.execute(
        select(Game)
        .where(Game.name.ilike(f"%{q}%"))
        .order_by(Game.playing.desc())
        .limit(limit)
    )
    games = result.scalars().all()

    return [
        GameSearchResult(
            id=game.id,
            name=game.name,
            playing=game.playing,
            thumbnail_url=game.thumbnail_url,
        )
        for game in games
    ]


@router.get("/{game_id}/similar")
async def get_similar_games(
    game_id: int,
    limit: int = Query(10, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
):
    """
    Get games similar to the specified game.

    Similarity is based on genre and player count range.
    """
    # Get the target game
    result = await session.execute(
        select(Game).where(Game.id == game_id)
    )
    game = result.scalar_one_or_none()

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Find similar games (same genre, exclude self)
    query = select(Game).where(Game.id != game_id)

    if game.genre:
        query = query.where(Game.genre == game.genre)

    query = query.order_by(Game.playing.desc()).limit(limit)

    result = await session.execute(query)
    similar = result.scalars().all()

    return {
        "game_id": game_id,
        "game_name": game.name,
        "similar": [
            {
                "id": g.id,
                "name": g.name,
                "playing": g.playing,
                "thumbnail_url": g.thumbnail_url,
            }
            for g in similar
        ],
    }
