"""
Game Discovery Script

Converts Place IDs to Universe IDs and validates games for tracking.
Run this script to expand the game list in collectors/roblox.py
"""

import asyncio
import httpx


# Place IDs gathered from web searches and tracking sites
# These need to be converted to Universe IDs for the Roblox API
DISCOVERED_PLACE_IDS = [
    # ===== TOP TRENDING (2026) =====
    126884695634066,  # Grow a Garden (NEW - viral 2026)

    # ===== TOP 20 BY VISITS/CCU =====
    1962086868,   # Tower of Hell
    370731277,    # MeepCity
    4623386862,   # Piggy
    15101393044,  # Dress To Impress
    286090429,    # Arsenal
    16732694052,  # Fisch
    17017769292,  # Anime Defenders
    13775256536,  # Toilet Tower Defense
    5233782396,   # Creatures of Sonaria
    4616652839,   # Shindo Life
    192800,       # Work at a Pizza Place (classic)
    1224212277,   # Mad City Chapter 2
    69184822,     # Theme Park Tycoon 2
    4580204640,   # Survive the Killer
    171391948,    # Vehicle Simulator
    2727067538,   # World // Zero
    3351674303,   # Driving Empire
    891852901,    # Greenville
    5104202731,   # Southwest Florida
    183364845,    # Speed Run 4
    6447798030,   # Funky Friday
    893973440,    # Flee the Facility

    # ===== ROLEPLAY & SOCIAL =====
    920587237,    # Livetopia
    4924922222,   # Ragdoll Engine
    2017374649,   # Super Golf
    4483381587,   # Super Striker League
    3956818381,   # Speed Race
    4439610654,   # Anime Fighting Simulator
    5576884243,   # The Mimic
    4872369839,   # Murder Mystery 3
    6943569276,   # Genesis Alpha
    2788229376,   # Rogue Lineage

    # ===== SIMULATORS =====
    4972273297,   # Mining Simulator 2
    4924922222,   # Pet Simulator (original)
    13822889,     # Super Hero Tycoon
    301549746,    # Bubble Gum Simulator
    2784731805,   # Anime Fighters Simulator
    4751234059,   # My Restaurant!

    # ===== HORROR =====
    6516141723,   # Apeirophobia
    2653632261,   # Bear (Alpha)
    8497143577,   # Regretevator
    6516141723,   # Pressure
    3527629287,   # Residence Massacre
    2558849451,   # Identity Fraud

    # ===== ACTION & COMBAT =====
    4442272183,   # Project Slayers
    6069928974,   # Deepwoken
    5608545938,   # Project Star
    2809202155,   # Your Bizarre Adventure
    3429416223,   # A Universal Time
    6284583030,   # All Star Tower Defense
    4521635730,   # Anime Dimensions

    # ===== SPORTS & RACING =====
    6872265039,   # Retro Bowl
    6573227032,   # Soccer Legends

    # ===== TYCOONS =====
    6718303552,   # Military Tycoon
    4922741943,   # Restaurant Tycoon 2

    # ===== ADVENTURE & RPG =====
    2474168535,   # Dragon Adventures
    4520749081,   # Project Mugetsu
    5753856982,   # Type Soul
    5505434564,   # Grand Piece Online
    6755929666,   # Sols RNG
    6154272481,   # Anime Last Stand
    4442272183,   # Project Slayers
]


async def convert_place_to_universe(client: httpx.AsyncClient, place_id: int) -> dict:
    """Convert a Place ID to Universe ID using Roblox API."""
    try:
        url = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
        response = await client.get(url)

        if response.status_code == 200:
            data = response.json()
            return {
                "place_id": place_id,
                "universe_id": data.get("universeId"),
                "success": True
            }
        else:
            return {
                "place_id": place_id,
                "universe_id": None,
                "success": False,
                "error": f"HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "place_id": place_id,
            "universe_id": None,
            "success": False,
            "error": str(e)
        }


async def get_game_details(client: httpx.AsyncClient, universe_ids: list[int]) -> list[dict]:
    """Get game details to verify the universe ID is valid."""
    if not universe_ids:
        return []

    url = "https://games.roblox.com/v1/games"
    params = {"universeIds": ",".join(map(str, universe_ids[:100]))}

    try:
        response = await client.get(url, params=params)
        if response.status_code == 200:
            return response.json().get("data", [])
    except Exception as e:
        print(f"Error fetching game details: {e}")

    return []


async def main():
    """Convert all Place IDs to Universe IDs and validate."""
    print("=" * 60)
    print("BloxPulse Game Discovery Script")
    print("=" * 60)

    async with httpx.AsyncClient(
        timeout=30.0,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        },
    ) as client:

        # Remove duplicates
        unique_place_ids = list(set(DISCOVERED_PLACE_IDS))
        print(f"\nProcessing {len(unique_place_ids)} unique Place IDs...")

        # Convert Place IDs to Universe IDs
        results = []
        for i, place_id in enumerate(unique_place_ids):
            result = await convert_place_to_universe(client, place_id)
            results.append(result)

            if result["success"]:
                print(f"  [{i+1}/{len(unique_place_ids)}] Place {place_id} -> Universe {result['universe_id']}")
            else:
                print(f"  [{i+1}/{len(unique_place_ids)}] Place {place_id} -> FAILED: {result.get('error')}")

            await asyncio.sleep(0.2)  # Rate limiting

        # Filter successful conversions
        successful = [r for r in results if r["success"] and r["universe_id"]]
        universe_ids = [r["universe_id"] for r in successful]

        print(f"\n{len(successful)}/{len(unique_place_ids)} Place IDs converted successfully")

        # Validate universe IDs by fetching game details
        print("\nValidating Universe IDs...")
        games = await get_game_details(client, universe_ids)

        valid_games = []
        for game in games:
            universe_id = game.get("id")
            name = game.get("name", "Unknown")
            playing = game.get("playing", 0)

            # Skip placeholder games
            if "'s Place" in name:
                print(f"  SKIP: {universe_id} ({name}) - placeholder")
                continue

            valid_games.append({
                "universe_id": universe_id,
                "name": name,
                "playing": playing,
            })

        # Sort by CCU
        valid_games.sort(key=lambda x: x["playing"], reverse=True)

        print(f"\n{len(valid_games)} valid games found:")
        print("-" * 60)

        # Generate code for roblox.py
        print("\n# ===== COPY THIS TO collectors/roblox.py =====")
        print("POPULAR_GAMES = [")

        current_tier = None
        for game in valid_games:
            # Determine tier
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
                print(f"\n    # ===== {tier} =====")
                current_tier = tier

            # Remove emojis and special characters from name for display
            safe_name = game['name'].encode('ascii', 'ignore').decode('ascii').strip()
            print(f"    {game['universe_id']},   # {safe_name} ({ccu:,})")

        print("]")
        print("# ===== END COPY =====")


if __name__ == "__main__":
    asyncio.run(main())
