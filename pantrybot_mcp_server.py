#!/usr/bin/env python3
"""
PantryBot MCP Server
A True Model Context Protocol server for intelligent pantry management and meal planning.

Combines Grocy (pantry inventory) + Spoonacular (recipes) + Claude AI
for complete pantry-to-plate assistance.

Usage with Claude Desktop:
  Add to your claude_desktop_config.json:
  {
    "mcpServers": {
      "pantrybot": {
        "command": "python",
        "args": ["/path/to/pantrybot_mcp_server.py"]
      }
    }
  }

Author: Built with Claude Code
License: MIT
"""

import asyncio
from mcp.server.fastmcp import FastMCP

# Import all shared tool functions
from pantry_tools import (
    get_pantry_items,
    get_product_info,
    consume_stock,
    add_stock,
    add_to_shopping_list,
    get_shopping_list,
    search_recipes_by_ingredients,
    get_recipe_details,
    save_recipe,
    get_recipe,
    list_recipes
)

# Initialize MCP server
mcp = FastMCP("PantryBot")


# ============================================================================
# GROCY PANTRY MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
async def get_pantry(category: str = "all") -> dict:
    """
    Get condensed list of items currently in pantry from Grocy.
    Use this to check what ingredients are available.

    Args:
        category: Filter by category:
            - 'all' (default): All items in stock
            - 'expiring_soon': Items expiring within 7 days
            - 'low_stock': Items below minimum stock level
            - Or a product name to search for (e.g., 'salmon')

    Returns:
        Dictionary with:
            - success: bool
            - total_products: int
            - items: list of {name, amount, best_before}
    """
    return await get_pantry_items(category)


@mcp.tool()
async def get_product(product_name: str) -> dict:
    """
    Get detailed information about a specific product in the pantry.

    Args:
        product_name: Name of the product to search for

    Returns:
        Dictionary with product details including amount, best_before date, etc.
    """
    return await get_product_info(product_name)


@mcp.tool()
async def use_ingredients(product_name: str, amount: float, spoiled: bool = False) -> dict:
    """
    Remove/consume items from pantry inventory in Grocy.
    Use this when the user says they used ingredients or made a recipe.

    Args:
        product_name: Name of the product to consume (e.g., 'salmon', 'canned salmon')
        amount: Amount to consume/remove from inventory
        spoiled: Whether the item was spoiled (default: False)

    Returns:
        Dictionary with success status and confirmation message

    Example:
        "I made salmon cakes and used 2 cans of salmon"
        → use_ingredients("salmon", 2)
    """
    return await consume_stock(product_name, amount, spoiled)


@mcp.tool()
async def purchase_groceries(product_name: str, amount: float, best_before_date: str = None, price: float = None) -> dict:
    """
    Add items to pantry inventory in Grocy.
    Use this when the user says they bought groceries or restocked items.

    Args:
        product_name: Name of the product to add (e.g., 'salmon', 'canned salmon')
        amount: Amount to add to inventory
        best_before_date: Best before date in YYYY-MM-DD format (optional)
        price: Price paid for the item (optional)

    Returns:
        Dictionary with success status and confirmation message

    Example:
        "I bought 5 cans of salmon at the store"
        → purchase_groceries("salmon", 5)
    """
    return await add_stock(product_name, amount, best_before_date, price)


@mcp.tool()
async def add_to_shopping(product_name: str, amount: float = 1) -> dict:
    """
    Add items to the Grocy shopping list.
    Use this when the user wants to remember to buy something.

    Args:
        product_name: Name of the product to add to shopping list
        amount: Amount to add to shopping list (default: 1)

    Returns:
        Dictionary with success status and confirmation message

    Example:
        "Add salmon to my shopping list"
        → add_to_shopping("salmon", 1)
    """
    return await add_to_shopping_list(product_name, amount)


@mcp.tool()
async def view_shopping_list() -> dict:
    """
    Get the current shopping list from Grocy.

    Returns:
        Dictionary with:
            - success: bool
            - total_items: int
            - items: list of shopping list items
    """
    return await get_shopping_list()


# ============================================================================
# RECIPE DISCOVERY & MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
async def find_recipes(ingredients: str, number: int = 5) -> dict:
    """
    Search for recipes using available ingredients via Spoonacular API.
    Returns recipe suggestions with match percentages showing how much you can make with current pantry.

    Args:
        ingredients: Comma-separated list of ingredients (e.g., 'salmon,lemon,dill')
        number: Number of recipes to return (default: 5, max: 10)

    Returns:
        Dictionary with:
            - success: bool
            - total_recipes: int
            - recipes: list of recipes sorted by match percentage (highest first)
                Each recipe includes:
                - id: Recipe ID for get_recipe_instructions
                - title: Recipe name
                - match_percentage: % of ingredients you have
                - missed_items: List of ingredients you need to buy
                - used_ingredients: Count of ingredients you have
                - missed_ingredients: Count of ingredients you need

    Example:
        "What can I make with salmon and rice?"
        → find_recipes("salmon,rice")
    """
    return await search_recipes_by_ingredients(ingredients, min(number, 10))


@mcp.tool()
async def get_recipe_instructions(recipe_id: int) -> dict:
    """
    Get full recipe details including ingredients and step-by-step instructions.
    Use this after find_recipes to get complete cooking instructions.

    Args:
        recipe_id: The Spoonacular recipe ID from find_recipes results

    Returns:
        Dictionary with:
            - success: bool
            - title: Recipe name
            - servings: Number of servings
            - ready_in_minutes: Cooking time
            - ingredients: Full ingredient list
            - instructions: Step-by-step cooking instructions
            - source_url: Original recipe URL

    Example:
        After finding recipe ID 663050:
        → get_recipe_instructions(663050)
    """
    return await get_recipe_details(recipe_id)


@mcp.tool()
async def save_favorite_recipe(recipe_name: str, recipe_content: str) -> dict:
    """
    Save a recipe to the filesystem for later reference.
    Use this to save family favorites or customized recipes.

    Args:
        recipe_name: Name for the recipe file (e.g., 'Salmon Cakes')
        recipe_content: Full recipe content including ingredients and instructions

    Returns:
        Dictionary with success status, file path, and confirmation

    Example:
        "Save this salmon cakes recipe"
        → save_favorite_recipe("Salmon Cakes", "Ingredients:\n...")
    """
    return await save_recipe(recipe_name, recipe_content)


@mcp.tool()
async def get_saved_recipe(recipe_name: str) -> dict:
    """
    Retrieve a previously saved recipe by name.

    Args:
        recipe_name: Name of the recipe to retrieve

    Returns:
        Dictionary with recipe content or list of available recipes if not found
    """
    return await get_recipe(recipe_name)


@mcp.tool()
async def list_saved_recipes() -> dict:
    """
    List all saved recipes with metadata.

    Returns:
        Dictionary with:
            - success: bool
            - total_recipes: int
            - recipes: list of {name, filename, size_kb, modified}
    """
    return await list_recipes()


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
