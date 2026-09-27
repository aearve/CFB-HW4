# HW4 - FBS Team Ratings

## File to look at

**`CFB_TeamRatings_HW4.ipynb`** - this is the whole assignment in one notebook: all three
models (Part 1), and both evaluation studies (Parts 2 and 3).

**This notebook has already been run in full - you don't need to run anything to see the
results.** All outputs (top 10/bottom 10 tables, evaluation results, interpretation write-ups)
are saved in the file itself, so opening it on GitHub or in Jupyter/VS Code shows everything as
already-executed. The instructions below are only if you want to re-run it yourself to verify
the code - in that case, be aware Step 4 will take several minutes on a fresh run (see below for
why).

## How to run it (optional - only if you want to re-run it yourself)

1. Install dependencies: `pip install pandas numpy requests statsmodels scipy python-dotenv`
2. Get a free CFBD API key at https://collegefootballdata.com/key and put it in a `.env` file in
   this folder: `CFBD_API_KEY=your_key_here`
3. Open `CFB_TeamRatings_HW4.ipynb` in Jupyter/VS Code and Run All.
   - Steps 1, 2, and 4 fetch and cache to CSV automatically, the same pattern as HW2. Steps 2 and
     4 fire several API requests concurrently (a thread pool) instead of one at a time, since
     each request is almost entirely spent waiting on the network rather than computing - this
     gave roughly a 10-15x speedup over a plain sequential loop in testing.
   - **Step 4 (win probability) is still the slowest one.** I checked CFBD's own API docs - their
     win probability endpoint genuinely has no bulk option, it's one HTTP request per game, and
     there are ~3,700 FBS games across 2021-2025. No amount of batching gets around that; this
     run can take several minutes even with concurrency. It saves its progress to `wp_by_game.csv`
     as each game finishes, so it's completely safe to stop (Ctrl+C / interrupt) and re-run - it
     only fetches the games still missing, and usually a rerun or two mops up anything that got
     rate-limited.
   - **If you'd rather not sit there watching the cell:** run `fetch_win_probability.py` from a
     terminal instead (`python3 fetch_win_probability.py`, after running Step 1 once so
     `games_fbs.csv` exists). It's the same fetch, just outside Jupyter, so you can leave it
     running in the background - switch to something else, or close the notebook entirely - and
     come back later. It writes to the same `wp_by_game.csv`, so when you do run Step 4 in the
     notebook, it'll see the games are already cached and finish almost instantly.

## Data

Nothing is committed to GitHub - `games_fbs.csv`, `plays_fbs.csv`, and `wp_by_game.csv` are all
fetched live from CFBD and cached locally only (see `.gitignore`).

## What's in the notebook

- **Part 1 (30 pts):** three opponent-adjusted rating models - SRS (final score margin), Game
  Control (average in-game scoring margin), and AWP (average in-game win probability) - each
  with a home-field-advantage term, fit separately per season, 2021-2025. Top 10 / bottom 10
  tables for every model/season combination.
- **Part 2 (20 pts):** predictive out-of-sample comparison, using a chronological (early
  weeks train / later weeks test) split per season, with the reasoning for that split explained
  in the notebook.
- **Part 3 (20 pts):** repeatability comparison, using a random split-half per season, with the
  reasoning for that split explained in the notebook.

The interpretation write-ups after Parts 2 and 3 are already filled in with the actual results
from the final run.
