"""
Standalone script to pre-fetch win probability data for HW4's AWP metric.

WHY THIS EXISTS: I checked CFBD's own API docs, and their /metrics/wp endpoint (in-game win
probability, which the AWP model is built from) has no bulk option - it's genuinely one HTTP
request per game, no way around it, and there are ~3,700 FBS games across 2021-2025. No amount
of clever batching changes that; the only real lever is how many requests run at once, and going
too high trips CFBD's (undocumented) rate limiter. So this will always take several minutes -
this script's only job is to make that wait happen somewhere that isn't a blocking Jupyter cell.

HOW TO RUN IT:
1. Run Step 1 in the notebook first (just that cell) so games_fbs.csv exists in this folder -
   that's the list of games this script needs to fetch win probability for.
2. Open a terminal in this folder and run:  python3 fetch_win_probability.py
3. Leave it running - you can keep working in the notebook on something else, switch to another
   app, or just let the terminal sit in the background. It prints progress as it goes.
4. When it's done (or even partway done), go back to the notebook and run Step 4 as normal - it
   reads the same wp_by_game.csv this script writes to, so it'll see the games are already
   cached and finish almost instantly instead of re-fetching anything.

Safe to Ctrl+C and re-run any time - it only fetches games still missing from wp_by_game.csv.
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
MAX_WORKERS = 12


def _load_dotenv(path=HERE / ".env"):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


def get_api_key():
    key = os.environ.get("CFBD_API_KEY")
    if not key:
        sys.exit("CFBD_API_KEY not found. Put it in a .env file in this folder: CFBD_API_KEY=your_key_here")
    return key


def cfbd_get(path, params=None, max_attempts=3):
    url = f"https://api.collegefootballdata.com{path}"
    headers = {"Authorization": f"Bearer {get_api_key()}"}
    for attempt in range(max_attempts):
        resp = requests.get(url, headers=headers, params=params or {})
        if resp.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code != 200:
            raise RuntimeError(f"CFBD {path} {params} failed: {resp.status_code} {resp.text[:200]}")
        return resp.json()
    raise RuntimeError(f"CFBD {path} {params} failed after {max_attempts} attempts (rate limited)")


def fetch_wp(game_id):
    try:
        wp_plays = cfbd_get("/metrics/wp", {"gameId": game_id})
    except RuntimeError as e:
        return game_id, None, str(e)
    if not wp_plays:
        return game_id, None, None
    avg_wp_home = float(np.mean([p.get("homeWinProbability") for p in wp_plays
                                  if p.get("homeWinProbability") is not None]))
    return game_id, avg_wp_home, None


def main():
    games_path = HERE / "games_fbs.csv"
    if not games_path.exists():
        sys.exit(f"{games_path.name} not found - run Step 1 in the notebook first, then re-run this script.")
    games = pd.read_csv(games_path)

    wp_path = HERE / "wp_by_game.csv"
    if wp_path.exists():
        wp_cache = pd.read_csv(wp_path)
    else:
        wp_cache = pd.DataFrame(columns=["game_id", "avg_wp_home"])
        wp_cache.to_csv(wp_path, index=False)

    already_done = set(wp_cache["game_id"])
    remaining = [gid for gid in games["game_id"] if gid not in already_done]
    print(f"{len(already_done)} games already cached, {len(remaining)} left to fetch", flush=True)
    if not remaining:
        print("Nothing left to do - wp_by_game.csv is already complete.")
        return

    t0 = time.time()
    fetched, errors = 0, 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_wp, gid): gid for gid in remaining}
        for future in as_completed(futures):
            game_id, avg_wp_home, err = future.result()
            if err is not None:
                errors += 1
                continue
            if avg_wp_home is not None:
                row = pd.DataFrame([{"game_id": game_id, "avg_wp_home": avg_wp_home}])
                row.to_csv(wp_path, mode="a", header=False, index=False)
            fetched += 1
            if (fetched + errors) % 50 == 0:
                elapsed = time.time() - t0
                print(f"  {fetched + errors} of {len(remaining)} done "
                      f"({fetched} fetched, {errors} rate-limited) - {elapsed:.0f}s elapsed", flush=True)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s: {fetched} fetched, {errors} rate-limited/failed this run.")
    if errors:
        print(f"Just run this script again to pick up the {errors} that got skipped - "
              f"it only retries what's missing.")


if __name__ == "__main__":
    main()
