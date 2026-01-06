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
        # Auto-create the product if it doesn't exist
        logger.info(f"🆕 Product '{product_name}' not found, creating it...")
        create_result = await create_product(product_name)

        if not create_result.get("success"):
            return {"success": False, "error": f"Product '{product_name}' not found and could not be created: {create_result.get('error')}"}

        # Re-search for the newly created product
        product_search = await find_product_id_by_name(product_name)
        if not product_search.get("found"):
            return {"success": False, "error": f"Product '{product_name}' was created but could not be found"}

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
                    "usedIngredients": used_count,
                    "matchPercentage": match_percentage,
                    "missedIngredients": missed_items
                })

            # Sort by match percentage (highest first)
            simplified.sort(key=lambda x: x["matchPercentage"], reverse=True)

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
                "image": recipe.get("image"),
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


async def search_recipes_by_name(query: str, number: int = 5) -> Dict[str, Any]:
    """Search for recipes by name/query via Spoonacular API"""
    if not SPOONACULAR_API_KEY:
        return {"error": "Spoonacular API key not configured"}

    logger.info(f"🔍 Searching Spoonacular for recipe: '{query}'")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.spoonacular.com/recipes/complexSearch",
                params={
                    "apiKey": SPOONACULAR_API_KEY,
                    "query": query,
                    "number": number,
                    "addRecipeInformation": True,
                    "fillIngredients": True,
                    "instructionsRequired": True
                },
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            recipes = data.get("results", [])

            # Simplify the response - format compatible with find_recipes for consistent UI
            simplified = []
            for recipe in recipes:
                simplified.append({
                    "id": recipe.get("id"),
                    "title": recipe.get("title"),
                    "image": recipe.get("image"),
                    "readyInMinutes": recipe.get("readyInMinutes"),
                    "servings": recipe.get("servings"),
                    # Add fields for frontend compatibility (no pantry comparison for name search)
                    "matchPercentage": 100,  # Name search means exact match
                    "usedIngredients": 0,  # Not comparing to pantry
                    "missedIngredients": []  # Unknown without pantry check
                })

            logger.info(f"✅ Found {len(simplified)} recipes for '{query}'")

            return {
                "success": True,
                "total_recipes": len(simplified),
                "recipes": simplified
            }

        except Exception as e:
            logger.error(f"❌ Recipe name search failed: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to search recipes: {str(e)}"
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


async def save_recipe_to_grocy(
    recipe_id: int,
    recipe_title: str,
    servings: int = 4,
    ready_in_minutes: int = 30,
    ingredients: list = None,
    instructions: list = None,
    image_url: str = None
) -> Dict[str, Any]:
    """
    Save a Spoonacular recipe to Grocy's recipe system with full integration.
    Auto-creates missing products at 0 quantity for shopping list integration.
    """
    if not GROCY_API_KEY:
        return {"success": False, "error": "Grocy API key not configured"}

    logger.info(f"💾 Saving recipe '{recipe_title}' to Grocy...")

    async with httpx.AsyncClient() as client:
        try:
            # 1. Create the recipe in Grocy
            recipe_data = {
                "name": recipe_title,
                "description": f"From Spoonacular (ID: {recipe_id})\nCook time: {ready_in_minutes} min\nServings: {servings}",
                "base_servings": servings,
                "desired_servings": servings,
                "type": "normal"
            }

            # Add image URL to description if provided
            if image_url:
                recipe_data["description"] += f"\n\nImage: {image_url}"

            # Add instructions to description
            if instructions:
                recipe_data["description"] += "\n\nInstructions:\n" + "\n".join(instructions)

            recipe_response = await client.post(
                f"{GROCY_API_URL}/objects/recipes",
                headers=get_grocy_headers(),
                json=recipe_data,
                timeout=10.0
            )
            recipe_response.raise_for_status()
            grocy_recipe = recipe_response.json()
            grocy_recipe_id = grocy_recipe.get("created_object_id")

            logger.info(f"✅ Created recipe in Grocy (ID: {grocy_recipe_id})")

            # 2. Process ingredients and create missing products
            created_products = []
            if ingredients:
                for idx, ingredient in enumerate(ingredients):
                    # Try to find existing product
                    product_search = await find_product_id_by_name(ingredient)

                    if not product_search.get("found"):
                        # Product doesn't exist - create it at 0 quantity
                        logger.info(f"🆕 Creating missing product: {ingredient}")
                        create_result = await create_product(ingredient, location="Pantry", quantity_unit="piece")

                        if create_result.get("success"):
                            created_products.append(ingredient)
                            # Re-search to get the new product ID
                            product_search = await find_product_id_by_name(ingredient)

                    # Add ingredient to recipe (if we have a product ID)
                    if product_search.get("found"):
                        product_id = product_search.get("product_id")

                        # Create recipe ingredient link
                        recipe_pos_data = {
                            "recipe_id": grocy_recipe_id,
                            "product_id": product_id,
                            "amount": 1,  # Default amount (Grocy uses generic units)
                            "note": ingredient,  # Store original ingredient text
                            "ingredient_group": "",
                            "product_group": idx + 1  # Position in recipe
                        }

                        await client.post(
                            f"{GROCY_API_URL}/objects/recipes_pos",
                            headers=get_grocy_headers(),
                            json=recipe_pos_data,
                            timeout=10.0
                        )

            logger.info(f"✅ Recipe saved to Grocy with {len(ingredients or [])} ingredients")
            if created_products:
                logger.info(f"🆕 Created {len(created_products)} new products: {', '.join(created_products)}")

            return {
                "success": True,
                "message": f"Recipe '{recipe_title}' saved to Grocy",
                "grocy_recipe_id": grocy_recipe_id,
                "created_products": created_products,
                "total_ingredients": len(ingredients or [])
            }

        except Exception as e:
            logger.error(f"❌ Failed to save recipe to Grocy: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to save recipe: {str(e)}"
            }


async def get_grocy_recipes() -> Dict[str, Any]:
    """Get all recipes from Grocy database"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GROCY_API_URL}/objects/recipes",
                headers=get_grocy_headers(),
                timeout=10.0
            )
            response.raise_for_status()
            recipes = response.json()

            # Extract image URLs from descriptions
            simplified = []
            for recipe in recipes:
                description = recipe.get("description", "")

                # Extract image URL if present
                image_url = None
                if "Image: " in description:
                    lines = description.split("\n")
                    for line in lines:
                        if line.startswith("Image: "):
                            image_url = line.replace("Image: ", "").strip()
                            break

                simplified.append({
                    "id": recipe.get("id"),
                    "name": recipe.get("name"),
                    "description": description,
                    "servings": recipe.get("base_servings"),
                    "image_url": image_url
                })

            return {
                "success": True,
                "total_recipes": len(simplified),
                "recipes": simplified
            }

        except Exception as e:
            logger.error(f"❌ Failed to get Grocy recipes: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to fetch recipes: {str(e)}"
            }


async def get_grocy_recipe_by_id(recipe_id: int) -> Dict[str, Any]:
    """Get a specific recipe from Grocy by ID"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GROCY_API_URL}/objects/recipes/{recipe_id}",
                headers=get_grocy_headers(),
                timeout=10.0
            )
            response.raise_for_status()
            recipe = response.json()

            return {
                "success": True,
                "recipe": recipe
            }

        except Exception as e:
            logger.error(f"❌ Failed to get Grocy recipe: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to fetch recipe: {str(e)}"
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
"""
Extended Grocy API Tools
Additional convenience functions for chores, tasks, batteries, and more
"""

import httpx
from typing import Dict, Any, Optional
from pantry_tools import get_grocy_headers, GROCY_API_URL


# ============================================================================
# GENERIC GROCY API ACCESS
# ============================================================================

async def grocy_api(
    endpoint: str,
    method: str = "GET",
    body: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generic Grocy API access for any endpoint.

    Common endpoints:
    - /stock - Current stock
    - /objects/chores - List chores
    - /chores/{id}/execute - Complete chore
    - /objects/batteries - List batteries
    - /batteries/{id}/charge - Charge battery
    - /objects/tasks - List tasks
    - /tasks/{id}/complete - Complete task
    - /objects/products - List all products
    - /objects/locations - List storage locations
    - /objects/quantity_units - List units
    - And 50+ more...

    Args:
        endpoint: API endpoint (e.g., "/objects/chores")
        method: HTTP method (GET, POST, PUT, DELETE)
        body: Optional request body for POST/PUT

    Returns:
        JSON response from Grocy API
    """
    url = f"{GROCY_API_URL}{endpoint}"

    async with httpx.AsyncClient() as client:
        try:
            if method == "GET":
                response = await client.get(url, headers=get_grocy_headers(), timeout=10.0)
            elif method == "POST":
                response = await client.post(url, headers=get_grocy_headers(), json=body, timeout=10.0)
            elif method == "PUT":
                response = await client.put(url, headers=get_grocy_headers(), json=body, timeout=10.0)
            elif method == "DELETE":
                response = await client.delete(url, headers=get_grocy_headers(), timeout=10.0)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}

            if response.status_code >= 400:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }

            # Return raw JSON (Claude will interpret it)
            if response.text:
                return response.json()
            else:
                return {"success": True, "status_code": response.status_code}

        except Exception as e:
            return {
                "success": False,
                "error": f"Grocy API error: {str(e)}"
            }


# ============================================================================
# CHORE MANAGEMENT
# ============================================================================

async def get_chores_status() -> Dict[str, Any]:
    """
    Get all chores with their status and next execution time.
    Shows which chores are due or overdue.
    """
    return await grocy_api("/chores")


async def complete_chore(chore_name: str) -> Dict[str, Any]:
    """
    Mark a chore as completed.

    Args:
        chore_name: Name of the chore (e.g., "Clean bathroom")

    Returns:
        Success confirmation with next execution time
    """
    # First, find the chore by name
    chores_response = await grocy_api("/objects/chores")

    if not chores_response or "success" in chores_response and not chores_response["success"]:
        return chores_response

    # Search for chore by name (case-insensitive)
    chore = None
    for c in chores_response:
        if c.get("name", "").lower() == chore_name.lower():
            chore = c
            break

    if not chore:
        return {
            "success": False,
            "error": f"Chore '{chore_name}' not found",
            "available_chores": [c.get("name") for c in chores_response]
        }

    # Execute the chore
    result = await grocy_api(
        f"/chores/{chore['id']}/execute",
        method="POST",
        body={"tracked_time": None, "done_by": None}
    )

    if "success" in result and not result["success"]:
        return result

    return {
        "success": True,
        "message": f"Completed chore: {chore['name']}",
        "chore_id": chore["id"]
    }


async def add_chore(
    name: str,
    period_days: int = 7,
    assignment_type: str = "no-assignment"
) -> Dict[str, Any]:
    """
    Add a new recurring chore.

    Args:
        name: Chore name (e.g., "Water plants")
        period_days: How often (in days) the chore repeats (default: 7)
        assignment_type: "no-assignment", "in-alphabetical-order", or "random"

    Returns:
        Success confirmation with chore ID
    """
    chore_data = {
        "name": name,
        "period_type": "daily",
        "period_days": period_days,
        "assignment_type": assignment_type,
        "assignment_config": None,
        "next_execution_assigned_to_user_id": None,
        "track_date_only": False,
        "rollover": False,
        "consume_product_on_execution": False,
        "product_id": None,
        "product_amount": None
    }

    result = await grocy_api("/objects/chores", method="POST", body=chore_data)

    if "success" in result and not result["success"]:
        return result

    return {
        "success": True,
        "message": f"Added chore: {name} (repeats every {period_days} days)",
        "chore_id": result.get("created_object_id")
    }


# ============================================================================
# TASK MANAGEMENT
# ============================================================================

async def get_pending_tasks() -> Dict[str, Any]:
    """
    Get all tasks that are not yet completed.
    """
    all_tasks = await grocy_api("/tasks")

    if "success" in all_tasks and not all_tasks["success"]:
        return all_tasks

    # Filter for incomplete tasks (Grocy /tasks endpoint already returns only incomplete)
    return {
        "success": True,
        "tasks": all_tasks,
        "total_pending": len(all_tasks) if isinstance(all_tasks, list) else 0
    }


async def complete_task(task_name: str) -> Dict[str, Any]:
    """
    Mark a task as completed.

    Args:
        task_name: Name of the task

    Returns:
        Success confirmation
    """
    # Get all tasks
    tasks_response = await grocy_api("/objects/tasks")

    if not tasks_response or "success" in tasks_response and not tasks_response["success"]:
        return tasks_response

    # Find task by name (case-insensitive)
    task = None
    for t in tasks_response:
        if t.get("name", "").lower() == task_name.lower():
            task = t
            break

    if not task:
        return {
            "success": False,
            "error": f"Task '{task_name}' not found",
            "available_tasks": [t.get("name") for t in tasks_response if not t.get("done")]
        }

    # Complete the task
    result = await grocy_api(f"/tasks/{task['id']}/complete", method="POST")

    if "success" in result and not result["success"]:
        return result

    return {
        "success": True,
        "message": f"Completed task: {task['name']}",
        "task_id": task["id"]
    }


async def add_task(name: str, due_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Add a new task to the task list.

    Args:
        name: Task description
        due_date: Optional due date in YYYY-MM-DD format

    Returns:
        Success confirmation with task ID
    """
    task_data = {
        "name": name,
        "due_date": due_date,
        "done": False
    }

    result = await grocy_api("/objects/tasks", method="POST", body=task_data)

    if "success" in result and not result["success"]:
        return result

    return {
        "success": True,
        "message": f"Added task: {name}",
        "task_id": result.get("created_object_id")
    }


# ============================================================================
# BATTERY MANAGEMENT
# ============================================================================

async def get_batteries_status() -> Dict[str, Any]:
    """
    Get all batteries with their charge status.
    Shows which batteries need charging based on last charge cycle.
    """
    return await grocy_api("/batteries")


async def charge_battery(battery_name: str) -> Dict[str, Any]:
    """
    Track a battery charge cycle.

    Args:
        battery_name: Name of the battery (e.g., "TV Remote")

    Returns:
        Success confirmation with next charge date
    """
    # Get all batteries
    batteries_response = await grocy_api("/objects/batteries")

    if not batteries_response or "success" in batteries_response and not batteries_response["success"]:
        return batteries_response

    # Find battery by name (case-insensitive)
    battery = None
    for b in batteries_response:
        if b.get("name", "").lower() == battery_name.lower():
            battery = b
            break

    if not battery:
        return {
            "success": False,
            "error": f"Battery '{battery_name}' not found",
            "available_batteries": [b.get("name") for b in batteries_response]
        }

    # Track charge cycle
    result = await grocy_api(
        f"/batteries/{battery['id']}/charge",
        method="POST",
        body={"tracked_time": None}
    )

    if "success" in result and not result["success"]:
        return result

    return {
        "success": True,
        "message": f"Tracked charge for battery: {battery['name']}",
        "battery_id": battery["id"]
    }


# ============================================================================
# PRODUCT CREATION
# ============================================================================

async def create_product(
    name: str,
    location: str = "Pantry",
    quantity_unit: str = "piece",
    min_stock_amount: int = 0
) -> Dict[str, Any]:
    """
    Create a new product in Grocy.
    Automatically creates it if it doesn't exist when adding stock.

    Args:
        name: Product name
        location: Storage location (default: "Pantry")
        quantity_unit: Unit of measurement (default: "piece")
        min_stock_amount: Minimum stock level for warnings (default: 0)

    Returns:
        Success confirmation with product ID
    """
    # First, get or create location
    locations = await grocy_api("/objects/locations")
    location_id = None

    if isinstance(locations, list):
        for loc in locations:
            if loc.get("name", "").lower() == location.lower():
                location_id = loc["id"]
                break

    if not location_id:
        # Create location
        loc_result = await grocy_api(
            "/objects/locations",
            method="POST",
            body={"name": location, "description": "Auto-created by PantryBot"}
        )
        location_id = loc_result.get("created_object_id", 1)

    # Get or create quantity unit
    units = await grocy_api("/objects/quantity_units")
    unit_id = None

    if isinstance(units, list):
        for unit in units:
            if unit.get("name", "").lower() == quantity_unit.lower():
                unit_id = unit["id"]
                break

    if not unit_id:
        # Use default unit (1) if not found
        unit_id = 1

    # Create product
    product_data = {
        "name": name,
        "location_id": location_id,
        "qu_id_purchase": unit_id,
        "qu_id_stock": unit_id,
        "min_stock_amount": min_stock_amount,
        "description": "Auto-created by PantryBot"
    }

    result = await grocy_api("/objects/products", method="POST", body=product_data)

    if "success" in result and not result["success"]:
        return result

    product_id = result.get("created_object_id")

    # Add initial stock entry at 0 quantity so it shows in Stock Overview
    from datetime import datetime, timedelta
    initial_stock_data = {
        "amount": 0,
        "best_before_date": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
        "price": 0
    }

    await grocy_api(
        f"/stock/products/{product_id}/add",
        method="POST",
        body=initial_stock_data
    )

    logger.info(f"✅ Created product '{name}' with initial 0 stock entry")

    return {
        "success": True,
        "message": f"Created product: {name} (added to stock at 0 quantity)",
        "product_id": product_id,
        "location": location,
        "unit": quantity_unit
    }


# ============================================================================
# STOCK MONITORING
# ============================================================================

async def get_expiring_soon(days: int = 7) -> Dict[str, Any]:
    """
    Get products that are expiring soon.

    Args:
        days: Number of days to look ahead (default: 7)

    Returns:
        List of products expiring within the specified days
    """
    volatile = await grocy_api("/stock/volatile")

    if "success" in volatile and not volatile["success"]:
        return volatile

    # Extract expiring and expired products
    expiring = volatile.get("expiring_products", [])
    expired = volatile.get("expired_products", [])

    return {
        "success": True,
        "expiring_soon": expiring,
        "already_expired": expired,
        "total_items": len(expiring) + len(expired)
    }


async def get_missing_products() -> Dict[str, Any]:
    """
    Get products that are below minimum stock level.
    """
    volatile = await grocy_api("/stock/volatile")

    if "success" in volatile and not volatile["success"]:
        return volatile

    missing = volatile.get("missing_products", [])

    return {
        "success": True,
        "missing_products": missing,
        "total_missing": len(missing)
    }


async def add_missing_to_shopping_list(shopping_list_id: int = 1) -> Dict[str, Any]:
    """
    Add all products below minimum stock to the shopping list.

    Args:
        shopping_list_id: ID of the shopping list (default: 1)

    Returns:
        Success confirmation with number of items added
    """
    result = await grocy_api(
        "/stock/shoppinglist/add-missing-products",
        method="POST",
        body={"list_id": shopping_list_id}
    )

    if "success" in result and not result["success"]:
        return result

    return {
        "success": True,
        "message": "Added missing products to shopping list",
        "shopping_list_id": shopping_list_id
    }
