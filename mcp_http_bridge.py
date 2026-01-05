#!/usr/bin/env python3
"""
HTTP Bridge for PantryBot MCP Server
Exposes MCP tools over HTTP so Mac CLI can access them over the network
"""

import os
import json
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from anthropic import Anthropic
from claude_chat_handler import call_claude_with_tools

# Import shared tool functions and configuration
from pantry_tools import (
    # Tool functions
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
    # Configuration constants
    GROCY_API_URL,
    RECIPE_DIR
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pantrybot")

# Claude API Configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

# Initialize Claude client
if not CLAUDE_API_KEY:
    raise ValueError("CLAUDE_API_KEY is required! Set it in .env file")
claude_client = Anthropic(api_key=CLAUDE_API_KEY)

app = FastAPI(title="PantryBot HTTP Bridge (Open WebUI)", version="2.0.0")


# Request/Response Models
class ToolRequest(BaseModel):
    tool: str
    parameters: Optional[Dict[str, Any]] = {}


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


# In-memory conversation storage (for simplicity)
conversations: Dict[str, list] = {}


# ============================================================================
# NOTE: All tool implementations have been moved to pantry_tools.py
# This server now acts as an HTTP/OpenAI-compatible wrapper around those tools
# ============================================================================


# ============================================================================
# HTTP API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "PantryBot MCP Bridge (Claude API)",
        "status": "running",
        "grocy_url": GROCY_API_URL,
        "ai_backend": "Claude API",
        "ai_model": CLAUDE_MODEL,
        "recipe_dir": str(RECIPE_DIR)
    }


@app.post("/tools/execute")
async def execute_tool(request: ToolRequest):
    """Execute an MCP tool"""
    tool_name = request.tool
    params = request.parameters or {}

    logger.info(f"🔧 Executing tool: {tool_name} with params: {params}")

    # Route to appropriate tool
    if tool_name == "get_pantry_items":
        result = await get_pantry_items(params.get("category", "all"))
    elif tool_name == "save_recipe":
        result = await save_recipe(
            params.get("recipe_name", ""),
            params.get("recipe_content", "")
        )
    elif tool_name == "get_recipe":
        result = await get_recipe(params.get("recipe_name", ""))
    elif tool_name == "list_recipes":
        result = await list_recipes()
    elif tool_name == "get_product_info":
        result = await get_product_info(params.get("product_name", ""))
    elif tool_name == "search_recipes_by_ingredients":
        result = await search_recipes_by_ingredients(
            params.get("ingredients", ""),
            params.get("number", 5)
        )
    elif tool_name == "get_recipe_details":
        result = await get_recipe_details(params.get("recipe_id", 0))
    elif tool_name == "consume_stock":
        result = await consume_stock(
            params.get("product_name", ""),
            params.get("amount", 0),
            params.get("spoiled", False)
        )
    elif tool_name == "add_stock":
        result = await add_stock(
            params.get("product_name", ""),
            params.get("amount", 0),
            params.get("best_before_date"),
            params.get("price")
        )
    elif tool_name == "add_to_shopping_list":
        result = await add_to_shopping_list(
            params.get("product_name", ""),
            params.get("amount", 1)
        )
    elif tool_name == "get_shopping_list":
        result = await get_shopping_list()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")

    return result


