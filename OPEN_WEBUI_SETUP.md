# Open WebUI Setup Guide for PantryBot

This guide will help you deploy Open WebUI on Windows to replace the Mac CLI client.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ Windows Server (192.168.0.83) - All services in Docker          │
│                                                                   │
│  ┌───────────┐  ┌────────────┐  ┌──────────────────────────┐   │
│  │  Ollama   │  │ PantryBot  │  │  Open WebUI              │   │
│  │  :11434   │  │ MCP Server │  │  :3004                   │   │
│  │           │◄─┤  :9999     │◄─┤  (Browser Interface)     │   │
│  └───────────┘  └────────────┘  └──────────────────────────┘   │
│       │              │                      │                    │
│       └──────────────┴──────────────────────┘                    │
│              pantrybot_network                                   │
│                                                                   │
│  Volumes:                                                        │
│  • E:/ollama-data                                                │
│  • E:/pantrybot/recipes                                          │
│  • E:/pantrybot/open-webui                                       │
└──────────────────────────────────────────────────────────────────┘
                              │
                         LAN (Network)
                              │
┌─────────────────────────────┴─────────────────────────────────────┐
│ Any Device with Browser                                           │
│                                                                    │
│  http://192.168.0.83:3004                                         │
│  • Mac browser                                                    │
│  • iPhone/iPad                                                    │
│  • Windows browser                                                │
│  • Any device on LAN                                              │
└───────────────────────────────────────────────────────────────────┘
```

## Benefits of Open WebUI vs Mac CLI

✅ **No network latency** - Everything runs on Windows Docker network
✅ **Browser-based** - Access from any device (phone, tablet, laptop)
✅ **Visual interface** - Better UX for family members
✅ **Conversation history** - Persistent chat history
✅ **Tool calling built-in** - Native support for function calling
✅ **No timeouts** - Container-to-container communication is instant
✅ **Multi-user** - Multiple family members can have separate accounts

## Part 1: Windows Setup

### Step 1: Create Data Directory

```powershell
# PowerShell on Windows
mkdir E:\pantrybot\open-webui
```

### Step 2: Transfer Updated docker-compose.yml to Windows

Transfer the updated `docker-compose.yml` to your Windows machine at `C:\pantrybot\`.

The new file includes the Open WebUI service:
```yaml
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    ports:
      - "3004:8080"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - WEBUI_SECRET_KEY=your-secret-key-change-this
      - ENABLE_RAG_WEB_SEARCH=false
      - ENABLE_OLLAMA_API=true
    volumes:
      - E:/pantrybot/open-webui:/app/backend/data
    restart: unless-stopped
    depends_on:
      - ollama
      - pantrybot
    networks:
      - pantrybot_network
```

### Step 3: Stop Existing Containers

```powershell
# In C:\pantrybot\
docker-compose down
```

### Step 4: Pull Open WebUI Image

```powershell
# Pull the image first to avoid build errors
docker pull ghcr.io/open-webui/open-webui:main
```

### Step 5: Start All Services

```powershell
# Start all containers (Ollama, PantryBot, Open WebUI)
docker-compose up -d

# Check all containers are running
docker ps
```

You should see 3 containers running:
- `ollama` on port 11434
- `pantrybot` on port 9999
- `open-webui` on port 3004

### Step 6: Check Logs

```powershell
# Check Open WebUI logs
docker logs open-webui

# Should show:
# INFO: Uvicorn running on http://0.0.0.0:8080
```

### Step 7: Test Access

```powershell
# Test from Windows
curl http://localhost:3004

# Should return HTML for Open WebUI login page
```

## Part 2: Initial Setup in Browser

### Step 1: Open Open WebUI

From any device on your LAN:
1. Open browser
2. Go to: `http://192.168.0.83:3004`
3. You should see the Open WebUI welcome screen

### Step 2: Create Admin Account

1. Click "Sign up"
2. Create first account (becomes admin):
   - Name: `Admin` (or your name)
   - Email: `admin@localhost` (can be fake)
   - Password: Your password
