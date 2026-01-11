"""
Data Sync Service

Handles synchronization of data to HuggingFace Datasets for persistence.
This solves the HuggingFace Spaces free tier limitation of no persistent storage.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from huggingface_hub import HfApi, hf_hub_download, upload_file
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from database import Game, TrendSnapshot, async_session_maker


logger = logging.getLogger(__name__)


class DataSyncService:
    """
    Service for syncing data to HuggingFace Dataset.

    This enables data persistence on the free tier by:
    1. Exporting SQLite data to JSON
    2. Uploading to a HuggingFace Dataset repo
    3. Loading from Dataset on startup
    """

    def __init__(self):
        self.api = HfApi(token=settings.hf_token) if settings.hf_token else None
        self.dataset_repo = f"{settings.hf_dataset_name}"
        self.data_file = "bloxpulse_data.json"

    @property
    def is_configured(self) -> bool:
        """Check if HuggingFace sync is configured."""
        return bool(settings.hf_token and settings.hf_dataset_name)

    async def export_to_json(self, session: AsyncSession) -> dict:
        """Export database to JSON format."""
        # Export games
        games_result = await session.execute(select(Game))
        games = games_result.scalars().all()

        games_data = [
            {
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "creator_name": g.creator_name,
                "creator_id": g.creator_id,
                "playing": g.playing,
                "visits": g.visits,
                "favorites": g.favorites,
                "genre": g.genre,
                "thumbnail_url": g.thumbnail_url,
                "created_at": g.created_at.isoformat() if g.created_at else None,
                "updated_at": g.updated_at.isoformat() if g.updated_at else None,
            }
            for g in games
        ]

        # Export recent snapshots (last 7 days worth)
        snapshots_result = await session.execute(
            select(TrendSnapshot)
            .order_by(TrendSnapshot.snapshot_at.desc())
            .limit(10000)  # Limit to prevent huge exports
        )
        snapshots = snapshots_result.scalars().all()

        snapshots_data = [
            {
                "id": s.id,
                "game_id": s.game_id,
                "playing": s.playing,
                "visits": s.visits,
                "favorites": s.favorites,
                "trending_rank": s.trending_rank,
                "snapshot_at": s.snapshot_at.isoformat() if s.snapshot_at else None,
            }
            for s in snapshots
        ]

        return {
            "exported_at": datetime.utcnow().isoformat(),
            "games": games_data,
            "snapshots": snapshots_data,
        }

    async def upload_to_huggingface(self) -> bool:
        """
        Export and upload data to HuggingFace Dataset.

        Returns True if successful.
        """
        if not self.is_configured:
            logger.warning("HuggingFace sync not configured, skipping upload")
            return False

        try:
            async with async_session_maker() as session:
                data = await self.export_to_json(session)

            # Write to temp file
            temp_path = Path("/tmp/bloxpulse_export.json")
            temp_path.write_text(json.dumps(data, indent=2))

            # Upload to HuggingFace
            self.api.upload_file(
                path_or_fileobj=str(temp_path),
                path_in_repo=self.data_file,
                repo_id=self.dataset_repo,
                repo_type="dataset",
            )

            logger.info(f"Data uploaded to HuggingFace: {len(data['games'])} games")
            return True

        except Exception as e:
            logger.error(f"Failed to upload to HuggingFace: {e}")
            return False

    async def load_from_huggingface(self) -> Optional[dict]:
        """
        Download and load data from HuggingFace Dataset.

        Returns the loaded data or None if failed.
        """
        if not self.is_configured:
            logger.warning("HuggingFace sync not configured, skipping load")
            return None

        try:
            # Download file
            file_path = hf_hub_download(
                repo_id=self.dataset_repo,
                filename=self.data_file,
                repo_type="dataset",
                token=settings.hf_token,
            )

            with open(file_path, "r") as f:
                data = json.load(f)

            logger.info(f"Data loaded from HuggingFace: {len(data.get('games', []))} games")
            return data

        except Exception as e:
            logger.warning(f"Failed to load from HuggingFace (may be first run): {e}")
            return None

    async def restore_from_backup(self) -> int:
        """
        Restore database from HuggingFace Dataset backup.

        Returns number of games restored.
        """
        data = await self.load_from_huggingface()
        if not data:
            return 0

        async with async_session_maker() as session:
            count = 0

            # Restore games
            for game_data in data.get("games", []):
                existing = await session.execute(
                    select(Game).where(Game.id == game_data["id"])
                )
                if existing.scalar_one_or_none():
                    continue  # Skip if already exists

                game = Game(
                    id=game_data["id"],
                    name=game_data["name"],
                    description=game_data.get("description"),
                    creator_name=game_data.get("creator_name"),
                    creator_id=game_data.get("creator_id"),
                    playing=game_data.get("playing", 0),
                    visits=game_data.get("visits", 0),
                    favorites=game_data.get("favorites", 0),
                    genre=game_data.get("genre"),
                    thumbnail_url=game_data.get("thumbnail_url"),
                )

                if game_data.get("created_at"):
                    game.created_at = datetime.fromisoformat(game_data["created_at"])
                if game_data.get("updated_at"):
                    game.updated_at = datetime.fromisoformat(game_data["updated_at"])

                session.add(game)
                count += 1

            await session.commit()
            logger.info(f"Restored {count} games from backup")
            return count


# Global service instance
data_sync_service = DataSyncService()
