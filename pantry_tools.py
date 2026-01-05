"""
Shared PantryBot Tool Functions
Used by both HTTP server (Open WebUI) and MCP server (Claude Desktop)
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger("pantrybot")

# Configuration
GROCY_API_URL = os.getenv("GROCY_API_URL", "http://192.168.0.83:9283/api")
GROCY_API_KEY = os.getenv("GROCY_API_KEY", "")
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "")
RECIPE_DIR = Path(os.getenv("RECIPE_DIR", "/app/recipes"))

# Ensure recipe directory exists
RECIPE_DIR.mkdir(exist_ok=True, parents=True)


def get_grocy_headers() -> dict:
    """Get headers for Grocy API requests"""
    headers = {"accept": "application/json"}
    if GROCY_API_KEY:
        headers["GROCY-API-KEY"] = GROCY_API_KEY
    return headers


# ============================================================================
# GROCY PANTRY TOOLS
# ============================================================================

async def get_pantry_items(category: str = "all") -> Dict[str, Any]:
    """Get condensed pantry items from Grocy"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GROCY_API_URL}/stock",
                headers=get_grocy_headers(),
                timeout=10.0
            )
            response.raise_for_status()
            stock_data = response.json()

            condensed_items = []
            for item in stock_data:
                product = item.get("product", {})
                amount = float(item.get("amount_aggregated", 0))

                if amount <= 0:
                    continue

                # Apply filtering
                if category != "all":
                    if category == "expiring_soon":
                        best_before = item.get("best_before_date", "")
                        if best_before:
                            exp_date = datetime.strptime(best_before, "%Y-%m-%d")
                            if (exp_date - datetime.now()).days > 7:
                                continue
                    elif category == "low_stock":
                        min_stock = float(product.get("min_stock_amount", 0))
                        if amount >= min_stock:
                            continue
                    elif category.lower() not in product.get("name", "").lower():
                        continue

                condensed_items.append({
                    "name": product.get("name", "Unknown"),
                    "amount": amount,
                    "best_before": item.get("best_before_date", "N/A")
                })

            return {
                "success": True,
                "total_products": len(condensed_items),
                "items": condensed_items
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to fetch pantry items: {str(e)}"
            }