@app.get("/tools/list")
async def list_tools():
    """List available MCP tools"""
    return {
        "tools": [
            {
                "name": "get_pantry_items",
                "description": "Get condensed list of pantry items from Grocy",
                "parameters": ["category (optional): all, expiring_soon, low_stock, or product name"]
            },
            {
                "name": "save_recipe",
                "description": "Save a recipe to filesystem",
                "parameters": ["recipe_name", "recipe_content"]
            },
            {
                "name": "get_recipe",
                "description": "Retrieve a saved recipe",
                "parameters": ["recipe_name"]
            },
            {
                "name": "list_recipes",
                "description": "List all saved recipes",
                "parameters": []
            },
            {
                "name": "get_product_info",
                "description": "Get detailed info about a specific product",
                "parameters": ["product_name"]
            },
            {
                "name": "search_recipes_by_ingredients",
                "description": "Search for recipes using available ingredients (Spoonacular API)",
                "parameters": ["ingredients (comma-separated)", "number (optional, default 5)"]
            },
            {
                "name": "get_recipe_details",
                "description": "Get full recipe with instructions by recipe ID",
                "parameters": ["recipe_id"]
            }
        ]
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint that uses Claude API with native tool calling"""
    logger.info(f"💬 Chat message: {request.message[:100]}...")
    conv_id = request.conversation_id or "default"

    # Initialize conversation if needed
    if conv_id not in conversations:
        conversations[conv_id] = []

    # Add user message
    conversations[conv_id].append({
        "role": "user",
        "content": request.message
    })

    # System prompt - Claude handles tool calling automatically
    system_prompt = """You are PantryBot, a helpful cooking assistant for a busy family.

You have access to:
- The family's real pantry inventory (via Grocy)
- Recipe search (via Spoonacular API)
- Saved family recipes

When someone asks "What can I make for supper?":
1. Check their pantry to see what's available
2. Search for 3 practical, family-friendly recipes using those ingredients
3. Present the options clearly and ask which they'd like
4. When they choose, get the full recipe details
5. Offer to save recipes they like

Be practical, helpful, and conversational. This tool helps a busy stay-at-home mom plan meals easily."""

    try:
        # Call Claude with tools
        result = await call_claude_with_tools(
            client=claude_client,
            model=CLAUDE_MODEL,
            messages=conversations[conv_id],
            system_prompt=system_prompt,
            execute_tool_func=execute_tool
        )

        # Update conversation history with Claude's messages
        conversations[conv_id] = result["messages"]

        # Add assistant's final response
        conversations[conv_id].append({
            "role": "assistant",
            "content": result["response"]
        })

        return {
            "response": result["response"],
            "tool_used": result.get("tool_used", False),
            "conversation_id": conv_id
        }

    except Exception as e:
        logger.error(f"❌ Chat failed: {str(e)}")
        return {
            "error": f"Chat failed: {str(e)}",
            "conversation_id": conv_id
        }


@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible models endpoint for Open WebUI"""
    return {
        "object": "list",
        "data": [
            {
                "id": "pantrybot-claude",
                "object": "model",
                "created": 1677649963,
                "owned_by": "pantrybot",
                "permission": [],
                "root": "pantrybot-claude",
                "parent": None,
            }
        ]
    }


@app.post("/v1/chat/completions")
async def openai_chat_completions(request: dict):
    """
    OpenAI-compatible chat endpoint for Open WebUI
    Converts OpenAI format to Claude format, calls Claude API directly with full context
    """
    logger.info(f"💬 OpenAI-compatible chat request received")

    # Extract messages from OpenAI format
    messages = request.get("messages", [])

    if not messages:
        return {"error": "No messages provided"}

    # Convert OpenAI messages to Claude format (filter out system messages, keep user/assistant)
    claude_messages = []
    for msg in messages:
        if msg["role"] in ["user", "assistant"]:
            claude_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    if not claude_messages:
        return {"error": "No valid messages found"}

    # System prompt
    system_prompt = """You are PantryBot, a helpful cooking assistant for a busy stay-at-home mom.

You have access to:
- The family's real pantry inventory (via Grocy)
- Recipe search (via Spoonacular API)
- Saved family recipes

CRITICAL INSTRUCTIONS:
When someone asks about recipes or "what can I make?":
1. Use get_pantry_items to check what they have available
2. Use search_recipes_by_ingredients ONCE with 3-5 main ingredients to find recipe options
   (Don't do multiple searches - just pick the key ingredients like "salmon, rice, tomatoes")
3. IMMEDIATELY present all recipe options with:
   - Recipe title
   - Match percentage (e.g., "92% match" - this shows how much of the recipe they can make with current ingredients)
   - What missing ingredients they'd need to buy (if any)
   - Brief description of why it's a good choice
4. Sort your presentation by match percentage (highest first) so best options are at the top
5. When they choose one, use get_recipe_details to get the full recipe with instructions
6. Present the complete recipe clearly (ingredients + step-by-step instructions)

IMPORTANT FORMATTING:
After you call search_recipes_by_ingredients, YOU MUST present options like this:
"Here are your best options (sorted by what you have in stock):

1. **Salmon Cakes - 92% match** ⭐
   Missing: panko breadcrumbs
   Perfect for using your canned salmon!

2. **Salmon Pasta - 67% match**
   Missing: pasta, parmesan cheese, cream
   A bit more shopping needed but delicious!"

The match percentage helps users decide if they can make it NOW or need to shop first.

Be warm, practical, and conversational. This is for busy meal planning, so keep it simple and helpful."""

    try:
        # Call Claude directly with full conversation history
        result = await call_claude_with_tools(
            client=claude_client,
            model=CLAUDE_MODEL,
            messages=claude_messages,
            system_prompt=system_prompt,
            execute_tool_func=execute_tool
        )

        # Convert to OpenAI format with unique ID for conversation tracking
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": "pantrybot-claude",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result["response"]
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }

    except Exception as e:
        logger.error(f"❌ Chat failed: {str(e)}")
        return {"error": f"Chat failed: {str(e)}"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
