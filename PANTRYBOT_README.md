# PantryBot - AI-Powered Pantry Management

**Intelligent meal planning and pantry tracking combining Grocy + Spoonacular + Claude AI**

PantryBot helps busy families answer "What's for supper?" by connecting real-time pantry inventory to recipe suggestions and complete meal planning assistance.

---

## 🎯 Features

- ✅ **Real-time Inventory** - Check what's in your pantry via Grocy API
- ✅ **Smart Recipe Search** - Find recipes based on available ingredients (Spoonacular)
- ✅ **Match Percentages** - See how much of each recipe you can make right now
- ✅ **Inventory Tracking** - Add purchases and track consumption automatically
- ✅ **Shopping Lists** - Manage what you need to buy
- ✅ **Recipe Library** - Save and retrieve favorite recipes
- ✅ **Dual Interface** - Browser (Open WebUI) + Claude Desktop (MCP) support

---

## 🏗️ Architecture

PantryBot uses a **hybrid architecture** with two interfaces sharing the same tool implementations:

```
┌──────────────────────────────┐
│   pantry_tools.py            │
│   (Shared Tool Functions)    │
│                              │
│   - Grocy API integration    │
│   - Spoonacular API          │
│   - Recipe management        │
└──────────┬───────────────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼────┐   ┌───▼────┐
│ FastAPI│   │  MCP   │
│ HTTP   │   │ Server │
│ Server │   │        │
└───┬────┘   └───┬────┘
    │             │
┌───▼────┐   ┌───▼────────┐
│  Open  │   │   Claude   │
│ WebUI  │   │  Desktop   │
│(Browser│   │ (MCP Client│
└────────┘   └────────────┘
```

---

## 📦 Installation

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for FastAPI server)
- Grocy instance (self-hosted or cloud)
- Spoonacular API key ([get free tier](https://spoonacular.com/food-api))
- Claude API key (for HTTP server) OR Claude Desktop (for MCP server)

### Setup

1. **Clone/Download Files:**
   ```bash
   cd /path/to/pantrybot
   ```

2. **Configure Environment:**
   Create `.env` file:
   ```bash
   # Grocy API
   GROCY_API_URL=http://192.168.0.83:9283/api
   GROCY_API_KEY=your_grocy_api_key_here

   # Spoonacular API
   SPOONACULAR_API_KEY=your_spoonacular_api_key_here

   # Recipe Storage
   RECIPE_DIR=/app/recipes  # or E:/pantrybot/recipes on Windows

   # Claude API (only for HTTP server)
   CLAUDE_API_KEY=sk-ant-api03-xxx
   CLAUDE_MODEL=claude-sonnet-4-5-20250929

   # HTTP Server Port
   PANTRYBOT_PORT=9999
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Usage

### Option 1: HTTP Server + Open WebUI (Family Use)

**Best for:** Browser-based access, multi-device usage, family members

#### Deploy with Docker:
```bash
docker-compose up -d
```

#### Access:
- Open WebUI: `http://localhost:3004` (or your server IP)
- Select model: `pantrybot-claude`
- Start chatting!

#### Example Conversations:
```
User: What can I make for supper?
Bot: Checking your pantry... Found 28 cans of salmon! Here are 3 recipes:
     1. Salmon Cakes - 92% match ⭐
        Missing: panko breadcrumbs
        Ready in 30 minutes!
```

```
User: I made salmon cakes and used 2 cans of salmon
Bot: ✅ Removed 2 cans of Deming's Red Sockeye from your inventory.
     You now have 26 cans remaining.
```

```
User: I bought 5 gallons of milk at the store
Bot: I see 2 milk products. Which one?
     1. Whole Milk (1 gallon)
     2. 2% Milk (1 gallon)

User: Whole milk
Bot: ✅ Added 5 gallons of Whole Milk to your pantry!
```

---

### Option 2: MCP Server + Claude Desktop (Developer Use)

**Best for:** Using Claude Desktop, development, sharing with MCP ecosystem

#### Configure Claude Desktop:

Edit your Claude Desktop config:
- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "pantrybot": {
      "command": "python",
      "args": ["/Users/jake/Dev/Agent/pantrybot_mcp_server.py"],
      "env": {
        "GROCY_API_URL": "http://192.168.0.83:9283/api",
        "GROCY_API_KEY": "your_key_here",
        "SPOONACULAR_API_KEY": "your_key_here",
        "RECIPE_DIR": "/Users/jake/Dev/Agent/recipes"
      }
    }
  }
}
```

#### Restart Claude Desktop

#### Use with Claude:
```
You: What's in my pantry?
Claude: [Uses get_pantry tool] You have 90 items in stock...

