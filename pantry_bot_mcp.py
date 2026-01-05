#!/usr/bin/env python3
"""
PantryBot MCP Server - Connects Llama to Grocy for pantry management and recipe suggestions
"""

import asyncio
import os
import json
from typing import Any
from datetime import datetime
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

# Configuration from environment variables
GROCY_API_URL = os.getenv("GROCY_API_URL", "http://192.168.0.83:9283/api")
GROCY_API_KEY = os.getenv("GROCY_API_KEY", "")
RECIPE_DIR = Path(os.getenv("RECIPE_DIR", "./recipes"))

# Ensure recipe directory exists
RECIPE_DIR.mkdir(exist_ok=True)

# Initialize FastMCP server
mcp = FastMCP("PantryBot")


def get_headers() -> dict:
    """Get headers for Grocy API requests"""
    headers = {"accept": "application/json"}
    if GROCY_API_KEY:
        headers["GROCY-API-KEY"] = GROCY_API_KEY
    return headers


@mcp.tool()
async def get_pantry_items(category: str = "all") -> str:
    """
    Get ultra-condensed list of items currently in pantry from Grocy.
    Returns ONLY essential fields: name, amount, best_before.

    Args:
        category: Filter by category (all, expiring_soon, low_stock, or specific product name)

    Returns:
        Minimal JSON with just what's needed for meal planning
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GROCY_API_URL}/stock",
                headers=get_headers(),
                timeout=10.0
            )
            response.raise_for_status()
            stock_data = response.json()

            # Ultra-condensed - only name, amount, best_before
            condensed_items = []
            for item in stock_data:
                product = item.get("product", {})

                # Skip items with zero stock
                amount = float(item.get("amount_aggregated", 0))
                if amount <= 0:
                    continue

                # Apply filtering
                if category != "all":
                    if category == "expiring_soon":
                        # Check if expiring within 7 days
                        best_before = item.get("best_before_date", "")
                        if best_before:
                            from datetime import datetime, timedelta
                            exp_date = datetime.strptime(best_before, "%Y-%m-%d")
                            if (exp_date - datetime.now()).days > 7:
                                continue
                    elif category == "low_stock":
                        # Check if below minimum stock
                        min_stock = float(product.get("min_stock_amount", 0))
                        if amount >= min_stock:
                            continue
                    elif category.lower() not in product.get("name", "").lower():
                        continue

                condensed_item = {
                    "name": product.get("name", "Unknown"),
                    "amount": amount,
                    "best_before": item.get("best_before_date", "N/A")
                }
                condensed_items.append(condensed_item)

            return json.dumps({
                "total_products": len(condensed_items),
                "items": condensed_items
            }, indent=2)

        except httpx.HTTPError as e:
            return json.dumps({
                "error": f"Failed to fetch pantry items: {str(e)}",
                "items": []
            })


@mcp.tool()
async def search_recipes(ingredient: str = "") -> str:
    """
    Search for recipes in Grocy recipe database or saved recipe files.

    Args:
        ingredient: Optional ingredient to filter recipes

    Returns:
        List of available recipes with basic info
    """
    async with httpx.AsyncClient() as client:
        try:
            # Get recipes from Grocy
            response = await client.get(
                f"{GROCY_API_URL}/objects/recipes",
                headers=get_headers(),
                timeout=10.0
            )
            response.raise_for_status()
            recipes_data = response.json()

            # Condense recipe info
            condensed_recipes = []
            for recipe in recipes_data:
                recipe_name = recipe.get("name", "Unknown")

                # Filter by ingredient if provided
                if ingredient and ingredient.lower() not in recipe_name.lower():
                    description = recipe.get("description", "")
                    if ingredient.lower() not in description.lower():
                        continue

                condensed_recipes.append({
                    "id": recipe.get("id"),
                    "name": recipe_name,
                    "description": recipe.get("description", ""),
                    "servings": recipe.get("desired_servings", 1)
                })

            return json.dumps({
                "total_recipes": len(condensed_recipes),
                "recipes": condensed_recipes
            }, indent=2)

        except httpx.HTTPError as e:
            # Fallback to local recipe files
            local_recipes = []
            if RECIPE_DIR.exists():
                for recipe_file in RECIPE_DIR.glob("*.txt"):
                    if not ingredient or ingredient.lower() in recipe_file.stem.lower():
                        local_recipes.append({
                            "name": recipe_file.stem.replace("_", " ").title(),
                            "file": str(recipe_file),
                            "source": "local"
                        })

            return json.dumps({
                "total_recipes": len(local_recipes),
                "recipes": local_recipes,
                "note": "Retrieved from local files (Grocy API unavailable)"
            }, indent=2)


@mcp.tool()
async def save_recipe(recipe_name: str, recipe_content: str) -> str:
    """
    Save a recipe to the filesystem.

    Args:
        recipe_name: Name of the recipe (e.g., "taco_seasoning" or "Taco Seasoning")
        recipe_content: Full recipe content with ingredients and instructions

    Returns:
        Confirmation message with file path
    """
    # Sanitize filename
    safe_name = recipe_name.lower().replace(" ", "_").replace("/", "_")
    if not safe_name.endswith(".txt"):
        safe_name += ".txt"

    recipe_path = RECIPE_DIR / safe_name

    try:
        # Add metadata header
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_content = f"""# {recipe_name.title()}
# Created: {timestamp}
# Source: PantryBot

