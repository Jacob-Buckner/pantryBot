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
    list_recipes,
    # New extended Grocy tools
    grocy_api,
    get_chores_status,
    complete_chore,
    add_chore,
    get_pending_tasks,
    complete_task,
    add_task,
    get_batteries_status,
    charge_battery,
    create_product,
    get_expiring_soon,
    get_missing_products,
    add_missing_to_shopping_list
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
# GENERIC GROCY API ACCESS
# ============================================================================

@mcp.tool()
async def call_grocy_api(endpoint: str, method: str = "GET", body: dict = None) -> dict:
    """
    Call any Grocy API endpoint directly for advanced operations.
    Use this for operations not covered by convenience tools.

    Args:
        endpoint: API endpoint path (e.g., "/objects/chores", "/stock/volatile")
        method: HTTP method - GET, POST, PUT, or DELETE (default: GET)
        body: Optional request body for POST/PUT requests

    Common endpoints:
        - /objects/chores - List all chores
        - /objects/batteries - List batteries
        - /objects/tasks - List tasks
        - /objects/equipment - List equipment
        - /objects/products - List all products
        - /objects/locations - List storage locations
        - /stock/volatile - Get expiring/missing products
        - /system/info - Get Grocy system information

    Returns:
        Raw JSON response from Grocy API
    """
    return await grocy_api(endpoint, method, body)


# ============================================================================
# CHORE MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
async def get_chores() -> dict:
    """
    Get all household chores with their status and next execution time.
    Shows which chores are due, overdue, or upcoming.

    Returns:
        List of chores with their schedule and status
    """
    return await get_chores_status()


@mcp.tool()
async def mark_chore_complete(chore_name: str) -> dict:
    """
    Mark a household chore as completed.
    Automatically calculates the next due date based on the chore's schedule.

    Args:
        chore_name: Name of the chore (e.g., "Clean bathroom", "Water plants")

    Returns:
        Confirmation with next execution time

    Example:
        "I finished cleaning the bathroom" → mark_chore_complete("Clean bathroom")
    """
    return await complete_chore(chore_name)


@mcp.tool()
async def create_chore(name: str, period_days: int = 7) -> dict:
    """
    Add a new recurring household chore.

    Args:
        name: Chore name (e.g., "Water plants", "Change air filter")
        period_days: How often the chore repeats in days (default: 7 for weekly)

    Returns:
        Confirmation with chore ID

    Example:
        "Add 'clean the gutters' as a monthly chore" → create_chore("Clean gutters", 30)
    """
    return await add_chore(name, period_days)


# ============================================================================
# TASK MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
async def get_tasks() -> dict:
    """
    Get all pending tasks (to-do items) that haven't been completed yet.

    Returns:
        List of incomplete tasks with due dates
    """
    return await get_pending_tasks()


@mcp.tool()
async def mark_task_complete(task_name: str) -> dict:
    """
    Mark a task as completed.

    Args:
        task_name: Name of the task to complete

    Returns:
        Confirmation

    Example:
        "I called the plumber" → mark_task_complete("Call plumber")
    """
    return await complete_task(task_name)


@mcp.tool()
async def create_task(name: str, due_date: str = None) -> dict:
    """
    Add a new task to the to-do list.

    Args:
        name: Task description
        due_date: Optional due date in YYYY-MM-DD format

    Returns:
        Confirmation with task ID

    Example:
        "Remind me to call the plumber next week" → create_task("Call plumber", "2026-01-12")
    """
    return await add_task(name, due_date)


# ============================================================================
# BATTERY MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
async def get_batteries() -> dict:
    """
    Get all batteries with their charge status and next charge date.
    Shows which batteries need charging soon.

    Returns:
        List of batteries with charge tracking information
    """
    return await get_batteries_status()


@mcp.tool()
async def track_battery_charge(battery_name: str) -> dict:
    """
    Track that a battery has been charged.
    Updates the last charge date and calculates next charge due.

    Args:
        battery_name: Name of the battery (e.g., "TV Remote", "Smoke Detector")

    Returns:
        Confirmation with next charge date

    Example:
        "I changed the smoke detector battery" → track_battery_charge("Smoke Detector")
    """
    return await charge_battery(battery_name)


# ============================================================================
# PRODUCT CREATION TOOL
# ============================================================================

@mcp.tool()
async def auto_create_product(name: str, location: str = "Pantry", unit: str = "piece") -> dict:
    """
    Automatically create a new product in Grocy if it doesn't exist.
    Use this when adding stock for a product that hasn't been set up yet.

    Args:
        name: Product name
        location: Where it's stored (default: "Pantry")
        unit: Unit of measurement - "piece", "kg", "lb", "liter", etc. (default: "piece")

    Returns:
        Confirmation with product ID

    Example:
        User says "I bought kale" but kale doesn't exist
        → auto_create_product("Kale", "Refrigerator", "bunch")
    """
    return await create_product(name, location, unit)


# ============================================================================
# STOCK MONITORING TOOLS
# ============================================================================

@mcp.tool()
async def check_expiring_products(days: int = 7) -> dict:
    """
    Check which products are expiring soon or already expired.

    Args:
        days: Number of days to look ahead (default: 7)

    Returns:
        Lists of expiring and expired products

    Example:
        "What food is expiring soon?" → check_expiring_products(7)
    """
    return await get_expiring_soon(days)


@mcp.tool()
async def check_low_stock() -> dict:
    """
    Check which products are below their minimum stock level.
    These are items that need to be restocked.

    Returns:
        List of products running low

    Example:
        "What am I running low on?" → check_low_stock()
    """
    return await get_missing_products()


@mcp.tool()
async def auto_add_to_shopping_list() -> dict:
    """
    Automatically add all low-stock products to the shopping list.
    Adds everything that's below minimum stock level.

    Returns:
        Confirmation with number of items added

    Example:
        "Add everything I'm low on to my shopping list" → auto_add_to_shopping_list()
    """
    return await add_missing_to_shopping_list()


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