You: Find me salmon recipes
Claude: [Uses find_recipes tool] Here are 3 recipes sorted by match %...

You: I bought groceries today - 3 cans of salmon
Claude: [Uses purchase_groceries tool] Added to your inventory!
```

---

## 🛠️ Available Tools

### Pantry Management
- `get_pantry(category)` - Check inventory
- `get_product(name)` - Get product details
- `use_ingredients(name, amount)` - Track consumption
- `purchase_groceries(name, amount, date, price)` - Add purchases
- `add_to_shopping(name, amount)` - Add to shopping list
- `view_shopping_list()` - See shopping list

### Recipe Discovery
- `find_recipes(ingredients, number)` - Search recipes by ingredients
- `get_recipe_instructions(recipe_id)` - Get full recipe details
- `save_favorite_recipe(name, content)` - Save recipe
- `get_saved_recipe(name)` - Retrieve saved recipe
- `list_saved_recipes()` - List all saved recipes

---

## 📊 API Costs

### Spoonacular
- Free tier: 150 requests/day
- Paid: Starting at $0.004/request
- [Pricing details](https://spoonacular.com/food-api/pricing)

### Claude API (HTTP Server only)
- Sonnet 4.5: ~$3 per million input tokens, ~$15 per million output tokens
- Typical usage: $0.25-$0.50 per extended conversation
- [Pricing details](https://www.anthropic.com/pricing)

**Note:** MCP server uses your Claude Desktop subscription (no additional API costs)

---

## 🔧 Development

### File Structure
```
pantrybot/
├── pantry_tools.py           # Shared tool implementations
├── mcp_http_bridge.py         # FastAPI HTTP server (Open WebUI)
├── pantrybot_mcp_server.py    # True MCP server (Claude Desktop)
├── claude_chat_handler.py     # Claude API integration
├── docker-compose.yml         # Docker orchestration
├── Dockerfile                 # Container definition
├── requirements.txt           # Python dependencies
└── .env                       # Configuration (not in git!)
```

### Adding New Tools

1. **Implement in `pantry_tools.py`:**
   ```python
   async def my_new_tool(param: str) -> dict:
       # Implementation
       return {"success": True, "result": "..."}
   ```

2. **Add to HTTP server (`mcp_http_bridge.py`):**
   ```python
   # Import
   from pantry_tools import my_new_tool

   # Add routing
   elif tool_name == "my_new_tool":
       result = await my_new_tool(params.get("param", ""))
   ```

3. **Add to MCP server (`pantrybot_mcp_server.py`):**
   ```python
   @mcp.tool()
   async def my_new_tool(param: str) -> dict:
       """Tool description for Claude"""
       return await pantry_tools.my_new_tool(param)
   ```

4. **Add tool definition (`claude_chat_handler.py`):**
   ```python
   {
       "name": "my_new_tool",
       "description": "What this tool does",
       "input_schema": {...}
   }
   ```

---

## 🤝 Contributing

This is a personal project, but if you find it useful:
- Report issues
- Suggest features
- Share your experience
- Fork and customize!

---

## 📝 License

MIT License - Feel free to use, modify, and share!

---

## 🙏 Acknowledgments

- **Grocy** - Self-hosted grocery & household management
- **Spoonacular** - Recipe and food API
- **Anthropic Claude** - AI powering the intelligence
- **FastMCP** - Model Context Protocol framework
- **Open WebUI** - Browser-based chat interface

---

## 💡 Future Ideas

- [ ] Voice interface integration
- [ ] Morning meal planning briefings
- [ ] Proactive suggestions for expiring items
- [ ] Meal calendar planning
- [ ] Nutritional tracking
- [ ] Family preference learning
- [ ] Multi-user support with individual preferences

---

**Built with ❤️ using Claude Code**
