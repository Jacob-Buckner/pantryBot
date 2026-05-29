#!/usr/bin/env python3
"""
Seed PantryBot with recipes from a JSON file.

Usage:
    python seed.py                            # loads seed_data/example_recipes.json
    python seed.py path/to/my_recipes.json   # loads a custom file

JSON format:
    [
      {
        "name": "Recipe Name",
        "servings": 4,
        "prep_minutes": 30,
        "notes": "Optional notes",
        "instructions": "Markdown text",
        "ingredients": [
          {"name": "Eggs", "amount": 4, "unit": "count"},
          {"name": "Flour", "amount": 200, "unit": "g"}
        ]
      }
    ]
"""

import json
import sys
from pathlib import Path
import db


def seed(json_path: Path) -> None:
    db.init_db()
    conn = db.get_db()

    data = json.loads(json_path.read_text(encoding="utf-8"))
    recipes_data = data if isinstance(data, list) else data.get("recipes", [])

    loaded = 0
    skipped = 0

    for r in recipes_data:
        name = r.get("name", "").strip()
        if not name:
            skipped += 1
            continue

        existing = conn.execute(
            "SELECT id FROM recipes WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()

        if existing:
            print(f"  ~ skipping '{name}' (already exists)")
            skipped += 1
            continue

        cur = conn.execute(
            """INSERT INTO recipes (name, instructions, servings, prep_minutes, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (
                name,
                r.get("instructions", ""),
                int(r.get("servings", 4)),
                int(r.get("prep_minutes", 0)),
                r.get("notes") or None,
            ),
        )
        recipe_id = cur.lastrowid

        for ing in r.get("ingredients", []):
            ing_name = ing["name"].strip()
            amount = float(ing["amount"])
            unit = ing.get("unit", "count").strip() or "count"

            existing_ing = conn.execute(
                "SELECT id FROM ingredients WHERE LOWER(name) = LOWER(?)", (ing_name,)
            ).fetchone()

            if existing_ing:
                ingredient_id = existing_ing["id"]
            else:
                cur2 = conn.execute(
                    "INSERT INTO ingredients (name, quantity, unit) VALUES (?, 0, ?)",
                    (ing_name, unit),
                )
                ingredient_id = cur2.lastrowid

            conn.execute(
                """INSERT OR REPLACE INTO recipe_ingredients
                   (recipe_id, ingredient_id, amount, unit) VALUES (?, ?, ?, ?)""",
                (recipe_id, ingredient_id, amount, unit),
            )

        print(f"  + {name}")
        loaded += 1

    conn.commit()
    conn.close()
    print(f"\nDone — {loaded} loaded, {skipped} skipped.")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("seed_data/example_recipes.json")
    if not path.exists():
        print(f"Error: file not found: {path}")
        sys.exit(1)
    print(f"Seeding from {path} ...\n")
    seed(path)
