"""
Open WebUI Function for PantryBot Integration
This function allows Open WebUI to call PantryBot MCP server tools.

Installation:
1. Open WebUI at http://192.168.0.83:3004
2. Go to Admin Panel → Functions
3. Create new Function
4. Paste this code
5. Enable the function

The function will be available to all models in Open WebUI.
"""

import httpx
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class Functions:
    """PantryBot integration for Open WebUI"""

    def __init__(self):
        self.valves = self.Valves()

    class Valves(BaseModel):
        PANTRYBOT_URL: str = Field(
            default="http://pantrybot:8000",
            description="PantryBot server URL (use Docker service name)"
        )
        TIMEOUT: int = Field(
            default=30,
            description="Request timeout in seconds"
        )

    async def get_pantry_items(
        self,
        category: str = "all",
        __event_emitter__: Optional[Any] = None
    ) -> str:
        """
        Get condensed list of items currently in pantry from Grocy.

        Args:
            category: Filter by category - "all", "expiring_soon", "low_stock", or product name

        Returns:
            JSON string with pantry items
        """
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Fetching pantry items (category: {category})",
                        "done": False,
                    },
                }
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.valves.PANTRYBOT_URL}/tools/execute",
                    json={
                        "tool": "get_pantry_items",
                        "parameters": {"category": category}
                    },
                    timeout=self.valves.TIMEOUT
                )
                response.raise_for_status()
                result = response.json()

                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": f"Found {result.get('total_products', 0)} items",
                                "done": True,
                            },
                        }
                    )

                return str(result)

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Error: {str(e)}",
                            "done": True,
                        },
                    }
                )
            return f"Error fetching pantry items: {str(e)}"

    async def save_recipe(
        self,
        recipe_name: str,
        recipe_content: str,
        __event_emitter__: Optional[Any] = None
    ) -> str:
        """
        Save a recipe to the filesystem.

        Args:
            recipe_name: Name of the recipe (e.g., "Beef Chili")
            recipe_content: Full recipe text including ingredients and instructions

        Returns:
            JSON string with save result
        """
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Saving recipe: {recipe_name}",
                        "done": False,
                    },
                }
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.valves.PANTRYBOT_URL}/tools/execute",
                    json={
                        "tool": "save_recipe",
                        "parameters": {
                            "recipe_name": recipe_name,
                            "recipe_content": recipe_content
                        }
                    },
                    timeout=self.valves.TIMEOUT
                )
                response.raise_for_status()
                result = response.json()

                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": "Recipe saved successfully",
                                "done": True,
                            },
                        }
                    )

                return str(result)

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Error: {str(e)}",
                            "done": True,
                        },
                    }
                )
            return f"Error saving recipe: {str(e)}"

    async def get_recipe(
        self,
        recipe_name: str,
        __event_emitter__: Optional[Any] = None
    ) -> str:
        """
        Retrieve a saved recipe from filesystem.

        Args:
            recipe_name: Name of the recipe to retrieve

        Returns:
            JSON string with recipe content
        """
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Retrieving recipe: {recipe_name}",
                        "done": False,
                    },
                }
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.valves.PANTRYBOT_URL}/tools/execute",
                    json={
                        "tool": "get_recipe",
                        "parameters": {"recipe_name": recipe_name}
                    },
                    timeout=self.valves.TIMEOUT
                )
                response.raise_for_status()
                result = response.json()

                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": "Recipe retrieved",
                                "done": True,
                            },
                        }
                    )

                return str(result)

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Error: {str(e)}",
                            "done": True,
                        },
                    }
                )
            return f"Error retrieving recipe: {str(e)}"

    async def list_recipes(
        self,
        __event_emitter__: Optional[Any] = None
    ) -> str:
        """
        List all saved recipes.

        Returns:
            JSON string with list of all recipes
        """
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Listing all recipes",
                        "done": False,
                    },
                }
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.valves.PANTRYBOT_URL}/tools/execute",
                    json={
                        "tool": "list_recipes",
                        "parameters": {}
                    },
                    timeout=self.valves.TIMEOUT
                )
                response.raise_for_status()
                result = response.json()

                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": f"Found {result.get('total_recipes', 0)} recipes",
                                "done": True,
                            },
                        }
                    )

                return str(result)

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Error: {str(e)}",
                            "done": True,
                        },
                    }
                )
            return f"Error listing recipes: {str(e)}"

    async def get_product_info(
        self,
        product_name: str,
        __event_emitter__: Optional[Any] = None
    ) -> str:
        """
        Get detailed information about a specific product in pantry.

        Args:
            product_name: Name of the product to search for

        Returns:
            JSON string with product details
        """
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Searching for product: {product_name}",
                        "done": False,
                    },
                }
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.valves.PANTRYBOT_URL}/tools/execute",
                    json={
                        "tool": "get_product_info",
                        "parameters": {"product_name": product_name}
                    },
                    timeout=self.valves.TIMEOUT
                )
                response.raise_for_status()
                result = response.json()

                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": "Product info retrieved",
                                "done": True,
                            },
                        }
                    )

                return str(result)

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Error: {str(e)}",
                            "done": True,
                        },
                    }
                )
            return f"Error getting product info: {str(e)}"
