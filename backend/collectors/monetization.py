"""
Monetization Data Collector

Collects game pass data from Roblox API to analyze monetization strategies.
Uses the new game-passes API endpoint:
https://apis.roblox.com/game-passes/v1/universes/{universeId}/game-passes
"""

import asyncio
import re
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database import GamePass, Game, CollectionLog


# Pass type keywords for categorization
PASS_TYPE_PATTERNS = {
    "vip": r"\b(vip|premium|elite|gold|platinum|diamond)\b",
    "access": r"\b(unlock|access|open|enter|estate|land|area|zone)\b",
    "speed": r"\b(speed|fast|quick|boost)\b",
    "cosmetic": r"\b(skin|outfit|costume|theme|face|clothes|customiz)\b",
    "power": r"\b(power|strong|damage|upgrade|level|boost|super|mega|ultra)\b",
    "utility": r"\b(music|radio|fly|teleport|admin|tool)\b",
    "vehicle": r"\b(vehicle|car|boat|plane|helicopter|motorcycle|horse)\b",
    "pack": r"\b(pack|bundle|collection|set)\b",
    "pet": r"\b(pet|companion|mount)\b",
    "storage": r"\b(storage|inventory|slot|space)\b",
}


def categorize_pass(name: str, description: str = "") -> str:
    """Categorize a game pass based on its name and description."""
    text = f"{name} {description}".lower()

    for pass_type, pattern in PASS_TYPE_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return pass_type

    return "other"


class MonetizationCollector:
    """Collector for game pass/monetization data."""

    GAME_PASSES_API = "https://apis.roblox.com/game-passes/v1/universes"

    REQUEST_DELAY = 0.5  # Slightly more conservative for this API

    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.last_error: Optional[str] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            },
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def get_game_passes(self, universe_id: int) -> list[dict]:
        """Fetch all game passes for a game."""
        await asyncio.sleep(self.REQUEST_DELAY)

        url = f"{self.GAME_PASSES_API}/{universe_id}/game-passes"
        params = {"passView": "Full"}

        try:
            response = await self.client.get(url, params=params)

            if response.status_code == 404:
                # Game might not have passes or doesn't exist
                return []

            response.raise_for_status()
            data = response.json()

            passes = []
            for item in data.get("data", []):
                # Extract price - handle different formats
                price = item.get("price")
                if price is None:
                    price = item.get("PriceInRobux")

                passes.append({
                    "id": item.get("id"),
                    "name": item.get("name", "Unknown Pass"),
                    "description": item.get("description", ""),
                    "price": price,
                    "is_for_sale": item.get("isForSale", price is not None),
                })

            return passes

        except httpx.HTTPStatusError as e:
            self.last_error = f"HTTP Error {e.response.status_code} for universe {universe_id}"
            print(self.last_error)
            return []
        except Exception as e:
            self.last_error = f"Error fetching passes for {universe_id}: {str(e)}"
            print(self.last_error)
            return []

    async def collect_monetization_data(self, session: AsyncSession) -> int:
        """
        Collect game pass data for all tracked games.

        Returns number of game passes collected.
        """
        log = CollectionLog(collector_name="monetization")
        session.add(log)
        await session.flush()

        try:
            # Get all tracked games
            result = await session.execute(select(Game.id))
            game_ids = [row[0] for row in result.fetchall()]

            if not game_ids:
                log.status = "success"
                log.items_collected = 0
                log.completed_at = datetime.utcnow()
                return 0

            print(f"Fetching game passes for {len(game_ids)} games...")

            total_passes = 0

            for universe_id in game_ids:
                passes = await self.get_game_passes(universe_id)

                for pass_data in passes:
                    if not pass_data.get("id"):
                        continue

                    # Upsert game pass
                    existing = await session.execute(
                        select(GamePass).where(GamePass.id == pass_data["id"])
                    )
                    game_pass = existing.scalar_one_or_none()

                    if game_pass is None:
                        game_pass = GamePass(id=pass_data["id"])
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
                    game_pass.updated_at = datetime.utcnow()

                    total_passes += 1

            log.status = "success"
            log.items_collected = total_passes
            log.completed_at = datetime.utcnow()

            print(f"Successfully collected {total_passes} game passes")
            return total_passes

        except Exception as e:
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            print(f"Monetization collection failed: {e}")
            raise


async def run_monetization_collection(session: AsyncSession) -> int:
    """Run monetization data collection."""
    async with MonetizationCollector() as collector:
        return await collector.collect_monetization_data(session)
