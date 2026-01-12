"""
Zetta Export Routes

Provides structured data exports for integration with the Zetta game creator.
Exports follow a versioned JSON schema for forward compatibility.
"""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from database import get_session, Game, TrendSnapshot, GamePass


router = APIRouter(prefix="/api/v1/export", tags=["Export"])


# =============================================================================
# Schema Version
# =============================================================================

SCHEMA_VERSION = "1.1.0"  # Added monetization data


# =============================================================================
# Export Models (Zetta-compatible JSON Schema)
# =============================================================================

class GameMetrics(BaseModel):
    """Core metrics for a game."""
    current_players: int = Field(description="Current concurrent users")
    total_visits: int = Field(description="All-time total visits")
    favorites: int = Field(description="Number of favorites")
    visits_per_player_ratio: float = Field(description="Visits/current_players - indicates game stickiness")
    favorites_per_visit_ratio: float = Field(description="Favorites/visits - indicates player loyalty")


class GameAnalysis(BaseModel):
    """Analyzed data for a single game."""
    universe_id: int
    name: str
    creator: Optional[str]
    genre: Optional[str]

    # Core metrics
    metrics: GameMetrics

    # Derived scores (0-100 scale)
    popularity_score: float = Field(description="Based on CCU rank among tracked games")
    engagement_score: float = Field(description="Based on visits/player and favorites ratios")

    # Classification
    tier: str = Field(description="mega (100k+), high (20k-100k), mid (5k-20k), low (1k-5k), micro (<1k)")

    # Timestamps
    last_updated: datetime


class GenreAnalysis(BaseModel):
    """Analysis of a genre/category."""
    name: str
    game_count: int
    total_ccu: int
    avg_ccu_per_game: float
    market_share_percent: float = Field(description="% of total tracked CCU")
    saturation_level: str = Field(description="high, medium, low - based on game count vs CCU")
    top_games: List[str] = Field(description="Top 3 games in this genre")


class MarketOpportunity(BaseModel):
    """Identified market opportunity."""
    opportunity_type: str = Field(description="underserved_genre, emerging_trend, gap_analysis")
    description: str
    confidence: float = Field(ge=0, le=1, description="Confidence score 0-1")
    supporting_data: dict
    recommended_action: str


class MonetizationStrategy(BaseModel):
    """Monetization strategy insights for a game or genre."""
    pass_count: int = Field(description="Number of game passes")
    price_range: List[int] = Field(description="[min, max] price in Robux")
    avg_price: float = Field(description="Average pass price in Robux")
    total_potential_spend: int = Field(description="Sum of all pass prices")
    pass_type_breakdown: dict = Field(description="Distribution of pass types")
    pricing_tier: str = Field(description="budget, standard, premium, whale-focused")


class GameMonetizationAnalysis(BaseModel):
    """Monetization analysis for a specific game."""
    game_id: int
    game_name: str
    strategy: Optional[MonetizationStrategy]
    passes: List[dict] = Field(description="List of game passes with details")


class MonetizationPatterns(BaseModel):
    """Overall monetization patterns across all games."""
    total_passes_tracked: int
    games_with_passes: int
    avg_passes_per_game: float
    overall_avg_price: float
    price_tier_distribution: dict = Field(description="Distribution across price tiers")
    pass_type_popularity: List[dict] = Field(description="Most common pass types")
    genre_monetization: List[dict] = Field(description="Avg price by genre")
    top_strategies: List[str] = Field(description="Most successful monetization approaches")


class ZettaExport(BaseModel):
    """
    Complete export schema for Zetta game creator integration.

    This schema is versioned and designed for forward compatibility.
    Zetta should check schema_version and handle accordingly.
    """
    # Metadata
    schema_version: str = Field(default=SCHEMA_VERSION)
    export_timestamp: datetime
    data_freshness_hours: float

    # Summary statistics
    summary: dict = Field(description="High-level market summary")

    # Detailed data
    games: List[GameAnalysis]
    genres: List[GenreAnalysis]

    # Monetization insights
    monetization: Optional[MonetizationPatterns] = Field(description="Overall monetization patterns")
    game_monetization: List[GameMonetizationAnalysis] = Field(default=[], description="Per-game monetization details")

    # Actionable insights
    opportunities: List[MarketOpportunity]

    # Recommendations for game development
    recommendations: dict


