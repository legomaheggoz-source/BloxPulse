"""
Game Scraper Script

Uses Playwright to scrape popular Roblox games from tracking sites.
Runs in GitHub Actions weekly to keep the game list updated.
"""

import asyncio
import json
import re
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("Playwright not installed - using fallback method")


# Output paths
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "discovered_games.json"


async def scrape_romonitor_stats() -> list[dict]:
    """Scrape top games from RoMonitor Stats."""
    games = []

    if not HAS_PLAYWRIGHT:
        return games

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print("Loading RoMonitor Stats...")
            await page.goto("https://romonitorstats.com/", timeout=60000)

            # Wait for games to load
            await page.wait_for_selector(".game-card, .game-item, [data-game-id]", timeout=30000)

            # Extract game data from the page
            game_elements = await page.query_selector_all(".game-card, .game-item, [data-game-id]")

            for element in game_elements[:100]:  # Limit to top 100
                try:
                    # Try to extract universe ID from data attribute or link
                    universe_id = await element.get_attribute("data-universe-id")
                    if not universe_id:
                        link = await element.query_selector("a[href*='roblox.com/games']")
                        if link:
                            href = await link.get_attribute("href")
                            # Extract ID from URL
                            match = re.search(r'/games/(\d+)', href)
                            if match:
                                universe_id = match.group(1)

                    name = await element.query_selector(".game-name, .name, h3, h4")
                    name_text = await name.inner_text() if name else "Unknown"

                    if universe_id:
                        games.append({
                            "universe_id": int(universe_id),
                            "name": name_text.strip(),
                            "source": "romonitor"
                        })
                except Exception as e:
                    print(f"Error extracting game: {e}")
                    continue

        except Exception as e:
            print(f"Error scraping RoMonitor: {e}")
        finally:
            await browser.close()

    return games


async def scrape_roblox_discover() -> list[dict]:
    """Scrape games directly from Roblox discover page."""
    games = []

    if not HAS_PLAYWRIGHT:
        return games

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print("Loading Roblox Discover page...")
            await page.goto("https://www.roblox.com/discover", timeout=60000)

            # Wait for games to load
            await page.wait_for_selector("[data-testid='game-tile']", timeout=30000)

            # Scroll to load more games
            for _ in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

            # Extract game links
            game_links = await page.query_selector_all("a[href*='/games/']")

            seen_ids = set()
            for link in game_links:
                try:
                    href = await link.get_attribute("href")
                    match = re.search(r'/games/(\d+)', href)
                    if match:
                        place_id = match.group(1)
                        if place_id not in seen_ids:
                            seen_ids.add(place_id)
                            games.append({
                                "place_id": int(place_id),
                                "source": "roblox_discover"
                            })
                except Exception:
                    continue

        except Exception as e:
            print(f"Error scraping Roblox: {e}")
        finally:
            await browser.close()

    return games


async def main():
    """Main scraping function."""
    print("=" * 60)
    print("BloxPulse Game Discovery Scraper")
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print("=" * 60)

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_games = []

    # Scrape from multiple sources
    print("\n[1/2] Scraping RoMonitor Stats...")
    romonitor_games = await scrape_romonitor_stats()
    print(f"  Found {len(romonitor_games)} games from RoMonitor")
    all_games.extend(romonitor_games)

    print("\n[2/2] Scraping Roblox Discover...")
    roblox_games = await scrape_roblox_discover()
    print(f"  Found {len(roblox_games)} games from Roblox Discover")
    all_games.extend(roblox_games)

    # Save raw scraped data
    output_data = {
        "scraped_at": datetime.utcnow().isoformat(),
        "total_raw": len(all_games),
        "games": all_games
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n✓ Saved {len(all_games)} games to {OUTPUT_FILE}")
    print("Next step: Run validate_games.py to verify Universe IDs")


if __name__ == "__main__":
    asyncio.run(main())
