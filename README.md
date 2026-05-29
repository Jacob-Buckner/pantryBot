# PantryBot v2

Local-first pantry and recipe manager. No cloud, no Docker, no external APIs — just Python and SQLite running on your Mac.

> **Looking for the Grocy-backed MCP server?** That's archived at the [v1.0.0 tag](../../releases/tag/v1.0.0).

## What it does

- Track pantry ingredients with quantities, units, best-by dates, and categories
- Browse recipes and see at a glance which ones you can make right now
- Generate a shopping list for ingredients you're short on
- Mark a recipe as made and auto-deduct ingredients from stock

## Requirements

- Python 3.10+
- macOS (tested on M-series)

## Quick start

```bash
# 1. Create a virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Launch — creates data/pantrybot.db automatically on first run
python app.py

# 3. Open http://127.0.0.1:5000
```

## Load example recipes

```bash
python seed.py                           # loads seed_data/example_recipes.json
python seed.py path/to/my_recipes.json  # loads a custom file
```

See `seed_data/example_recipes.json` for the expected JSON format.

## Project layout

```
app.py                  Flask app — all routes
db.py                   SQLite schema + connection helper
seed.py                 Import recipes from a JSON file
requirements.txt

data/
  pantrybot.db          SQLite database (auto-created, gitignored)

static/
  style.css             Hand-written CSS, no build step

templates/
  base.html             Shared layout and nav
  pantry.html           / — pantry view
  recipes.html          /recipes — recipe list
  recipe_detail.html    /recipes/<id>
  recipe_form.html      /recipes/new and /recipes/<id>/edit
  shopping.html         /shopping — shopping list

seed_data/
  example_recipes.json  Sample data for seed.py
```

## Units

Weight units: `g`, `kg`, `oz`, `lb`. Countable items (eggs, cans, etc.) use `count`.
No unit conversion is performed — amounts are compared directly, so keep units consistent between your pantry and your recipes.

## LLM / chat features

Planned for v2.0.0 final. See `ROADMAP.md`.