3. Click "Create Account"

### Step 3: Verify Ollama Connection

1. Click on your profile (top right)
2. Go to "Settings" → "Connections"
3. Verify Ollama URL is: `http://ollama:11434`
4. Click "Test Connection"
5. Should show: "Connected ✓"
6. You should see your models (llama3.1:8b)

### Step 4: Create a Test Chat

1. Click "New Chat"
2. Select model: `llama3.1:8b`
3. Type: "Hello, how are you?"
4. Verify Llama responds

## Part 3: Install PantryBot Functions

### Step 1: Copy Function Code

1. Open the file `open_webui_pantrybot_function.py` on your Mac
2. Copy the entire contents

### Step 2: Create Function in Open WebUI

1. In Open WebUI, click your profile → "Admin Panel"
2. Go to "Functions" in the sidebar
3. Click "+" (Create New Function)
4. Paste the entire code from `open_webui_pantrybot_function.py`
5. Click "Save"
6. Enable the function (toggle switch)

### Step 3: Test PantryBot Integration

1. Start a new chat
2. Select model: `llama3.1:8b`
3. Type: "What's in my pantry?"
4. Llama should call the `get_pantry_items` function
5. You should see tool execution status in the chat

## Part 4: Create PantryBot System Prompt (Optional)

To make every chat automatically act like PantryBot:

### Option 1: Model Preset

1. Go to "Workspace" → "Models"
2. Find `llama3.1:8b`
3. Click the 3 dots → "Edit"
4. Add System Prompt:

```
You are PantryBot, a helpful cooking assistant. You have access to a pantry management system via these functions:

- get_pantry_items(category): Get current pantry stock from Grocy
- save_recipe(recipe_name, recipe_content): Save recipes to filesystem
- get_recipe(recipe_name): Retrieve saved recipes
- list_recipes(): List all saved recipes
- get_product_info(product_name): Get detailed product information

When users ask "What can I make?", call get_pantry_items() first, analyze available ingredients, then suggest 2-3 recipe ideas. If they want a full recipe, provide detailed instructions.

Always use the actual pantry data from the functions - never hallucinate inventory items!
```

5. Save the preset

### Option 2: Per-Chat System Prompt

1. Start new chat
2. Click "Advanced Settings" (gear icon)
3. Add the same system prompt as above
4. This applies only to that conversation

## Part 5: Usage Examples

### Example 1: What can I make tonight?

```
You: What can I make with beef tonight?

[Open WebUI shows tool execution: get_pantry_items("beef")]

PantryBot: I found these items in your pantry:
- Ground Beef: 2.5 lbs
- Onions: 3 units
- Tomatoes: 5 units
- Cheese: 1 lb

Here are 3 dinner ideas:
1. Beef Tacos
2. Chili
3. Beef Stir-fry

Which would you like the recipe for?

You: Give me the chili recipe

PantryBot: [Provides full recipe]

You: Save that recipe please

[Open WebUI shows tool execution: save_recipe("chili", "...")]

PantryBot: Recipe saved successfully to E:\pantrybot\recipes\chili.txt!
```

### Example 2: What's expiring soon?

```
You: What's expiring soon in my pantry?

[Tool execution: get_pantry_items("expiring_soon")]

PantryBot: These items are expiring within 7 days:
- Milk: expires in 2 days
- Lettuce: expires in 4 days
- Yogurt: expires in 5 days

Would you like recipe suggestions to use these items?
```

### Example 3: Show saved recipes

```
You: What recipes do I have saved?

[Tool execution: list_recipes()]

PantryBot: You have 5 saved recipes:
1. Chili (modified: 2026-01-02)
2. Beef Tacos (modified: 2026-01-02)
3. Taco Seasoning (modified: 2026-01-01)
...

You: Show me the chili recipe

[Tool execution: get_recipe("chili")]

PantryBot: [Displays full recipe content]
```

## Part 6: Troubleshooting

### Open WebUI won't start

**Check logs:**
```powershell
docker logs open-webui
```

