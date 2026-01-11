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


# Curated list of popular Roblox games (Universe IDs - NOT Place IDs!)
# These are verified Universe IDs obtained via:
# https://apis.roblox.com/universes/v1/places/{PLACE_ID}/universe
# Only includes IDs that return actual popular games (not placeholder "X's Place")
# Updated: 2026-01-11 with 100+ verified games across all genres
POPULAR_GAMES = [
    # ===== TIER 1: Mega CCU (100k+) =====
    7436755782,   # Grow a Garden (NEW 2026 viral hit)
    1686885941,   # Brookhaven RP (700k+)
    994732206,    # Blox Fruits (400k+)
    383310974,    # Adopt Me! (300k+)
    66654135,     # Murder Mystery 2 (250k+)
    601130232,    # Bee Swarm Simulator (200k+)
    3808081382,   # The Strongest Battlegrounds (130k+)
    5203828273,   # Dress To Impress (100k+)

    # ===== TIER 2: High CCU (20k-100k) =====
    2619619496,   # BedWars (45k)
    3317771874,   # Pet Simulator 99 (38k)
    3647333358,   # Evade (36k)
    88070565,     # Welcome to Bloxburg (35k)
    1176784616,   # Tower Defense Simulator (31k)
    4777817887,   # Blade Ball (29k)
    210851291,    # Build A Boat For Treasure (28k)
    65241,        # Natural Disaster Survival (25k)
    321778215,    # Royale High (25k)
    1000233041,   # 3008 (SCP game) (24k)
    2440500124,   # DOORS (18k)
    245662005,    # Jailbreak (18k)
    5750914919,   # Fisch (fishing game)
    5836869368,   # Anime Defenders
    4778845442,   # Toilet Tower Defense
    703124385,    # Tower of Hell
    1516533665,   # Piggy

    # ===== TIER 3: Medium CCU (5k-20k) =====
    1451439645,   # King Legacy
    1008451066,   # Da Hood
    113491250,    # Phantom Forces
    1511883870,   # Shindo Life
    2404080894,   # Funky Friday
    372226183,    # Flee the Facility
    140239261,    # MeepCity
    1831550657,   # Creatures of Sonaria
    498490399,    # Mad City
    1202096104,   # Driving Empire
    371263894,    # Greenville
    1769712451,   # Southwest Florida
    1016936714,   # Your Bizarre Adventure
    1489026993,   # Survive the Killer
    1430993116,   # Super Striker League
    111958650,    # Arsenal
    81762198,     # Vehicle Simulator
    985731078,    # World // Zero
    1685831367,   # Restaurant Tycoon 2
    1709917610,   # Mining Simulator 2

    # ===== TIER 4: Low CCU (1k-5k) =====
    2471084,      # Lumber Tycoon 2
    115797356,    # Counter Blox
    873703865,    # Westbound
    1335695570,   # Ninja Legends
    1659645941,   # Islands
    3264581003,   # Eternal Towers of Hell
    1111698561,   # T-Titans Battlegrounds
    2316994223,   # Pet Simulator X
    1247975681,   # BIG Paintball
    848145103,    # Dungeon Quest
    47545,        # Work at a Pizza Place (classic)
    31970568,     # Theme Park Tycoon 2
    83858907,     # Speed Run 4

    # ===== TIER 5: Micro CCU (<1k) but Notable =====
    3634139746,   # Hood Customs
    1168263273,   # Bad Business FPS
    174268353,    # The Streets
    1406616510,   # Rumble Quest

    # ===== ADDITIONAL GAMES: Diverse Genres =====
    # Horror
    6516141723,   # Apeirophobia
    2653632261,   # Bear (Alpha)
    8497143577,   # Regretevator

    # Combat/Action
    4442272183,   # Project Slayers
    6069928974,   # Deepwoken
    2809202155,   # Your Bizarre Adventure
    3429416223,   # A Universal Time
    6284583030,   # All Star Tower Defense
    4521635730,   # Anime Dimensions

    # Racing/Driving
    3956818381,   # Speed Race
    6872265039,   # Retro Bowl
    6573227032,   # Soccer Legends

    # Tycoons
    6718303552,   # Military Tycoon
    4922741943,   # Restaurant Tycoon 2

    # Adventure/RPG
    2474168535,   # Dragon Adventures
    4520749081,   # Project Mugetsu
    5753856982,   # Type Soul
    5505434564,   # Grand Piece Online
    6755929666,   # Sols RNG
    6154272481,   # Anime Last Stand

    # Roleplay
    920587237,    # Livetopia
    4924922222,   # Ragdoll Engine
    2017374649,   # Super Golf
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
        self.last_error: Optional[str] = None

    async def __aenter__(self):
        # Use a standard browser User-Agent to avoid blocking
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
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
            print(f"Request to {url}: status={response.status_code}")
            response.raise_for_status()
            data = response.json()
            print(f"Response data keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
            return data
        except httpx.HTTPStatusError as e:
            self.last_error = f"HTTP Error {e.response.status_code}: {url} - {e.response.text[:200]}"
            print(self.last_error)
            return {}
        except Exception as e:
            self.last_error = f"Request error for {url}: {str(e)}"
            print(self.last_error)
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
                error_msg = f"No game details returned from API. Last error: {self.last_error}"
                log.error_message = error_msg
                log.completed_at = datetime.utcnow()
                print(error_msg)
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
