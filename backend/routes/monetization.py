"""
Monetization API Routes

Endpoints for game pass data and monetization analysis.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from database import get_session, GamePass, Game

router = APIRouter(prefix="/api/v1/monetization", tags=["Monetization"])


@router.get("/passes")
async def get_game_passes(
    game_id: int = Query(None, description="Filter by game ID"),
    pass_type: str = Query(None, description="Filter by pass type"),
    min_price: int = Query(None, description="Minimum price in Robux"),
    max_price: int = Query(None, description="Maximum price in Robux"),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    session: AsyncSession = Depends(get_session),
):
    """Get game passes with optional filters."""
    query = select(GamePass, Game.name.label("game_name")).join(
        Game, GamePass.game_id == Game.id, isouter=True
    )

    if game_id:
        query = query.where(GamePass.game_id == game_id)
    if pass_type:
        query = query.where(GamePass.pass_type == pass_type)
    if min_price is not None:
        query = query.where(GamePass.price >= min_price)
    if max_price is not None:
        query = query.where(GamePass.price <= max_price)

    query = query.where(GamePass.is_for_sale == True)
    query = query.order_by(GamePass.price.desc().nullslast())
    query = query.offset(offset).limit(limit)

    result = await session.execute(query)
    rows = result.fetchall()

    passes = []
    for row in rows:
        gp = row[0]
        passes.append({
            "id": gp.id,
            "game_id": gp.game_id,
            "game_name": row.game_name,
            "name": gp.name,
            "description": gp.description,
            "price": gp.price,
            "pass_type": gp.pass_type,
        })

    return {"passes": passes, "count": len(passes)}


@router.get("/stats")
async def get_monetization_stats(
    session: AsyncSession = Depends(get_session),
):
    """Get overall monetization statistics."""
    # Total passes and games with passes
    total_result = await session.execute(
        select(
            func.count(GamePass.id).label("total_passes"),
            func.count(func.distinct(GamePass.game_id)).label("games_with_passes"),
        ).where(GamePass.is_for_sale == True)
    )
    totals = total_result.fetchone()

    # Price statistics
    price_result = await session.execute(
        select(
            func.avg(GamePass.price).label("avg_price"),
            func.min(GamePass.price).label("min_price"),
            func.max(GamePass.price).label("max_price"),
            func.sum(GamePass.price).label("total_price_sum"),
        ).where(GamePass.is_for_sale == True, GamePass.price.isnot(None))
    )
    prices = price_result.fetchone()

    # Pass type distribution
    type_result = await session.execute(
        select(
            GamePass.pass_type,
            func.count(GamePass.id).label("count"),
            func.avg(GamePass.price).label("avg_price"),
        )
        .where(GamePass.is_for_sale == True)
        .group_by(GamePass.pass_type)
        .order_by(func.count(GamePass.id).desc())
    )
    type_dist = [
        {
            "type": row.pass_type or "uncategorized",
            "count": row.count,
            "avg_price": round(row.avg_price, 0) if row.avg_price else None,
        }
        for row in type_result.fetchall()
    ]

    # Price tier distribution
    tier_result = await session.execute(
        select(
            case(
                (GamePass.price < 50, "budget"),
                (GamePass.price < 200, "standard"),
                (GamePass.price < 500, "premium"),
                (GamePass.price < 1000, "luxury"),
                else_="whale"
            ).label("tier"),
            func.count(GamePass.id).label("count"),
        )
        .where(GamePass.is_for_sale == True, GamePass.price.isnot(None))
        .group_by("tier")
    )
    price_tiers = {row.tier: row.count for row in tier_result.fetchall()}

    return {
        "total_passes": totals.total_passes if totals else 0,
        "games_with_passes": totals.games_with_passes if totals else 0,
        "avg_price": round(prices.avg_price, 0) if prices and prices.avg_price else 0,
        "min_price": prices.min_price if prices else 0,
        "max_price": prices.max_price if prices else 0,
        "pass_type_distribution": type_dist,
        "price_tiers": {
            "budget": price_tiers.get("budget", 0),      # <50
            "standard": price_tiers.get("standard", 0),  # 50-199
            "premium": price_tiers.get("premium", 0),    # 200-499
            "luxury": price_tiers.get("luxury", 0),      # 500-999
            "whale": price_tiers.get("whale", 0),        # 1000+
        },
    }


@router.get("/patterns")
async def get_monetization_patterns(
    session: AsyncSession = Depends(get_session),
):
    """Analyze monetization patterns across top games."""
    # Get games with their pass statistics
    game_stats = await session.execute(
        select(
            Game.id,
            Game.name,
            Game.genre,
            Game.playing,
            func.count(GamePass.id).label("pass_count"),
            func.avg(GamePass.price).label("avg_pass_price"),
            func.min(GamePass.price).label("min_pass_price"),
            func.max(GamePass.price).label("max_pass_price"),
        )
        .join(GamePass, Game.id == GamePass.game_id)
        .where(GamePass.is_for_sale == True)
        .group_by(Game.id)
        .order_by(Game.playing.desc())
        .limit(20)
    )

    top_games = []
    for row in game_stats.fetchall():
        # Get pass types for this game
        types_result = await session.execute(
            select(GamePass.pass_type, func.count(GamePass.id))
            .where(GamePass.game_id == row.id, GamePass.is_for_sale == True)
            .group_by(GamePass.pass_type)
        )
        pass_types = {r[0] or "other": r[1] for r in types_result.fetchall()}

        top_games.append({
            "id": row.id,
            "name": row.name,
            "genre": row.genre,
            "ccu": row.playing,
            "pass_count": row.pass_count,
            "avg_price": round(row.avg_pass_price, 0) if row.avg_pass_price else 0,
            "price_range": [row.min_pass_price, row.max_pass_price],
            "pass_types": pass_types,
        })

    # Genre-based monetization patterns
    genre_stats = await session.execute(
        select(
            Game.genre,
            func.count(func.distinct(Game.id)).label("game_count"),
            func.avg(GamePass.price).label("avg_price"),
            func.count(GamePass.id).label("total_passes"),
        )
        .join(GamePass, Game.id == GamePass.game_id)
        .where(GamePass.is_for_sale == True, Game.genre.isnot(None))
        .group_by(Game.genre)
        .order_by(func.avg(GamePass.price).desc())
    )

    genre_patterns = [
        {
            "genre": row.genre,
            "game_count": row.game_count,
            "avg_price": round(row.avg_price, 0) if row.avg_price else 0,
            "avg_passes_per_game": round(row.total_passes / row.game_count, 1),
        }
        for row in genre_stats.fetchall()
    ]

    # Common pass name patterns (what sells)
    common_passes = await session.execute(
        select(
            GamePass.name,
            GamePass.pass_type,
            func.count(GamePass.id).label("frequency"),
            func.avg(GamePass.price).label("avg_price"),
        )
        .where(GamePass.is_for_sale == True)
        .group_by(GamePass.name, GamePass.pass_type)
        .having(func.count(GamePass.id) >= 2)
        .order_by(func.count(GamePass.id).desc())
        .limit(20)
    )

    popular_passes = [
        {
            "name": row.name,
            "type": row.pass_type,
            "frequency": row.frequency,
            "avg_price": round(row.avg_price, 0) if row.avg_price else 0,
        }
        for row in common_passes.fetchall()
    ]

    return {
        "top_games": top_games,
        "genre_patterns": genre_patterns,
        "popular_pass_types": popular_passes,
        "insights": generate_insights(top_games, genre_patterns, popular_passes),
    }


def generate_insights(top_games: list, genre_patterns: list, popular_passes: list) -> list[str]:
    """Generate actionable monetization insights."""
    insights = []

    if top_games:
        # Average passes per successful game
        avg_passes = sum(g["pass_count"] for g in top_games) / len(top_games)
        insights.append(f"Top games average {avg_passes:.0f} game passes each")

        # Price range insight
        all_avg_prices = [g["avg_price"] for g in top_games if g["avg_price"]]
        if all_avg_prices:
            overall_avg = sum(all_avg_prices) / len(all_avg_prices)
            insights.append(f"Average pass price in top games: {overall_avg:.0f} Robux")

        # Most common pass type in top games
        type_counts = {}
        for g in top_games:
            for pt, count in g.get("pass_types", {}).items():
                type_counts[pt] = type_counts.get(pt, 0) + count
        if type_counts:
            top_type = max(type_counts, key=type_counts.get)
            insights.append(f"Most common pass type in top games: {top_type}")

    if genre_patterns:
        # Highest monetizing genre
        top_genre = genre_patterns[0]
        insights.append(
            f"{top_genre['genre']} games have highest avg pass price ({top_genre['avg_price']} Robux)"
        )

    if popular_passes:
        # VIP is almost always present
        vip_passes = [p for p in popular_passes if "vip" in p["name"].lower()]
        if vip_passes:
            avg_vip = sum(p["avg_price"] for p in vip_passes) / len(vip_passes)
            insights.append(f"VIP passes are standard - avg price: {avg_vip:.0f} Robux")

    return insights


@router.get("/game/{game_id}")
async def get_game_monetization(
    game_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get detailed monetization data for a specific game."""
    # Get game info
    game_result = await session.execute(
        select(Game).where(Game.id == game_id)
    )
    game = game_result.scalar_one_or_none()

    if not game:
        return {"error": "Game not found"}

    # Get all passes for this game
    passes_result = await session.execute(
        select(GamePass)
        .where(GamePass.game_id == game_id)
        .order_by(GamePass.price.desc().nullslast())
    )
    passes = passes_result.scalars().all()

    # Calculate stats
    for_sale = [p for p in passes if p.is_for_sale and p.price]
    total_price = sum(p.price for p in for_sale) if for_sale else 0
    avg_price = total_price / len(for_sale) if for_sale else 0

    # Group by type
    by_type = {}
    for p in passes:
        pt = p.pass_type or "other"
        if pt not in by_type:
            by_type[pt] = []
        by_type[pt].append({
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "is_for_sale": p.is_for_sale,
        })

    return {
        "game": {
            "id": game.id,
            "name": game.name,
            "genre": game.genre,
            "ccu": game.playing,
        },
        "summary": {
            "total_passes": len(passes),
            "for_sale": len(for_sale),
            "avg_price": round(avg_price, 0),
            "total_potential_spend": total_price,
            "price_range": [
                min(p.price for p in for_sale) if for_sale else 0,
                max(p.price for p in for_sale) if for_sale else 0,
            ],
        },
        "passes_by_type": by_type,
        "all_passes": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "pass_type": p.pass_type,
                "is_for_sale": p.is_for_sale,
            }
            for p in passes
        ],
    }
