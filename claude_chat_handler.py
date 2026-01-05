"""
Claude API integration for PantryBot
Handles tool calling with Claude's native tool use feature
"""

import json
import logging
from typing import Dict, Any, List
from anthropic import Anthropic

logger = logging.getLogger("pantrybot")


def get_claude_tools() -> List[Dict[str, Any]]:
    """Define tools in Claude's format"""
    return [
        {
            "name": "get_pantry_items",
            "description": "Get condensed list of items currently in pantry from Grocy. Use this to check what ingredients are available.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category: 'all', 'expiring_soon', 'low_stock', or a product name to search for",
                        "default": "all"
                    }
                },
                "required": []
            }
        },
        {
            "name": "search_recipes_by_ingredients",
            "description": "Search for recipes using available ingredients via Spoonacular API. Returns recipe suggestions instantly.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ingredients": {
                        "type": "string",
                        "description": "Comma-separated list of ingredients (e.g., 'salmon,lemon,dill')"
                    },
                    "number": {
                        "type": "integer",
                        "description": "Number of recipes to return (default 3, max 5)",
                        "default": 3
                    }
                },
                "required": ["ingredients"]
            }
        },
        {
            "name": "get_recipe_details",
            "description": "Get full recipe details including ingredients and instructions for a specific recipe by ID",
            "input_schema": {
                "type": "object",
                "properties": {
                    "recipe_id": {
                        "type": "integer",
                        "description": "The Spoonacular recipe ID from search results"
                    }
                },
                "required": ["recipe_id"]
            }
        },
        {
            "name": "save_recipe",
            "description": "Save a recipe to the filesystem for later reference",
            "input_schema": {
                "type": "object",
                "properties": {
                    "recipe_name": {
                        "type": "string",
                        "description": "Name for the recipe file (e.g., 'Salmon Cakes')"
                    },
                    "recipe_content": {
                        "type": "string",
                        "description": "Full recipe content including ingredients and instructions"
                    }
                },
                "required": ["recipe_name", "recipe_content"]
            }
        },
        {
            "name": "list_recipes",
            "description": "List all saved recipes",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_recipe",
            "description": "Retrieve a previously saved recipe by name",
            "input_schema": {
                "type": "object",
                "properties": {
                    "recipe_name": {
                        "type": "string",
                        "description": "Name of the recipe to retrieve"
                    }
                },
                "required": ["recipe_name"]
            }
        },
        {
            "name": "get_product_info",
            "description": "Get detailed information about a specific product in the pantry",
            "input_schema": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Name of the product to search for"
                    }
                },
                "required": ["product_name"]
            }
        },
        {
            "name": "consume_stock",
            "description": "Remove/consume items from pantry inventory in Grocy. Use this when the user says they used ingredients or made a recipe.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Name of the product to consume (e.g., 'salmon', 'canned salmon')"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount to consume/remove from inventory"
                    },
                    "spoiled": {
                        "type": "boolean",
                        "description": "Whether the item was spoiled (default: false)",
                        "default": False
                    }
                },
                "required": ["product_name", "amount"]
            }
        },
        {
            "name": "add_stock",
            "description": "Add items to pantry inventory in Grocy. Use this when the user says they bought groceries or restocked items.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Name of the product to add (e.g., 'salmon', 'canned salmon')"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount to add to inventory"
                    },
                    "best_before_date": {
                        "type": "string",
                        "description": "Best before date in YYYY-MM-DD format (optional)"
                    },
                    "price": {
                        "type": "number",
                        "description": "Price paid for the item (optional)"
                    }
                },
                "required": ["product_name", "amount"]
            }
        },
        {
            "name": "add_to_shopping_list",
            "description": "Add items to the Grocy shopping list. Use this when the user wants to remember to buy something.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Name of the product to add to shopping list"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount to add to shopping list (default: 1)",
                        "default": 1
                    }
                },
                "required": ["product_name"]
            }
        },
        {
            "name": "get_shopping_list",
            "description": "Get the current shopping list from Grocy",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    ]


async def call_claude_with_tools(
    client: Anthropic,
    model: str,
    messages: List[Dict[str, Any]],
    system_prompt: str,
    execute_tool_func
) -> Dict[str, Any]:
    """
    Call Claude API with tool support, handling multiple rounds of tool calls

    Args:
        client: Anthropic client instance
        model: Claude model name
        messages: Conversation messages
        system_prompt: System prompt
        execute_tool_func: Async function to execute tools

    Returns:
        Dict with response and updated messages
    """
    logger.info(f"🤖 Calling Claude ({model}) with {len(messages)} messages")

    # Import here to avoid circular dependency
    from pydantic import BaseModel
    class ToolRequest(BaseModel):
        tool: str
        parameters: Dict[str, Any]

    # Loop to handle multiple rounds of tool calling
    max_iterations = 10
    tool_used = False

    for iteration in range(max_iterations):
        # Call Claude
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            tools=get_claude_tools()
        )

        logger.info(f"✅ Claude responded (stop_reason: {response.stop_reason}, iteration: {iteration + 1})")

        # If no tool use, we're done
        if response.stop_reason != "tool_use":
            # Extract text response
            response_text = ""
            for block in response.content:
                if block.type == "text":
                    response_text += block.text

            # Add final assistant message to conversation history
            messages.append({
                "role": "assistant",
                "content": response_text
            })

            logger.info(f"✅ Final response length: {len(response_text)} chars")

            return {
                "response": response_text,
                "messages": messages,
                "tool_used": tool_used
            }

        # Handle tool use
        tool_used = True
        assistant_content = []
        tool_results = []

        for block in response.content:
            if block.type == "text":
                assistant_content.append(block)
            elif block.type == "tool_use":
                logger.info(f"🔧 Claude wants to use tool: {block.name} with params: {block.input}")

                # Execute the tool
                tool_result = await execute_tool_func(
                    ToolRequest(tool=block.name, parameters=block.input)
                )

                logger.info(f"✅ Tool {block.name} returned: {str(tool_result)[:200]}...")

                # Add to results
                assistant_content.append(block)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(tool_result)
                })

        # Add assistant message with tool use to conversation
        messages.append({
            "role": "assistant",
            "content": assistant_content
        })

        # Add tool results as user message
        messages.append({
            "role": "user",
            "content": tool_results
        })

        logger.info(f"🔄 Calling Claude again (iteration {iteration + 2})...")

    # If we hit max iterations, return what we have
    logger.warning(f"⚠️ Hit max iterations ({max_iterations}) for tool calling loop")
    return {
        "response": "I apologize, but I encountered an issue processing your request. Please try again.",
        "messages": messages,
        "tool_used": tool_used
    }