# =============================================================================
# Helper Functions
# =============================================================================

def calculate_tier(playing: int) -> str:
    """Classify game into player count tier."""
    if playing >= 100000:
        return "mega"
    elif playing >= 20000:
        return "high"
    elif playing >= 5000:
        return "mid"
    elif playing >= 1000:
        return "low"
    else:
        return "micro"


def calculate_popularity_score(rank: int, total: int) -> float:
    """Calculate popularity score (0-100) based on rank."""
    if total == 0:
        return 0
    return max(0, 100 - (rank / total) * 100)


def calculate_engagement_score(visits: int, playing: int, favorites: int) -> float:
    """
    Calculate engagement score (0-100) based on multiple factors.

    Factors:
    - Visits/player ratio (stickiness)
    - Favorites/visits ratio (loyalty)
    """
    if playing == 0 or visits == 0:
        return 0

    # Visits per player (higher = more sessions per concurrent user)
    # Typical range: 1000-100000
    visits_ratio = min(visits / max(playing, 1), 100000) / 100000

    # Favorites per visit (higher = more loyal players)
    # Typical range: 0.001-0.01
    favorites_ratio = min(favorites / max(visits, 1), 0.01) / 0.01

    # Weighted combination
    return round((visits_ratio * 40 + favorites_ratio * 60) * 100, 2)


def calculate_saturation(game_count: int, avg_ccu: float) -> str:
    """Determine genre saturation level."""
    if game_count > 5 and avg_ccu < 10000:
        return "high"  # Many games, low average = saturated
    elif game_count < 3 and avg_ccu > 50000:
        return "low"   # Few games, high average = opportunity
    else:
        return "medium"


def determine_pricing_tier(avg_price: float) -> str:
    """Determine the pricing tier based on average pass price."""
    if avg_price < 100:
        return "budget"
    elif avg_price < 300:
        return "standard"
    elif avg_price < 600:
        return "premium"
    else:
        return "whale-focused"


def identify_opportunities(games: list, genres: list, total_ccu: int) -> List[MarketOpportunity]:
    """Identify market opportunities from the data."""
    opportunities = []

    # Find underserved genres (low game count, high avg CCU)
    for genre in genres:
        if genre["count"] <= 2 and genre["avg_ccu"] > 30000:
            opportunities.append(MarketOpportunity(
                opportunity_type="underserved_genre",
                description=f"{genre['name']} has only {genre['count']} games but high average CCU ({genre['avg_ccu']:,.0f})",
                confidence=0.8,
                supporting_data={
                    "genre": genre["name"],
                    "game_count": genre["count"],
                    "avg_ccu": genre["avg_ccu"],
                },
                recommended_action=f"Consider creating a {genre['name']} game with unique mechanics"
            ))

    # Find oversaturated genres (many games, low avg CCU)
    for genre in genres:
        if genre["count"] > 5 and genre["avg_ccu"] < 5000:
            opportunities.append(MarketOpportunity(
                opportunity_type="saturated_warning",
                description=f"{genre['name']} is saturated: {genre['count']} games with low average CCU ({genre['avg_ccu']:,.0f})",
                confidence=0.7,
                supporting_data={
                    "genre": genre["name"],
                    "game_count": genre["count"],
                    "avg_ccu": genre["avg_ccu"],
                },
                recommended_action=f"Avoid {genre['name']} unless you have a strong differentiator"
            ))

    # Find top-heavy genres (one dominant game)
    for genre in genres:
        if genre.get("top_game_share", 0) > 0.7:
            opportunities.append(MarketOpportunity(
                opportunity_type="challenger_opportunity",
                description=f"{genre['name']} is dominated by one game - room for a strong #2",
                confidence=0.6,
                supporting_data=genre,
                recommended_action=f"Study the dominant {genre['name']} game and create an alternative"
            ))

    return opportunities