async def get_product_info(product_name: str) -> Dict[str, Any]:
    """Get detailed info about a specific product"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GROCY_API_URL}/stock",
                headers=get_grocy_headers(),
                timeout=10.0
            )
            response.raise_for_status()
            stock_data = response.json()

            matches = []
            for item in stock_data:
                product = item.get("product", {})
                name = product.get("name", "")

                if product_name.lower() in name.lower():
                    matches.append({
                        "name": name,
                        "amount": float(item.get("amount_aggregated", 0)),
                        "amount_opened": float(item.get("amount_opened_aggregated", 0)),
                        "best_before": item.get("best_before_date", "N/A"),
                        "min_stock_amount": product.get("min_stock_amount", 0)
                    })

            if matches:
                return {"found": True, "matches": matches}
            else:
                return {"found": False, "message": f"No products found matching '{product_name}'"}

        except Exception as e:
            return {"error": f"Failed to fetch product info: {str(e)}"}


async def find_product_id_by_name(product_name: str) -> Dict[str, Any]:
    """Helper function to find Grocy product ID by name"""
    async with httpx.AsyncClient() as client:
        try:
            # Get all products from Grocy
            response = await client.get(
                f"{GROCY_API_URL}/objects/products",
                headers=get_grocy_headers(),
                timeout=10.0
            )
            response.raise_for_status()
            products = response.json()

            # Search for matching product
            matches = []
            for product in products:
                name = product.get("name", "")
                if product_name.lower() in name.lower():
                    matches.append({
                        "id": product.get("id"),
                        "name": name
                    })

            if matches:
                return {"found": True, "matches": matches}
            else:
                return {"found": False, "message": f"No product found matching '{product_name}'"}

        except Exception as e:
            return {"error": f"Failed to search for product: {str(e)}"}


async def consume_stock(product_name: str, amount: float, spoiled: bool = False) -> Dict[str, Any]:
    """Consume/remove stock from Grocy inventory"""
    logger.info(f"🗑️ Consuming {amount} of '{product_name}' (spoiled: {spoiled})")

    # First, find the product ID
    product_search = await find_product_id_by_name(product_name)
    if not product_search.get("found"):
        return {"success": False, "error": f"Product '{product_name}' not found in Grocy"}

    matches = product_search.get("matches", [])
    if len(matches) > 1:
        # Multiple matches - let user know
        match_names = [m["name"] for m in matches]
        return {
            "success": False,
            "error": f"Multiple products found: {', '.join(match_names)}. Please be more specific."
        }

    product_id = matches[0]["id"]
    product_exact_name = matches[0]["name"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{GROCY_API_URL}/stock/products/{product_id}/consume",
                headers=get_grocy_headers(),
                json={
                    "amount": amount,
                    "spoiled": spoiled,
                    "transaction_type": "consume"
                },
                timeout=10.0
            )
            response.raise_for_status()

            logger.info(f"✅ Consumed {amount} of '{product_exact_name}' from inventory")

            return {
                "success": True,
                "message": f"Successfully consumed {amount} of '{product_exact_name}'",
                "product_name": product_exact_name,
                "amount": amount,
                "spoiled": spoiled
            }

        except Exception as e:
            logger.error(f"❌ Failed to consume stock: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to consume stock: {str(e)}"
            }


async def add_stock(product_name: str, amount: float, best_before_date: str = None, price: float = None) -> Dict[str, Any]:
    """Add stock to Grocy inventory"""
    logger.info(f"📦 Adding {amount} of '{product_name}' to inventory")

    # First, find the product ID
    product_search = await find_product_id_by_name(product_name)
    if not product_search.get("found"):
        return {"success": False, "error": f"Product '{product_name}' not found in Grocy"}

    matches = product_search.get("matches", [])
    if len(matches) > 1:
        match_names = [m["name"] for m in matches]
        return {
            "success": False,
            "error": f"Multiple products found: {', '.join(match_names)}. Please be more specific."
        }

    product_id = matches[0]["id"]
    product_exact_name = matches[0]["name"]

    async with httpx.AsyncClient() as client:
        try:
            # Build request body
            body = {
                "amount": amount,
                "transaction_type": "purchase"
            }

            if best_before_date:
                body["best_before_date"] = best_before_date

            if price is not None:
                body["price"] = price

            response = await client.post(
                f"{GROCY_API_URL}/stock/products/{product_id}/add",
                headers=get_grocy_headers(),
                json=body,
                timeout=10.0
            )
            response.raise_for_status()

            logger.info(f"✅ Added {amount} of '{product_exact_name}' to inventory")

            return {
                "success": True,
                "message": f"Successfully added {amount} of '{product_exact_name}' to inventory",
                "product_name": product_exact_name,
                "amount": amount,
                "best_before_date": best_before_date,
                "price": price
            }

        except Exception as e:
            logger.error(f"❌ Failed to add stock: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to add stock: {str(e)}"
            }


async def add_to_shopping_list(product_name: str, amount: float = 1) -> Dict[str, Any]:
    """Add item to Grocy shopping list"""
    logger.info(f"🛒 Adding {amount} of '{product_name}' to shopping list")

    # First, find the product ID
    product_search = await find_product_id_by_name(product_name)
    if not product_search.get("found"):
        return {"success": False, "error": f"Product '{product_name}' not found in Grocy"}

    matches = product_search.get("matches", [])
    if len(matches) > 1:
        match_names = [m["name"] for m in matches]
        return {
            "success": False,
            "error": f"Multiple products found: {', '.join(match_names)}. Please be more specific."
        }

    product_id = matches[0]["id"]
    product_exact_name = matches[0]["name"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{GROCY_API_URL}/stock/products/{product_id}/add-to-shopping-list",
                headers=get_grocy_headers(),
                json={
                    "product_id": product_id,
                    "amount": amount
                },
                timeout=10.0
            )
            response.raise_for_status()

            logger.info(f"✅ Added '{product_exact_name}' to shopping list")

            return {
                "success": True,
                "message": f"Added {amount} of '{product_exact_name}' to shopping list",
                "product_name": product_exact_name,
                "amount": amount
            }

        except Exception as e:
            logger.error(f"❌ Failed to add to shopping list: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to add to shopping list: {str(e)}"
            }


async def get_shopping_list() -> Dict[str, Any]:
    """Get current shopping list from Grocy"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GROCY_API_URL}/objects/shopping_list",
                headers=get_grocy_headers(),
                timeout=10.0
            )
            response.raise_for_status()
            shopping_list = response.json()

            items = []
            for item in shopping_list:
                items.append({
                    "product_id": item.get("product_id"),
                    "amount": item.get("amount"),
                    "note": item.get("note", "")
                })

            logger.info(f"✅ Retrieved shopping list with {len(items)} items")

            return {
                "success": True,
                "total_items": len(items),
                "items": items
            }

        except Exception as e:
            logger.error(f"❌ Failed to get shopping list: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get shopping list: {str(e)}"
            }


# ============================================================================
# RECIPE TOOLS
# ============================================================================

