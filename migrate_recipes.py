#!/usr/bin/env python3
"""
Migrate filesystem recipes to Grocy database
Run: python3 migrate_recipes.py
"""
import os
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GROCY_API_URL = os.getenv("GROCY_API_URL", "http://localhost:9283/api")
GROCY_API_KEY = os.getenv("GROCY_API_KEY", "")
RECIPE_DIR = Path("./data/recipes")


def get_grocy_headers():
    return {
        "GROCY-API-KEY": GROCY_API_KEY,
        "accept": "application/json"
    }


async def migrate_recipes():
    """Migrate all .txt recipes from filesystem to Grocy"""
    if not RECIPE_DIR.exists():
        print(f"❌ Recipe directory not found: {RECIPE_DIR}")
        return

    recipe_files = list(RECIPE_DIR.glob("*.txt"))
    if not recipe_files:
        print("📭 No recipes found to migrate")
        return

    print(f"📚 Found {len(recipe_files)} recipes to migrate\n")

    async with httpx.AsyncClient() as client:
        for recipe_file in recipe_files:
            try:
                # Read recipe content
                content = recipe_file.read_text(encoding="utf-8")

                # Extract name (remove .txt, replace _ with space, title case)
                name = recipe_file.stem.replace("_", " ").title()

                # Create recipe in Grocy
                recipe_data = {
                    "name": name,
                    "description": f"Migrated from filesystem\n\n{content}",
                    "base_servings": 4,
                    "desired_servings": 4,
                    "type": "normal"
                }

                response = await client.post(
                    f"{GROCY_API_URL}/objects/recipes",
                    headers=get_grocy_headers(),
                    json=recipe_data,
                    timeout=10.0
                )

                if response.status_code == 200:
                    result = response.json()
                    recipe_id = result.get("created_object_id")
                    print(f"✅ Migrated: {name} (Grocy ID: {recipe_id})")
                else:
                    print(f"❌ Failed to migrate {name}: HTTP {response.status_code}")

            except Exception as e:
                print(f"❌ Error migrating {recipe_file.name}: {str(e)}")

    print(f"\n✨ Migration complete!")
    print(f"💡 Tip: Filesystem recipes are still in {RECIPE_DIR} (not deleted)")


if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate_recipes())
