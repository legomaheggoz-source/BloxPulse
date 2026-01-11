"""
Roblox API Collector

Collects data from official Roblox APIs:
- Popular games (curated list + discovered)
- Game details and player counts
- Thumbnails
"""

import asyncio
from datetime import datetime
from typing import Optional
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import Game, TrendSnapshot, CollectionLog


# Curated list of popular Roblox games (Universe IDs)
# These are consistently popular games that demonstrate the tracking system
POPULAR_GAMES = [
    # Top games by concurrent players (2024-2025)
    286090429,    # Adopt Me!
    2753915549,   # Blox Fruits
    4252370517,   # Brookhaven RP
    920587237,    # Royale High
    2474168535,   # Tower of Hell
    185655149,    # Welcome to Bloxburg
    3260590327,   # Doors
    6516141723,   # Rivals
    142823291,    # Murder Mystery 2
    1224212277,   # Murder Mystery S
    2021178065,   # Ability Wars
    65241,        # Natural Disaster Survival
    189707,       # Jailbreak
    292439477,    # Phantom Forces
    1962086868,   # Tower Defense Simulator
    13822889,     # Piggy
    3956818381,   # Bee Swarm Simulator
    4520749081,   # King Legacy
    3233893879,   # A Dusty Trip
    6284583030,   # Da Hood
    4922409811,   # DOORS: Floor 2
    5036207802,   # Pet Simulator X
    3527629287,   # Anime Fighters Simulator
    455366377,    # Dragon Ball Daima: Destiny
    2414851778,   # Shindo Life
    4991295695,   # My Restaurant
    68133584,     # Meep City
    2950983942,   # Anime Adventures
    2512644273,   # OBBY BUT YOURE A BALL
    3260917757,   # Grand Piece Online
    5504587950,   # Build a Boat for Treasure
    1600503495,   # MM2 Sandbox
    2563455047,   # Sonic Speed Simulator
    3407858589,   # Blade Ball
    4872321990,   # Arm Wrestle Simulator
    6018864097,   # Fisch
    113108949,    # Work at a Pizza Place
    4763704977,   # MY HERO MANIA
    4669040,      # Theme Park Tycoon 2
    478820088,    # Creatures of Sonaria
]


class RobloxCollector:
    """Collector for Roblox official API data."""

    # API Endpoints
    GAMES_API = "https://games.roblox.com"
    THUMBNAIL_API = "https://thumbnails.roblox.com"

    # Rate limiting
    REQUEST_DELAY = 0.3  # seconds between requests

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

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP Error {e.response.status_code}: {url}")
            return {}
        except Exception as e:
            print(f"Request error: {e}")
            return {}

    async def get_game_details(self, universe_ids: list[int]) -> list[dict]:
        """Get detailed information for multiple games."""
        if not universe_ids:
            return []

        # API accepts max 100 IDs at a time
        all_games = []
        for i in range(0, len(universe_ids), 100):
            batch = universe_ids[i:i + 100]
            url = f"{self.GAMES_API}/v1/games"
            params = {"universeIds": ",".join(map(str, batch))}

            data = await self._request(url, params)
            games = data.get("data", [])
            all_games.extend(games)

        return all_games

    async def get_game_icons(self, universe_ids: list[int], size: str = "150x150") -> dict:
        """Get game thumbnail icons."""
        if not universe_ids:
            return {}

        icons = {}
        for i in range(0, len(universe_ids), 100):
            batch = universe_ids[i:i + 100]
            url = f"{self.THUMBNAIL_API}/v1/games/icons"
            params = {
                "universeIds": ",".join(map(str, batch)),
                "size": size,
                "format": "Png",
                "isCircular": "false",
            }

            data = await self._request(url, params)
            for item in data.get("data", []):
                if item.get("state") == "Completed":
                    icons[item["targetId"]] = item.get("imageUrl")

        return icons

    async def collect_trending_games(self, session: AsyncSession) -> int:
        """
        Collect game data and save to database.

        Returns number of games collected.
        """
        log = CollectionLog(collector_name="roblox_trending")
        session.add(log)
        await session.flush()

        try:
            # Use curated list of popular games
            universe_ids = POPULAR_GAMES.copy()

            # Get detailed information
            print(f"Fetching details for {len(universe_ids)} games...")
            details = await self.get_game_details(universe_ids)

            if not details:
                log.status = "failed"
                log.error_message = "No game details returned from API"
                log.completed_at = datetime.utcnow()
                return 0

            # Get thumbnails
            print(f"Fetching thumbnails...")
            icons = await self.get_game_icons(universe_ids)

            # Sort by current players (descending) to determine rank
            details_sorted = sorted(details, key=lambda x: x.get("playing", 0), reverse=True)

            # Process and save games
            count = 0
            snapshot_time = datetime.utcnow()

            for rank, detail in enumerate(details_sorted, 1):
                universe_id = detail.get("id")
                if not universe_id:
                    continue

                # Upsert game record
                existing = await session.execute(
                    select(Game).where(Game.id == universe_id)
                )
                game = existing.scalar_one_or_none()

                if game is None:
                    game = Game(id=universe_id)
                    session.add(game)

                # Update game data
                game.name = detail.get("name", "Unknown")
                game.description = detail.get("description", "")[:2000] if detail.get("description") else None

                creator = detail.get("creator", {})
                game.creator_name = creator.get("name")
                game.creator_id = creator.get("id")

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
                    trending_rank=rank,
                    snapshot_at=snapshot_time,
                )
                session.add(snapshot)

                count += 1

            log.status = "success"
            log.items_collected = count
            log.completed_at = datetime.utcnow()

            print(f"Successfully collected {count} games")
            return count

        except Exception as e:
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            print(f"Collection failed: {e}")
            raise


async def run_collection(session: AsyncSession) -> dict:
    """Run a full data collection cycle."""
    results = {}

    async with RobloxCollector() as collector:
        results["roblox_games"] = await collector.collect_trending_games(session)

    return results
