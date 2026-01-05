#!/usr/bin/env python3
"""
PantryBot CLI Client for Mac
- Connects to PantryBot MCP Server (Windows) for Grocy operations
- Saves recipes locally on Mac
"""

import sys
import json
import argparse
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import httpx


class RecipeManager:
    """Handles local recipe storage on Mac"""

    def __init__(self, recipe_dir: Path):
        self.recipe_dir = recipe_dir
        self.recipe_dir.mkdir(parents=True, exist_ok=True)

    def save_recipe(self, recipe_name: str, recipe_content: str) -> Dict[str, Any]:
        """Save a recipe to local filesystem"""
        safe_name = recipe_name.lower().replace(" ", "_").replace("/", "_")
        if not safe_name.endswith(".txt"):
            safe_name += ".txt"

        recipe_path = self.recipe_dir / safe_name

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

    def get_recipe(self, recipe_name: str) -> Dict[str, Any]:
        """Read a recipe from local filesystem"""
        safe_name = recipe_name.lower().replace(" ", "_")
        if not safe_name.endswith(".txt"):
            safe_name += ".txt"

        recipe_path = self.recipe_dir / safe_name

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
                           for f in self.recipe_dir.glob("*.txt")]
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

    def list_recipes(self) -> Dict[str, Any]:
        """List all local recipes"""
        try:
            recipes = []
            if self.recipe_dir.exists():
                for recipe_file in sorted(self.recipe_dir.glob("*.txt")):
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


