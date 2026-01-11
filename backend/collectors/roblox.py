"""
Roblox API Collector

Collects data from official Roblox APIs:
- Trending games
- Top earning games
- Game details
- Player counts
"""

import asyncio
from datetime import datetime
from typing import Optional
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import Game, TrendSnapshot, CollectionLog


class RobloxCollector:
    """Collector for Roblox official API data."""

    # API Endpoints
    BASE_URL = "https://games.roblox.com"
    CATALOG_URL = "https://catalog.roblox.com"
    THUMBNAIL_URL = "https://thumbnails.roblox.com"

    # Rate limiting
    REQUEST_DELAY = 0.5  # seconds between requests

    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "BloxPulse/1.0 (Market Research Tool)",
                "Accept": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _request(self, url: str, params: dict = None) -> dict:
        """Make a rate-limited request to the Roblox API."""
        await asyncio.sleep(self.REQUEST_DELAY)

        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_games_list(
        self,
        sort_token: str = "HomeSorts",
        genre_token: str = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get list of games from Roblox discovery API.

        Sort tokens:
        - HomeSorts: Default home page sorts
        - MostEngaging: Most engaging games
        - TopEarning: Top earning games
        - TopRated: Highest rated games
        """
        url = f"{self.BASE_URL}/v1/games/list"
        params = {
            "sortToken": sort_token,
            "limit": limit,
        }
        if genre_token:
            params["genreToken"] = genre_token

        try:
            data = await self._request(url, params)
            return data.get("games", [])
        except httpx.HTTPStatusError as e:
            print(f"Error fetching games list: {e}")
            return []

    async def get_game_details(self, universe_ids: list[int]) -> list[dict]:
        """Get detailed information for multiple games."""
        if not universe_ids:
            return []

        url = f"{self.BASE_URL}/v1/games"
        params = {"universeIds": ",".join(map(str, universe_ids[:100]))}  # Max 100

        try:
            data = await self._request(url, params)
            return data.get("data", [])
        except httpx.HTTPStatusError as e:
            print(f"Error fetching game details: {e}")
            return []

    async def get_game_icons(self, universe_ids: list[int], size: str = "150x150") -> dict:
        """Get game thumbnail icons."""
        if not universe_ids:
            return {}

        url = f"{self.THUMBNAIL_URL}/v1/games/icons"
        params = {
            "universeIds": ",".join(map(str, universe_ids[:100])),
            "size": size,
            "format": "Png",
            "isCircular": "false",
        }

        try:
            data = await self._request(url, params)
            return {
                item["targetId"]: item.get("imageUrl")
                for item in data.get("data", [])
                if item.get("state") == "Completed"
            }
        except httpx.HTTPStatusError as e:
            print(f"Error fetching game icons: {e}")
            return {}

    async def collect_trending_games(self, session: AsyncSession) -> int:
        """
        Collect trending games and save to database.

        Returns number of games collected.
        """
        log = CollectionLog(collector_name="roblox_trending")
        session.add(log)
        await session.flush()

        try:
            # Get trending/popular games from multiple sources
            games_data = []

            # Most engaging games
            engaging = await self.get_games_list(sort_token="MostEngaging", limit=50)
            for i, game in enumerate(engaging):
                game["_trending_rank"] = i + 1
            games_data.extend(engaging)

            # Get unique universe IDs
            universe_ids = list({g.get("universeId") for g in games_data if g.get("universeId")})

            if not universe_ids:
                log.status = "failed"
                log.error_message = "No games found"
                log.completed_at = datetime.utcnow()
                return 0

            # Get detailed information
            details = await self.get_game_details(universe_ids)
            details_map = {d["id"]: d for d in details}

            # Get thumbnails
            icons = await self.get_game_icons(universe_ids)

            # Process and save games
            count = 0
            snapshot_time = datetime.utcnow()

            for game_data in games_data:
                universe_id = game_data.get("universeId")
                if not universe_id:
                    continue

                detail = details_map.get(universe_id, {})

                # Upsert game record
                existing = await session.execute(
                    select(Game).where(Game.id == universe_id)
                )
                game = existing.scalar_one_or_none()

                if game is None:
                    game = Game(id=universe_id)
                    session.add(game)

                # Update game data
                game.name = detail.get("name") or game_data.get("name", "Unknown")
                game.description = detail.get("description", "")
                game.creator_name = detail.get("creator", {}).get("name")
                game.creator_id = detail.get("creator", {}).get("id")
                game.playing = detail.get("playing", 0)
                game.visits = detail.get("visits", 0)
                game.favorites = detail.get("favoritedCount", 0)
                game.genre = detail.get("genre")
                game.thumbnail_url = icons.get(universe_id)
                game.updated_at = datetime.utcnow()

                # Create trend snapshot
                snapshot = TrendSnapshot(
                    game_id=universe_id,
                    playing=game.playing,
                    visits=game.visits,
                    favorites=game.favorites,
                    trending_rank=game_data.get("_trending_rank"),
                    snapshot_at=snapshot_time,
                )
                session.add(snapshot)

                count += 1

            log.status = "success"
            log.items_collected = count
            log.completed_at = datetime.utcnow()

            return count

        except Exception as e:
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            raise


async def run_collection(session: AsyncSession) -> dict:
    """Run a full data collection cycle."""
    results = {}

    async with RobloxCollector() as collector:
        results["roblox_games"] = await collector.collect_trending_games(session)

    return results