{recipe_content}
"""

        recipe_path.write_text(full_content, encoding="utf-8")

        return json.dumps({
            "success": True,
            "message": f"Recipe saved successfully",
            "file_path": str(recipe_path),
            "recipe_name": recipe_name
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to save recipe: {str(e)}"
        })


@mcp.tool()
async def get_recipe(recipe_name: str) -> str:
    """
    Read a saved recipe from the filesystem.

    Args:
        recipe_name: Name of the recipe file (with or without .txt extension)

    Returns:
        Recipe content or error message
    """
    # Try to find the recipe file
    safe_name = recipe_name.lower().replace(" ", "_")
    if not safe_name.endswith(".txt"):
        safe_name += ".txt"

    recipe_path = RECIPE_DIR / safe_name

    try:
        if recipe_path.exists():
            content = recipe_path.read_text(encoding="utf-8")
            return json.dumps({
                "success": True,
                "recipe_name": recipe_name,
                "content": content
            }, indent=2)
        else:
            # List available recipes
            available = [f.stem.replace("_", " ").title()
                        for f in RECIPE_DIR.glob("*.txt")]
            return json.dumps({
                "success": False,
                "error": f"Recipe '{recipe_name}' not found",
                "available_recipes": available
            }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to read recipe: {str(e)}"
        })


@mcp.tool()
async def list_recipes() -> str:
    """
    List all saved recipes in the recipe directory.

    Returns:
        List of available recipe files
    """
    try:
        recipes = []
        if RECIPE_DIR.exists():
            for recipe_file in sorted(RECIPE_DIR.glob("*.txt")):
                # Get file size and modification time
                stat = recipe_file.stat()
                recipes.append({
                    "name": recipe_file.stem.replace("_", " ").title(),
                    "filename": recipe_file.name,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                })

        return json.dumps({
            "total_recipes": len(recipes),
            "recipes": recipes,
            "recipe_directory": str(RECIPE_DIR)
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to list recipes: {str(e)}"
        })


@mcp.tool()
async def get_product_info(product_name: str) -> str:
    """
    Get detailed information about a specific product in Grocy.

    Args:
        product_name: Name of the product to search for

    Returns:
        Detailed product information including stock levels
    """
    async with httpx.AsyncClient() as client:
        try:
            # Get all stock
            response = await client.get(
                f"{GROCY_API_URL}/stock",
                headers=get_headers(),
                timeout=10.0
            )
            response.raise_for_status()
            stock_data = response.json()

            # Find matching products
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
                        "min_stock_amount": product.get("min_stock_amount", 0),
                        "description": product.get("description", "No description")
                    })

            if matches:
                return json.dumps({
                    "found": True,
                    "matches": matches
                }, indent=2)
            else:
                return json.dumps({
                    "found": False,
                    "message": f"No products found matching '{product_name}'"
                })

        except httpx.HTTPError as e:
            return json.dumps({
                "error": f"Failed to fetch product info: {str(e)}"
            })


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