class PantryBotClient:
    """CLI client for PantryBot"""

    def __init__(self, server_url: str, recipe_dir: Path):
        self.server_url = server_url.rstrip('/')
        self.conversation_id = None
        self.recipe_manager = RecipeManager(recipe_dir)

    def check_connection(self) -> bool:
        """Test connection to PantryBot server"""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.server_url}/")
                response.raise_for_status()
                data = response.json()
                print(f"✅ Connected to {data.get('service', 'PantryBot')}")
                print(f"   Grocy: {data.get('grocy_url')}")
                print(f"   Ollama: {data.get('ollama_host')} ({data.get('ollama_model')})")
                print(f"   Local Recipes: {self.recipe_manager.recipe_dir}")
                return True
        except Exception as e:
            print(f"❌ Failed to connect to PantryBot server: {e}")
            print(f"   Make sure Docker is running on Windows at {self.server_url}")
            return False

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool - either locally (recipes) or remotely (Grocy)"""

        # Handle recipe operations locally on Mac
        if tool_name == "save_recipe":
            return self.recipe_manager.save_recipe(
                parameters.get("recipe_name", ""),
                parameters.get("recipe_content", "")
            )

        elif tool_name == "get_recipe":
            return self.recipe_manager.get_recipe(parameters.get("recipe_name", ""))

        elif tool_name == "list_recipes":
            return self.recipe_manager.list_recipes()

        # Handle Grocy operations remotely via MCP server
        else:
            try:
                with httpx.Client(timeout=60.0) as client:  # 1 minute for API calls
                    response = client.post(
                        f"{self.server_url}/tools/execute",
                        json={"tool": tool_name, "parameters": parameters}
                    )
                    response.raise_for_status()
                    return response.json()
            except Exception as e:
                return {"success": False, "error": f"Failed to execute tool: {str(e)}"}

    def chat(self, message: str) -> None:
        """Send a chat message to PantryBot"""
        try:
            with httpx.Client(timeout=300.0) as client:  # 5 minutes for slow responses
                payload = {"message": message}
                if self.conversation_id:
                    payload["conversation_id"] = self.conversation_id

                print(f"\n🤖 Thinking...\n")

                response = client.post(
                    f"{self.server_url}/chat",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

                # Store conversation ID
                self.conversation_id = data.get("conversation_id")

                # Handle errors
                if "error" in data:
                    print(f"❌ Error: {data['error']}\n")
                    return

                # Check if Llama wants to use a tool
                assistant_message = data.get("response", "")
                tool_call = self.parse_tool_call(assistant_message)

                if tool_call:
                    tool_name = tool_call.get("tool")
                    params = tool_call.get("parameters", {})

                    print(f"🔧 Using tool: {tool_name}")

                    # Execute tool (local or remote)
                    tool_result = self.execute_tool(tool_name, params)

                    # Send tool result back to Llama for final response
                    result_message = f"Tool '{tool_name}' returned: {json.dumps(tool_result)}\n\nProvide a natural response to the user."

                    response = client.post(
                        f"{self.server_url}/chat",
                        json={
                            "message": result_message,
                            "conversation_id": self.conversation_id
                        }
                    )
                    response.raise_for_status()
                    final_data = response.json()

                    final_message = final_data.get("response", "")
                    print(f"\n{final_message}\n")
                else:
                    # No tool needed
                    print(f"\n{assistant_message}\n")

        except httpx.TimeoutException:
            print("❌ Request timed out. The server might be busy.\n")
        except httpx.HTTPError as e:
            print(f"❌ HTTP Error: {e}\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")

    def parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse tool call from Llama response"""
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                tool_call = json.loads(json_str)
                if "tool" in tool_call:
                    return tool_call
        except:
            pass
        return None

    def list_tools(self) -> None:
        """List available tools"""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.server_url}/tools/list")
                response.raise_for_status()
                data = response.json()

                print("\n📦 Available Tools:\n")

                # Show Grocy tools (from server)
                print("  Grocy Operations (via MCP Server):")
                for tool in data.get("tools", []):
                    if tool['name'] not in ['save_recipe', 'get_recipe', 'list_recipes']:
                        print(f"    • {tool['name']}")
                        print(f"      {tool['description']}")
                        if tool.get("parameters"):
                            print(f"      Parameters: {', '.join(tool['parameters'])}")
                        print()

                # Show local recipe tools
                print("  Recipe Operations (Local on Mac):")
                print(f"    • save_recipe")
                print(f"      Save a recipe to {self.recipe_manager.recipe_dir}")
                print(f"      Parameters: recipe_name, recipe_content")
                print()
                print(f"    • get_recipe")
                print(f"      Retrieve a saved recipe")
                print(f"      Parameters: recipe_name")
                print()
                print(f"    • list_recipes")
                print(f"      List all saved recipes")
                print()

        except Exception as e:
            print(f"❌ Failed to list tools: {e}\n")

    def run_interactive(self) -> None:
        """Run interactive chat mode"""
        print("=" * 60)
        print("🥘 PantryBot CLI")
        print("=" * 60)
        print("Server:", self.server_url)
        print("Recipes:", self.recipe_manager.recipe_dir)
        print("\nCommands:")
        print("  /tools     - List available tools")
        print("  /recipes   - List saved recipes")
        print("  /new       - Start new conversation")
        print("  /quit      - Exit")
        print("\nOr just type your message to chat!")
        print("=" * 60)

        # Test connection
        if not self.check_connection():
            print("\n⚠️  Continuing anyway, but connection may fail...\n")

        while True:
            try:
                user_input = input("\n💬 You: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ['/quit', '/exit', '/q']:
                    print("\n👋 Goodbye!\n")
                    break

                elif user_input.lower() == '/tools':
                    self.list_tools()
                    continue

                elif user_input.lower() == '/recipes':
                    result = self.recipe_manager.list_recipes()
                    if result.get("success"):
                        print(f"\n📚 You have {result['total_recipes']} saved recipes:\n")
                        for recipe in result.get("recipes", []):
                            print(f"  • {recipe['name']} (modified: {recipe['modified']})")
                        print()
                    else:
                        print(f"\n❌ {result.get('error')}\n")
                    continue

                elif user_input.lower() == '/new':
                    self.conversation_id = None
                    print("✨ Started new conversation\n")
                    continue

                elif user_input.lower() == '/help':
                    print("\n📚 Help:")
                    print("  Just ask questions naturally!")
                    print("  Examples:")
                    print("    - What's in my pantry?")
                    print("    - What can I make with beef tonight?")
                    print("    - Show me my saved recipes")
                    print("    - Save this recipe as 'chili'")
                    print()
                    continue

                # Regular chat
                self.chat(user_input)

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!\n")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")


def main():
    parser = argparse.ArgumentParser(description="PantryBot CLI Client")
    parser.add_argument(
        "--server",
        default="http://192.168.0.83:9999",
        help="PantryBot server URL (default: http://192.168.0.83:9999)"
    )
    parser.add_argument(
        "--recipes",
        default="/Users/jake/Recipes",
        help="Local recipe directory (default: /Users/jake/Recipes)"
    )
    parser.add_argument(
        "--message", "-m",
        help="Send a single message and exit"
    )
    parser.add_argument(
        "--tools",
        action="store_true",
        help="List available tools and exit"
    )
    parser.add_argument(
        "--list-recipes",
        action="store_true",
        help="List saved recipes and exit"
    )

    args = parser.parse_args()

    recipe_dir = Path(args.recipes)
    client = PantryBotClient(args.server, recipe_dir)

    # Handle one-off commands
    if args.tools:
        client.list_tools()
        return

    if args.list_recipes:
        result = client.recipe_manager.list_recipes()
        if result.get("success"):
            print(f"\nYou have {result['total_recipes']} saved recipes:\n")
            for recipe in result.get("recipes", []):
                print(f"  • {recipe['name']} (modified: {recipe['modified']})")
            print()
        else:
            print(f"Error: {result.get('error')}")
        return

    if args.message:
        client.chat(args.message)
        return

    # Default: interactive mode
    client.run_interactive()


if __name__ == "__main__":
    main()