async def search_recipes_by_ingredients(ingredients: str, number: int = 5) -> Dict[str, Any]:
    """Search for recipes using available ingredients via Spoonacular API"""
    if not SPOONACULAR_API_KEY:
        return {"error": "Spoonacular API key not configured"}

    logger.info(f"🔍 Searching Spoonacular for recipes with: {ingredients}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.spoonacular.com/recipes/findByIngredients",
                params={
                    "apiKey": SPOONACULAR_API_KEY,
                    "ingredients": ingredients,
                    "number": number,
                    "ranking": 2,  # Maximize used ingredients
                    "ignorePantry": False
                },
                timeout=10.0
            )
            response.raise_for_status()
            recipes = response.json()

            # Simplify the response and calculate match percentage
            simplified = []
            for recipe in recipes:
                used_count = len(recipe.get("usedIngredients", []))
                missed_count = len(recipe.get("missedIngredients", []))
                total_ingredients = used_count + missed_count

                # Calculate match percentage
                match_percentage = round((used_count / total_ingredients * 100) if total_ingredients > 0 else 0, 1)

                # Get names of missing ingredients
                missed_items = [ing.get("name") for ing in recipe.get("missedIngredients", [])]

                simplified.append({
                    "id": recipe.get("id"),
                    "title": recipe.get("title"),
                    "image": recipe.get("image"),
                    "used_ingredients": used_count,
                    "missed_ingredients": missed_count,
                    "match_percentage": match_percentage,
                    "missed_items": missed_items
                })

            # Sort by match percentage (highest first)
            simplified.sort(key=lambda x: x["match_percentage"], reverse=True)

            logger.info(f"✅ Found {len(simplified)} recipes from Spoonacular (sorted by match %)")

            return {
                "success": True,
                "total_recipes": len(simplified),
                "recipes": simplified
            }

        except Exception as e:
            logger.error(f"❌ Spoonacular search failed: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to search recipes: {str(e)}"
            }


async def get_recipe_details(recipe_id: int) -> Dict[str, Any]:
    """Get full recipe details including instructions from Spoonacular"""
    if not SPOONACULAR_API_KEY:
        return {"error": "Spoonacular API key not configured"}

    logger.info(f"📖 Getting recipe details for ID: {recipe_id}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://api.spoonacular.com/recipes/{recipe_id}/information",
                params={
                    "apiKey": SPOONACULAR_API_KEY,
                    "includeNutrition": False
                },
                timeout=10.0
            )
            response.raise_for_status()
            recipe = response.json()

            # Extract key information
            ingredients = []
            for ing in recipe.get("extendedIngredients", []):
                ingredients.append(ing.get("original", ""))

            instructions = []
            if recipe.get("analyzedInstructions"):
                for step in recipe["analyzedInstructions"][0].get("steps", []):
                    instructions.append(f"{step.get('number')}. {step.get('step')}")
            elif recipe.get("instructions"):
                instructions = [recipe.get("instructions")]

            logger.info(f"✅ Retrieved recipe: {recipe.get('title')} ({len(ingredients)} ingredients, {len(instructions)} steps)")

            return {
                "success": True,
                "title": recipe.get("title"),
                "servings": recipe.get("servings"),
                "ready_in_minutes": recipe.get("readyInMinutes"),
                "ingredients": ingredients,
                "instructions": instructions,
                "source_url": recipe.get("sourceUrl")
            }

        except Exception as e:
            logger.error(f"❌ Failed to get recipe details: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get recipe details: {str(e)}"
            }


async def save_recipe(recipe_name: str, recipe_content: str) -> Dict[str, Any]:
    """Save a recipe to filesystem"""
    safe_name = recipe_name.lower().replace(" ", "_").replace("/", "_")
    if not safe_name.endswith(".txt"):
        safe_name += ".txt"

    recipe_path = RECIPE_DIR / safe_name

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_content = f"""# {recipe_name.title()}
# Created: {timestamp}
# Source: PantryBot

{recipe_content}
"""
        recipe_path.write_text(full_content, encoding="utf-8")

        return {
            "success": True,
            "message": "Recipe saved successfully",
            "file_path": str(recipe_path),
            "recipe_name": recipe_name
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to save recipe: {str(e)}"
        }


async def get_recipe(recipe_name: str) -> Dict[str, Any]:
    """Read a recipe from filesystem"""
    safe_name = recipe_name.lower().replace(" ", "_")
    if not safe_name.endswith(".txt"):
        safe_name += ".txt"

    recipe_path = RECIPE_DIR / safe_name

    try:
        if recipe_path.exists():
            content = recipe_path.read_text(encoding="utf-8")
            return {
                "success": True,
                "recipe_name": recipe_name,
                "content": content
            }
        else:
            available = [f.stem.replace("_", " ").title()
                        for f in RECIPE_DIR.glob("*.txt")]
            return {
                "success": False,
                "error": f"Recipe '{recipe_name}' not found",
                "available_recipes": available
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to read recipe: {str(e)}"
        }


async def list_recipes() -> Dict[str, Any]:
    """List all saved recipes"""
    try:
        recipes = []
        if RECIPE_DIR.exists():
            for recipe_file in sorted(RECIPE_DIR.glob("*.txt")):
                stat = recipe_file.stat()
                recipes.append({
                    "name": recipe_file.stem.replace("_", " ").title(),
                    "filename": recipe_file.name,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                })

        return {
            "success": True,
            "total_recipes": len(recipes),
            "recipes": recipes
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list recipes: {str(e)}"
        }
