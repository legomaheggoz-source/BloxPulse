"""
Game Validation Script

Validates scraped games against Roblox API:
1. Converts Place IDs to Universe IDs
2. Fetches game details to verify they're real games
3. Filters out placeholder games ("X's Place")
4. Updates the POPULAR_GAMES list in roblox.py
"""

import asyncio
import json
import re
from pathlib import Path
from datetime import datetime

import httpx


# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_FILE = DATA_DIR / "discovered_games.json"
ROBLOX_FILE = Path(__file__).parent.parent / "collectors" / "roblox.py"


async def convert_place_to_universe(client: httpx.AsyncClient, place_id: int) -> int | None:
    """Convert a Place ID to Universe ID."""
    try:
        url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("universeId")
    except Exception:
        pass
    return None


async def get_game_details(client: httpx.AsyncClient, universe_ids: list[int]) -> list[dict]:
    """Get game details for multiple Universe IDs."""
    if not universe_ids:
        return []

    valid_games = []

    # Process in batches of 50 (Roblox API limit)
    for i in range(0, len(universe_ids), 50):
        batch = universe_ids[i:i + 50]
        url = "https://games.roblox.com/v1/games"
        params = {"universeIds": ",".join(map(str, batch))}

        try:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                for game in data.get("data", []):
                    name = game.get("name", "")
                    playing = game.get("playing", 0)
                    visits = game.get("visits", 0)

                    # Filter out placeholder games
                    if "'s Place" in name:
                        continue
                    if playing == 0 and visits < 1000:
                        continue

                    valid_games.append({
                        "universe_id": game.get("id"),
                        "name": name,
                        "playing": playing,
                        "visits": visits,
                        "genre": game.get("genre"),
                    })

            await asyncio.sleep(0.3)  # Rate limiting
        except Exception as e:
            print(f"Error fetching batch: {e}")

    return valid_games


def update_roblox_py(games: list[dict]):
    """Update the POPULAR_GAMES list in roblox.py."""
    # Sort by CCU
    games.sort(key=lambda x: x["playing"], reverse=True)

    # Read current file
    content = ROBLOX_FILE.read_text()

    # Generate new POPULAR_GAMES list
    lines = [
        "# Curated list of popular Roblox games (Universe IDs - NOT Place IDs!)",
        "# Auto-updated by GitHub Actions game discovery workflow",
        f"# Last updated: {datetime.utcnow().strftime('%Y-%m-%d')} with {len(games)} verified games",
        "POPULAR_GAMES = ["
    ]

    # Group by tier
    current_tier = None
    for game in games:
        ccu = game["playing"]
        if ccu >= 100000:
            tier = "TIER 1: Mega (100k+)"
        elif ccu >= 20000:
            tier = "TIER 2: High (20k-100k)"
        elif ccu >= 5000:
            tier = "TIER 3: Medium (5k-20k)"
        elif ccu >= 1000:
            tier = "TIER 4: Low (1k-5k)"
        else:
            tier = "TIER 5: Micro (<1k)"

        if tier != current_tier:
            lines.append(f"\n    # ===== {tier} =====")
            current_tier = tier

        # Sanitize name for comment
        safe_name = game["name"].encode('ascii', 'ignore').decode('ascii').strip()[:40]
        lines.append(f"    {game['universe_id']},   # {safe_name} ({ccu:,})")

    lines.append("]")

    # Replace the POPULAR_GAMES section in the file
    pattern = r"# Curated list of popular Roblox games.*?^POPULAR_GAMES = \[.*?^\]"
    new_section = "\n".join(lines)

    new_content = re.sub(pattern, new_section, content, flags=re.MULTILINE | re.DOTALL)

    # Write updated file
    ROBLOX_FILE.write_text(new_content)
    print(f"✓ Updated {ROBLOX_FILE} with {len(games)} games")


async def main():
    """Main validation function."""
    print("=" * 60)
    print("BloxPulse Game Validation")
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print("=" * 60)

    # Load scraped data
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found. Run scrape_games.py first.")
        return

    with open(INPUT_FILE) as f:
        data = json.load(f)

    raw_games = data.get("games", [])
    print(f"\nLoaded {len(raw_games)} raw scraped games")

    # Collect all IDs
    universe_ids = set()
    place_ids_to_convert = []

    for game in raw_games:
        if "universe_id" in game:
            universe_ids.add(game["universe_id"])
        elif "place_id" in game:
            place_ids_to_convert.append(game["place_id"])

    print(f"  - {len(universe_ids)} Universe IDs")
    print(f"  - {len(place_ids_to_convert)} Place IDs to convert")

    async with httpx.AsyncClient(
        timeout=30.0,
        headers={"User-Agent": "Mozilla/5.0"}
    ) as client:

        # Convert Place IDs to Universe IDs
        if place_ids_to_convert:
            print("\nConverting Place IDs to Universe IDs...")
            for i, place_id in enumerate(place_ids_to_convert):
                universe_id = await convert_place_to_universe(client, place_id)
                if universe_id:
                    universe_ids.add(universe_id)
                if (i + 1) % 20 == 0:
                    print(f"  Converted {i + 1}/{len(place_ids_to_convert)}")
                await asyncio.sleep(0.2)  # Rate limiting

        print(f"\nTotal unique Universe IDs: {len(universe_ids)}")

        # Validate Universe IDs
        print("\nValidating games against Roblox API...")
        valid_games = await get_game_details(client, list(universe_ids))
        print(f"✓ {len(valid_games)} valid games found")

    # Update roblox.py with validated games
    if valid_games:
        update_roblox_py(valid_games)

        # Save validated data
        validated_file = DATA_DIR / "validated_games.json"
        with open(validated_file, "w") as f:
            json.dump({
                "validated_at": datetime.utcnow().isoformat(),
                "total": len(valid_games),
                "games": valid_games
            }, f, indent=2)
        print(f"✓ Saved validated games to {validated_file}")

    print("\n✓ Validation complete!")


if __name__ == "__main__":
    asyncio.run(main())