**Common issues:**
- Port 3004 in use: Change port in docker-compose.yml
- Missing data directory: `mkdir E:\pantrybot\open-webui`
- Permission issues: Give Everyone write access to E:\pantrybot\open-webui

### Can't access from browser

**Check:**
1. Container is running: `docker ps | grep open-webui`
2. Windows firewall allows port 3004
3. Can ping Windows from other device: `ping 192.168.0.83`
4. Try accessing from Windows first: `http://localhost:3004`

**Add firewall rule:**
```powershell
# PowerShell (as Administrator)
New-NetFirewallRule -DisplayName "Open WebUI" -Direction Inbound -LocalPort 3004 -Protocol TCP -Action Allow
```

### Ollama models not showing

1. Check Ollama connection in Settings → Connections
2. Verify Ollama is running: `docker ps | grep ollama`
3. Test Ollama directly: `docker exec ollama ollama list`
4. Check URL is `http://ollama:11434` (not localhost)

### PantryBot functions not working

**Check PantryBot server:**
```powershell
# Test PantryBot endpoint
curl http://localhost:9999/

# Should return JSON with service info
```

**Check function configuration:**
1. In Open WebUI Admin Panel → Functions
2. Verify function is enabled (toggle switch is ON)
3. Check "Valves" settings:
   - PANTRYBOT_URL should be `http://pantrybot:8000`
   - TIMEOUT should be 30 or higher

**Test function manually:**
1. In function editor, click "Test"
2. Try calling `get_pantry_items(category="all")`
3. Check response for errors

### Functions timing out

Increase timeout in function Valves:
1. Admin Panel → Functions → PantryBot
2. Click "Valves" tab
3. Change TIMEOUT from 30 to 60 or 120
4. Save

### Llama still hallucinating inventory

**Strengthen system prompt:**
```
IMPORTANT: You MUST call get_pantry_items() before suggesting recipes. NEVER make up inventory items. Only use items returned by the get_pantry_items() function. If you don't have inventory data, call the function first.
```

**Use RAG (Optional):**
Enable "Knowledge" feature in Open WebUI to upload reference documents about not hallucinating.

## Part 7: Advanced Features

### Multiple Users

1. Admin Panel → Users → "Add User"
2. Create accounts for family members
3. Each user has separate chat history
4. Shared access to PantryBot functions

### Custom Prompts

Create prompt presets for different tasks:
- "Quick Meal" - Use items expiring soon
- "Meal Planning" - Plan week of meals
- "Leftover Magic" - Use opened containers

### Model Settings

Tune model parameters:
- Temperature: Lower (0.3-0.5) for more consistent tool calling
- Top P: 0.9
- Max tokens: 2048 or higher for long recipes

### Backup and Restore

**Backup:**
```powershell
# Backup Open WebUI data
xcopy E:\pantrybot\open-webui E:\backup\open-webui /E /I /Y
```

**Restore:**
```powershell
# Stop container
docker-compose stop open-webui

# Restore data
xcopy E:\backup\open-webui E:\pantrybot\open-webui /E /I /Y

# Start container
docker-compose start open-webui
```

## Quick Reference

**Access URLs:**
- Open WebUI: `http://192.168.0.83:3004`
- PantryBot API: `http://192.168.0.83:9999`
- Ollama API: `http://192.168.0.83:11434`
- Grocy: `http://192.168.0.83:9283`

**Docker Commands:**
```powershell
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker logs open-webui -f
docker logs pantrybot -f
docker logs ollama -f

# Restart specific service
docker-compose restart open-webui

# Check running containers
docker ps
```

**Data Locations:**
- Recipes: `E:\pantrybot\recipes\`
- Open WebUI data: `E:\pantrybot\open-webui\`
- Ollama models: `E:\ollama-data\`

## What's Next?

✅ **Working:** Open WebUI → Ollama → PantryBot → Grocy
✅ **Accessible:** Any browser on LAN
✅ **No latency:** All on Windows Docker network
✅ **Family-friendly:** Visual interface, no CLI needed

Enjoy PantryBot through your browser! 🥘
