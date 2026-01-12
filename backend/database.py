"""
BloxPulse Database

SQLite database setup with SQLAlchemy async support.
"""

from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import settings


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# =============================================================================
# Models
# =============================================================================

class Game(Base):
    """Roblox game data."""

    __tablename__ = "games"

    id = Column(Integer, primary_key=True)  # Roblox universe ID
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    creator_name = Column(String(255), nullable=True)
    creator_id = Column(Integer, nullable=True)

    # Metrics
    playing = Column(Integer, default=0)  # Current players
    visits = Column(Integer, default=0)  # Total visits
    favorites = Column(Integer, default=0)

    # Metadata
    genre = Column(String(100), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Game {self.id}: {self.name}>"


class TrendSnapshot(Base):
    """Historical snapshot of trending games."""

    __tablename__ = "trend_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, nullable=False, index=True)

    # Metrics at snapshot time
    playing = Column(Integer, default=0)
    visits = Column(Integer, default=0)
    favorites = Column(Integer, default=0)

    # Position in charts
    trending_rank = Column(Integer, nullable=True)
    top_earning_rank = Column(Integer, nullable=True)

    # Timestamp
    snapshot_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<TrendSnapshot {self.game_id} @ {self.snapshot_at}>"


class SocialTrend(Base):
    """Social media trend data (YouTube, X/Twitter)."""

    __tablename__ = "social_trends"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Source
    platform = Column(String(50), nullable=False)  # youtube, twitter
    content_type = Column(String(50), nullable=False)  # video, tweet, hashtag

    # Content
    external_id = Column(String(255), nullable=False)  # Platform-specific ID
    title = Column(String(500), nullable=True)
    url = Column(String(500), nullable=True)

    # Metrics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)

    # Analysis
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    keywords = Column(JSON, nullable=True)  # List of extracted keywords
    related_game_ids = Column(JSON, nullable=True)  # Related Roblox games

    # Tracking
    published_at = Column(DateTime, nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SocialTrend {self.platform}: {self.title[:30]}...>"


class GamePass(Base):
    """Game pass/monetization data for games."""

    __tablename__ = "game_passes"

    id = Column(Integer, primary_key=True)  # Roblox pass ID
    game_id = Column(Integer, nullable=False, index=True)  # Universe ID

    # Pass details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Integer, nullable=True)  # Robux price, None if not for sale
    is_for_sale = Column(Boolean, default=True)

    # Categorization (for analysis)
    pass_type = Column(String(50), nullable=True)  # vip, cosmetic, power, access, etc.

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<GamePass {self.id}: {self.name} ({self.price}R$)>"


class CollectionLog(Base):
    """Log of data collection runs."""

    __tablename__ = "collection_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Collection details
    collector_name = Column(String(100), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Status
    status = Column(String(50), default="running")  # running, success, failed
    items_collected = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<CollectionLog {self.collector_name}: {self.status}>"


# =============================================================================
# Database Operations
# =============================================================================

async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