def generate_recommendations(games: list, genres: list, opportunities: list) -> dict:
    """Generate actionable recommendations for Zetta."""

    # Find best genres
    genre_scores = []
    for g in genres:
        # Score based on: high avg CCU, low saturation, reasonable game count
        score = (g["avg_ccu"] / 1000) * (1 if g["saturation"] == "low" else 0.5 if g["saturation"] == "medium" else 0.2)
        genre_scores.append({"genre": g["name"], "score": score})

    best_genres = sorted(genre_scores, key=lambda x: x["score"], reverse=True)[:3]

    # Find successful game patterns
    top_games = sorted(games, key=lambda x: x["playing"], reverse=True)[:10]

    return {
        "recommended_genres": [g["genre"] for g in best_genres],
        "genre_reasoning": {g["genre"]: f"Score: {g['score']:.1f}" for g in best_genres},
        "successful_patterns": {
            "top_genres_in_top_10": list(set(g["genre"] for g in top_games if g.get("genre"))),
            "avg_engagement_of_top_10": sum(g.get("engagement_score", 0) for g in top_games) / len(top_games) if top_games else 0,
        },
        "avoid_list": [o.supporting_data.get("genre") for o in opportunities if o.opportunity_type == "saturated_warning"],
        "key_insights": [
            f"Total market: {sum(g['playing'] for g in games):,} concurrent players",
            f"Top 5 games hold {sum(g['playing'] for g in top_games[:5]) / max(sum(g['playing'] for g in games), 1) * 100:.1f}% of the market",
            f"Most diverse genre: {max(genres, key=lambda x: x['count'])['name']} with {max(genres, key=lambda x: x['count'])['count']} games",
        ]
    }


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/zetta", response_model=ZettaExport)
async def export_for_zetta(
    session: AsyncSession = Depends(get_session),
):
    """
    Generate a comprehensive export for Zetta game creator.

    Returns structured market analysis data including:
    - All tracked games with metrics and scores
    - Genre analysis and saturation levels
    - Market opportunities
    - Actionable recommendations

    Schema version is included for forward compatibility.
    """

    # Fetch all games
    result = await session.execute(
        select(Game).order_by(desc(Game.playing))
    )
    games = result.scalars().all()

    if not games:
        return ZettaExport(
            export_timestamp=datetime.utcnow(),
            data_freshness_hours=-1,
            summary={"error": "No data available"},
            games=[],
            genres=[],
            opportunities=[],
            recommendations={},
        )

    # Calculate data freshness
    latest_update = max(g.updated_at for g in games if g.updated_at)
    freshness_hours = (datetime.utcnow() - latest_update).total_seconds() / 3600 if latest_update else -1

    # Process games
    total_players = sum(g.playing for g in games)
    game_analyses = []

    for rank, game in enumerate(games, 1):
        visits_ratio = game.visits / max(game.playing, 1) if game.playing > 0 else 0
        favorites_ratio = game.favorites / max(game.visits, 1) if game.visits > 0 else 0

        analysis = GameAnalysis(
            universe_id=game.id,
            name=game.name,
            creator=game.creator_name,
            genre=game.genre,
            metrics=GameMetrics(
                current_players=game.playing,
                total_visits=game.visits,
                favorites=game.favorites,
                visits_per_player_ratio=round(visits_ratio, 2),
                favorites_per_visit_ratio=round(favorites_ratio, 6),
            ),
            popularity_score=calculate_popularity_score(rank, len(games)),
            engagement_score=calculate_engagement_score(game.visits, game.playing, game.favorites),
            tier=calculate_tier(game.playing),
            last_updated=game.updated_at,
        )
        game_analyses.append(analysis)

    # Process genres
    genre_stats = {}
    for game in games:
        genre = game.genre or "Unknown"
        if genre not in genre_stats:
            genre_stats[genre] = {"games": [], "total_ccu": 0}
        genre_stats[genre]["games"].append(game)
        genre_stats[genre]["total_ccu"] += game.playing

    genre_analyses = []
    for genre_name, data in genre_stats.items():
        game_count = len(data["games"])
        total_ccu = data["total_ccu"]
        avg_ccu = total_ccu / game_count if game_count > 0 else 0

        # Get top games in genre
        top_in_genre = sorted(data["games"], key=lambda x: x.playing, reverse=True)[:3]

        # Calculate if one game dominates
        if top_in_genre and total_ccu > 0:
            top_game_share = top_in_genre[0].playing / total_ccu
        else:
            top_game_share = 0

        genre_analyses.append(GenreAnalysis(
            name=genre_name,
            game_count=game_count,
            total_ccu=total_ccu,
            avg_ccu_per_game=round(avg_ccu, 2),
            market_share_percent=round(total_ccu / total_players * 100, 2) if total_players > 0 else 0,
            saturation_level=calculate_saturation(game_count, avg_ccu),
            top_games=[g.name for g in top_in_genre],
        ))

    # Sort genres by market share
    genre_analyses.sort(key=lambda x: x.market_share_percent, reverse=True)

    # Prepare data for opportunity analysis
    games_data = [{"name": g.name, "playing": g.playing, "genre": g.genre, "engagement_score": 0} for g in games]
    genres_data = [
        {
            "name": g.name,
            "count": g.game_count,
            "avg_ccu": g.avg_ccu_per_game,
            "saturation": g.saturation_level,
            "top_game_share": genre_stats[g.name]["games"][0].playing / g.total_ccu if g.total_ccu > 0 else 0
        }
        for g in genre_analyses
    ]

    # Generate opportunities and recommendations
    opportunities = identify_opportunities(games_data, genres_data, total_players)
    recommendations = generate_recommendations(games_data, genres_data, opportunities)

    # Build summary
    summary = {
        "total_games_tracked": len(games),
        "total_concurrent_players": total_players,
        "unique_genres": len(genre_analyses),
        "tier_distribution": {
            "mega": len([g for g in game_analyses if g.tier == "mega"]),
            "high": len([g for g in game_analyses if g.tier == "high"]),
            "mid": len([g for g in game_analyses if g.tier == "mid"]),
            "low": len([g for g in game_analyses if g.tier == "low"]),
            "micro": len([g for g in game_analyses if g.tier == "micro"]),
        },
        "market_concentration": {
            "top_5_share_percent": round(sum(g.metrics.current_players for g in game_analyses[:5]) / total_players * 100, 2) if total_players > 0 else 0,
            "top_10_share_percent": round(sum(g.metrics.current_players for g in game_analyses[:10]) / total_players * 100, 2) if total_players > 0 else 0,
        },
    }

    # =========================================================================
    # Monetization Data
    # =========================================================================

    # Fetch all game passes
    passes_result = await session.execute(
        select(GamePass).where(GamePass.is_for_sale == True)
    )
    all_passes = passes_result.scalars().all()

    # Build monetization patterns
    monetization_patterns = None
    game_monetization = []

    if all_passes:
        # Group passes by game
        passes_by_game = {}
        for p in all_passes:
            if p.game_id not in passes_by_game:
                passes_by_game[p.game_id] = []
            passes_by_game[p.game_id].append(p)

        # Calculate overall stats
        prices = [p.price for p in all_passes if p.price]
        overall_avg = sum(prices) / len(prices) if prices else 0

        # Pass type popularity
        type_counts = {}
        for p in all_passes:
            pt = p.pass_type or "other"
            type_counts[pt] = type_counts.get(pt, 0) + 1

        type_popularity = sorted(
            [{"type": t, "count": c, "percent": round(c / len(all_passes) * 100, 1)}
             for t, c in type_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )

        # Price tier distribution
        tier_counts = {"budget": 0, "standard": 0, "premium": 0, "luxury": 0, "whale": 0}
        for price in prices:
            if price < 50:
                tier_counts["budget"] += 1
            elif price < 200:
                tier_counts["standard"] += 1
            elif price < 500:
                tier_counts["premium"] += 1
            elif price < 1000:
                tier_counts["luxury"] += 1
            else:
                tier_counts["whale"] += 1

        # Genre monetization (need to cross-reference with games)
        genre_prices = {}
        for game in games:
            if game.id in passes_by_game:
                genre = game.genre or "Unknown"
                if genre not in genre_prices:
                    genre_prices[genre] = []
                for p in passes_by_game[game.id]:
                    if p.price:
                        genre_prices[genre].append(p.price)

        genre_monetization = sorted(
            [{"genre": g, "avg_price": round(sum(prices) / len(prices), 0), "pass_count": len(prices)}
             for g, prices in genre_prices.items() if prices],
            key=lambda x: x["avg_price"],
            reverse=True
        )

        # Generate strategy insights
        top_strategies = []
        if type_popularity:
            top_strategies.append(f"Most common pass type: {type_popularity[0]['type']} ({type_popularity[0]['percent']}%)")
        if overall_avg > 0:
            top_strategies.append(f"Market average price: {overall_avg:.0f} Robux")
        if genre_monetization:
            top_genre = genre_monetization[0]
            top_strategies.append(f"Highest monetizing genre: {top_genre['genre']} (avg {top_genre['avg_price']:.0f}R$)")

        # VIP analysis
        vip_passes = [p for p in all_passes if p.pass_type == "vip" and p.price]
        if vip_passes:
            avg_vip = sum(p.price for p in vip_passes) / len(vip_passes)
            top_strategies.append(f"VIP passes average: {avg_vip:.0f} Robux")

        monetization_patterns = MonetizationPatterns(
            total_passes_tracked=len(all_passes),
            games_with_passes=len(passes_by_game),
            avg_passes_per_game=round(len(all_passes) / len(passes_by_game), 1) if passes_by_game else 0,
            overall_avg_price=round(overall_avg, 0),
            price_tier_distribution=tier_counts,
            pass_type_popularity=type_popularity[:10],
            genre_monetization=genre_monetization[:10],
            top_strategies=top_strategies,
        )

        # Per-game monetization details (for top 20 games)
        for game in games[:20]:
            if game.id in passes_by_game:
                game_passes = passes_by_game[game.id]
                prices = [p.price for p in game_passes if p.price]

                if prices:
                    # Pass type breakdown
                    type_breakdown = {}
                    for p in game_passes:
                        pt = p.pass_type or "other"
                        type_breakdown[pt] = type_breakdown.get(pt, 0) + 1

                    strategy = MonetizationStrategy(
                        pass_count=len(game_passes),
                        price_range=[min(prices), max(prices)],
                        avg_price=round(sum(prices) / len(prices), 0),
                        total_potential_spend=sum(prices),
                        pass_type_breakdown=type_breakdown,
                        pricing_tier=determine_pricing_tier(sum(prices) / len(prices)),
                    )

                    game_monetization.append(GameMonetizationAnalysis(
                        game_id=game.id,
                        game_name=game.name,
                        strategy=strategy,
                        passes=[
                            {"name": p.name, "price": p.price, "type": p.pass_type}
                            for p in game_passes
                        ],
                    ))

    return ZettaExport(
        schema_version=SCHEMA_VERSION,
        export_timestamp=datetime.utcnow(),
        data_freshness_hours=round(freshness_hours, 2),
        summary=summary,
        games=game_analyses,
        genres=genre_analyses,
        monetization=monetization_patterns,
        game_monetization=game_monetization,
        opportunities=opportunities,
        recommendations=recommendations,
    )


@router.get("/zetta/schema")
async def get_zetta_schema():
    """
    Returns the JSON schema for the Zetta export format.

    Use this to validate exports or for documentation.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "description": "BloxPulse export schema for Zetta game creator integration",
        "fields": {
            "schema_version": "Semantic version string for forward compatibility",
            "export_timestamp": "ISO 8601 timestamp of export generation",
            "data_freshness_hours": "Hours since last data collection",
            "summary": "High-level market statistics",
            "games": "Array of GameAnalysis objects with metrics and scores",
            "genres": "Array of GenreAnalysis objects with saturation levels",
            "monetization": "Overall monetization patterns across all games",
            "game_monetization": "Per-game monetization details for top games",
            "opportunities": "Array of identified market opportunities",
            "recommendations": "Actionable recommendations for game development",
        },
        "monetization_fields": {
            "total_passes_tracked": "Total number of game passes collected",
            "games_with_passes": "Number of games that have monetization",
            "avg_passes_per_game": "Average passes per game",
            "overall_avg_price": "Market average pass price in Robux",
            "price_tier_distribution": "Distribution across budget/standard/premium/luxury/whale tiers",
            "pass_type_popularity": "Most common pass types (vip, cosmetic, power, etc.)",
            "genre_monetization": "Average prices by genre",
            "top_strategies": "Key monetization insights",
        },
        "tiers": {
            "mega": "100,000+ concurrent players",
            "high": "20,000-99,999 concurrent players",
            "mid": "5,000-19,999 concurrent players",
            "low": "1,000-4,999 concurrent players",
            "micro": "<1,000 concurrent players",
        },
        "pricing_tiers": {
            "budget": "Average pass price <100 Robux",
            "standard": "Average pass price 100-299 Robux",
            "premium": "Average pass price 300-599 Robux",
            "whale-focused": "Average pass price 600+ Robux",
        },
        "scores": {
            "popularity_score": "0-100, based on CCU rank",
            "engagement_score": "0-100, based on visits/player and favorites ratios",
        },
    }
