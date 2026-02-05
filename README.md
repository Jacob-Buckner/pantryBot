# PantryBot

**AI-powered pantry management using [Grocy](https://grocy.info/) and [Spoonacular](https://spoonacular.com/food-api)**

PantryBot lets you manage your household pantry, discover recipes based on what you have, track chores and tasks, and more — all through natural language conversation with Claude.

## Two Ways to Use PantryBot

| | Claude Desktop (MCP Server) | Self-Hosted Web UI (Docker) |
|---|---|---|
| **Interface** | Claude Desktop app | Browser-based chat UI |
| **Cost** | $0 (uses Claude Pro subscription) | ~$20-30/year (Anthropic API credits) |
| **Requirements** | Python 3.8+, Claude Desktop + Pro | Docker & Docker Compose |
| **Best for** | Personal use, already have Claude Pro | Sharing with household, standalone setup |

---

## Option 1: Claude Desktop MCP Server

Use PantryBot as an MCP (Model Context Protocol) server inside the Claude Desktop app. No API costs — runs on your Claude Pro subscription.

### What You Need

- **Claude Desktop App** with Pro subscription
- **Python 3.8+**
- **Grocy** running locally (see [Grocy Setup](#grocy-setup) below)
- **Spoonacular API key** (free tier: 150 requests/day)

### Setup

1. **Create Python virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Grocy API URL/key and Spoonacular key
   ```

3. **Add to Claude Desktop config:**

   Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (see `claude_desktop_config.example.json` for reference):
   ```json
   {
     "mcpServers": {
       "pantrybot": {
         "command": "/path/to/your/venv/bin/python",
         "args": ["/path/to/pantrybot_mcp_server.py"],
         "env": {
           "GROCY_API_URL": "http://localhost:9283/api",
           "GROCY_API_KEY": "your_grocy_api_key",
           "SPOONACULAR_API_KEY": "your_spoonacular_api_key",
           "RECIPE_DIR": "/path/to/data/recipes"
         }
       }
     }
   }
   ```

4. **Restart Claude Desktop** — PantryBot tools will appear automatically.

---

## Option 2: Self-Hosted Web UI (Docker)

A complete containerized setup with a React frontend, Node.js backend, and built-in Grocy instance.

### What You Need

- **Docker & Docker Compose**
- **Anthropic API key** (buy credits at [console.anthropic.com](https://console.anthropic.com))
- **Spoonacular API key** (free tier: 150 requests/day)

### Quick Start

1. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

2. **Start everything:**
   ```bash
   docker-compose up -d
   ```

3. **Access the apps:**
   - **PantryBot Web UI:** http://localhost:3002
   - **Grocy (pantry management):** http://localhost:9283
   - **Backend API:** http://localhost:8080

### Architecture

```
┌─────────────────┐
│  React Frontend │ (Port 3002)
│   (Vite + TS)   │
└────────┬────────┘
         │ WebSocket
┌────────▼────────┐
│  Node.js Backend│ (Port 8080)
│   + MCP Client  │──── spawns ───▶ Python MCP Server (stdio)
└────────┬────────┘
         │
    ┌────▼─────┐
    │  Grocy   │ (Port 9283)
    │ Database │
    └──────────┘
```

### Cost Analysis

- **Model:** Claude Haiku 4.5 ($0.25/M input, $1.25/M output tokens)
- **Per recipe search:** ~$0.02-0.05
- **$5 API credit** = ~100-250 recipe interactions
- **Average family:** 10-20 interactions/week = **~$20-30/year**

Current optimizations:
- Using Haiku instead of Sonnet (12x cheaper)
- Condensed system prompt (78% reduction)
- Limited conversation history (last 10 messages)
- Reduced max output tokens (2048 vs 4096)

### Database Access

The Grocy SQLite database is at:
```
./data/grocy/data/grocy.db
```

---

## Features

### Pantry Management
- Check inventory, filter by category
- Add/remove items from stock
- Track expiring products
- Low stock alerts with auto-add to shopping list

### Recipe Discovery
- Search recipes by ingredients (with match percentage)
- Search recipes by name
- Get full recipe instructions
- Save favorites to Grocy recipe book

### Shopping Lists
- Add items to shopping list
- View current shopping list
- Auto-generate from low stock items

### Household Management
- Chores — track, create, and complete recurring chores
- Tasks — manage one-off to-do items
- Batteries — track charge cycles for household batteries

### Generic API Access
- Direct Grocy API access for anything not covered by built-in tools

---

## Grocy Setup

If you don't already have Grocy running (the Docker Web UI option includes it automatically):

```bash
docker run -d \
  --name grocy \
  -p 9283:80 \
  -e PUID=1000 \
  -e PGID=1000 \
  -e TZ=America/Chicago \
  -v grocy-data:/config \
  linuxserver/grocy:latest
```

Access Grocy at http://localhost:9283 and grab your API key from **Settings > Manage API keys**.

---

## Spoonacular API

Sign up at [spoonacular.com/food-api](https://spoonacular.com/food-api) for a free API key. The free tier provides 150 requests/day, which is more than enough for typical household use.

---

## Support

Self-hosted, no subscription, no telemetry, no ongoing fees.
