# PantryBot Setup Guide

Complete setup instructions for running PantryBot across your LAN.

## Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│ Windows Server (192.168.0.83)                              │
│                                                             │
│  Docker Containers:                                        │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────────┐   │
│  │  Grocy   │  │  Ollama  │  │  PantryBot MCP Server  │   │
│  │  :9283   │  │  :11434  │  │  :9999 (HTTP Bridge)   │   │
│  └──────────┘  └──────────┘  └────────────────────────┘   │
│                                         ↓                   │
│                              E:\pantrybot\recipes          │
└────────────────────────────┬────────────────────────────────┘
                             │
                        LAN (Network)
                             │
┌────────────────────────────┴────────────────────────────────┐
│ Mac Terminal (or any device)                                │
│                                                              │
│  pantrybot_cli.py → http://192.168.0.83:9999                │
└──────────────────────────────────────────────────────────────┘
```

---

## Part 1: Windows Server Setup (Run Docker Containers)

### Prerequisites

- Windows machine with Docker Desktop installed
- Grocy already running on port 9283
- Ollama already running on port 11434
- E: drive available for recipe storage

### Step 1: Transfer Files to Windows

Transfer these files to your Windows machine (e.g., `C:\pantrybot\`):

```
pantrybot/
├── Dockerfile
├── docker-compose.yml
├── pantry_bot_mcp.py
├── mcp_http_bridge.py
├── requirements.txt
├── .env.example
└── .gitignore
```

### Step 2: Create Recipe Directory

```powershell
# PowerShell
mkdir E:\pantrybot\recipes
```

### Step 3: Configure Environment

```powershell
# Copy example to .env
cp .env.example .env

# Edit .env with your settings
notepad .env
```

**Update `.env` for Windows:**

```bash
GROCY_API_URL=http://192.168.0.83:9283/api
GROCY_API_KEY=AcP3e7ZyYPkT0igwhE2u9aJEEkxRo2VYuGy0x1QhJyhgH47Rfm
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1:8b
RECIPE_DIR=E:/pantrybot/recipes
PANTRYBOT_PORT=9999
```

**Important:** Use forward slashes (`/`) even on Windows in Docker paths!

### Step 4: Build and Run with Docker Compose

```powershell
# Build the container
docker-compose build

# Start the container
docker-compose up -d

# Check it's running
docker ps
```

You should see `pantrybot` container running on port 9999.

### Step 5: Test the Server

```powershell
# Test the health endpoint
curl http://localhost:9999/

# Or from another device on the LAN
curl http://192.168.0.83:9999/
```

Expected response:
```json
{
  "service": "PantryBot MCP Bridge",
  "status": "running",
  "grocy_url": "http://192.168.0.83:9283/api",
  "ollama_host": "http://host.docker.internal:11434",
  "ollama_model": "llama3.1:8b",
  "recipe_dir": "/app/recipes"
}
```

### Troubleshooting Windows Setup

**Container can't reach Ollama:**
- Check Ollama is running: `docker ps` (look for ollama container)
- Verify: `curl http://localhost:11434/api/tags`
- Docker Desktop settings → Resources → Network → Enable host.docker.internal

**Recipe directory not mounted:**
- Check path in docker-compose.yml uses forward slashes
- Verify E: drive exists and has permissions
- Try absolute path: `E:/pantrybot/recipes:/app/recipes`

**Port 9999 already in use:**
- Change `PANTRYBOT_PORT` in `.env` to any available port
- Update Mac CLI to use new port

---

## Part 2: Mac Terminal Setup (CLI Client)

### Prerequisites

- Python 3.8+ installed on Mac
- Network access to Windows server (192.168.0.83)

### Step 1: Install Python Dependencies

```bash
# Install httpx for HTTP requests
pip3 install httpx
```

### Step 2: Test Connection to Windows Server

```bash
# Test that you can reach the server
curl http://192.168.0.83:9999/
```

If this fails:
- Check Windows firewall allows port 9999
- Verify Docker container is running on Windows
- Ping Windows server: `ping 192.168.0.83`

### Step 3: Run PantryBot CLI

```bash
# Make script executable (already done, but just in case)
chmod +x pantrybot_cli.py

# Run interactive mode
./pantrybot_cli.py --server http://192.168.0.83:9999

# Or use default (192.168.0.83:9999)
./pantrybot_cli.py
```

### Step 4: Try It Out!

```
💬 You: What's in my pantry?
🤖 Thinking...
🔧 Used tool: get_pantry_items

You have 98 products in your pantry. Here are some items:
- Ground Beef: 2.5 lbs
- Onions: 3 units
- Tomatoes: 5 units
...

💬 You: What can I make with beef tonight?
🤖 Thinking...

Based on your pantry, here are 3 dinner ideas:
1. Beef Tacos - Ground beef, cheese, onions
2. Chili - Ground beef, beans, tomatoes
3. Beef Stir-fry - Ground beef, onions, vegetables

💬 You: Give me the chili recipe
🤖 [Provides detailed chili recipe]

💬 You: Save that recipe
🤖 Thinking...
🔧 Used tool: save_recipe

Recipe saved successfully to E:\pantrybot\recipes\chili.txt!
```

### CLI Commands

**Interactive mode:**
```bash
./pantrybot_cli.py
```

**Single message:**
```bash
./pantrybot_cli.py -m "What's in my pantry?"
```

**List available tools:**
```bash
./pantrybot_cli.py --tools
```

**Change server URL:**
```bash
./pantrybot_cli.py --server http://192.168.0.100:8888
```

**In-chat commands:**
- `/tools` - List available tools
- `/new` - Start new conversation
- `/help` - Show help
- `/quit` - Exit

---

## Part 3: Usage Examples

### Example 1: Meal Planning

```
You: What can I make with chicken tonight?
Bot: [Calls get_pantry_items, sees chicken in stock]
Bot: Here are 3 recipes:
     1. Chicken Stir-fry
     2. Chicken Tacos
     3. Grilled Chicken Salad

You: Give me the stir-fry recipe
Bot: [Provides full recipe]

You: Save this as chicken stir fry
Bot: [Saves to E:\pantrybot\recipes\chicken_stir_fry.txt]
```

### Example 2: Check Expiring Items

```
You: What's expiring soon?
Bot: [Calls get_pantry_items with category="expiring_soon"]
Bot: These items are expiring within 7 days:
     - Milk: 2 days
     - Lettuce: 4 days
     - Yogurt: 5 days
```

### Example 3: Recipe Management

```
You: What recipes do I have?
Bot: [Calls list_recipes]
Bot: You have 5 saved recipes:
     1. Chili (modified: 2026-01-01)
     2. Taco Seasoning (modified: 2026-01-01)
     3. Chicken Stir Fry (modified: 2026-01-02)
     ...

You: Show me the chili recipe
Bot: [Calls get_recipe, shows full recipe]
```

---

## Part 4: Advanced Configuration

### Running from Other Devices

**From any device on your LAN:**

```bash
# Install Python and httpx
pip install httpx

# Download pantrybot_cli.py to the device
# Run with server IP
python3 pantrybot_cli.py --server http://192.168.0.83:9999
```

### Custom Port Configuration

**Change PantryBot port:**

Edit `.env` on Windows:
```bash
PANTRYBOT_PORT=8888  # Or any available port
```

Rebuild container:
```powershell
docker-compose down
docker-compose up -d
```

Update Mac CLI:
```bash
./pantrybot_cli.py --server http://192.168.0.83:8888
```

### Raspberry Pi Migration (Future)

When you're ready to move to RPi:

1. Transfer all files to RPi
2. Update `.env`:
   ```bash
   RECIPE_DIR=/home/pi/pantrybot/recipes
   ```
3. Run docker-compose on RPi
4. Update Mac CLI to new RPi IP address

---

## Part 5: Troubleshooting

### "Connection refused" from Mac

**Check:**
1. Windows Docker container is running: `docker ps`
2. Windows firewall allows port 9999
3. Can ping Windows from Mac: `ping 192.168.0.83`
4. Test with curl: `curl http://192.168.0.83:9999/`

**Fix Windows Firewall:**
```powershell
# PowerShell (as Administrator)
New-NetFirewallRule -DisplayName "PantryBot" -Direction Inbound -LocalPort 9999 -Protocol TCP -Action Allow
```

### "Tool execution failed"

**Check Grocy connection:**
```bash
curl -H "GROCY-API-KEY: YOUR_KEY" http://192.168.0.83:9283/api/stock
```

**Check Ollama connection (from Windows):**
```powershell
curl http://localhost:11434/api/tags
```

### Recipes not saving

**Check volume mount:**
```powershell
# Windows PowerShell
docker exec pantrybot ls -la /app/recipes

# Should show mounted directory
```

**Check permissions:**
```powershell
# Give Everyone write permissions to E:\pantrybot\recipes
icacls E:\pantrybot\recipes /grant Everyone:F
```

### Container keeps restarting

**Check logs:**
```powershell
docker logs pantrybot
```

Common issues:
- Missing .env file
- Invalid environment variables
- Port already in use

---

## Part 6: Maintenance

### View Logs

```powershell
# Windows
docker logs pantrybot -f  # Follow logs

# Last 100 lines
docker logs pantrybot --tail 100
```

### Restart Container

```powershell
docker-compose restart
```

### Update Code

```powershell
# After changing Python files
docker-compose down
docker-compose build
docker-compose up -d
```

### Backup Recipes

```powershell
# Windows
xcopy E:\pantrybot\recipes E:\backup\pantrybot\recipes /E /I /Y
```

```bash
# Mac (via network share or scp)
scp user@192.168.0.83:E:/pantrybot/recipes/* ./backup/
```

---

## Quick Reference

**Windows Commands:**
```powershell
docker-compose up -d          # Start PantryBot
docker-compose down           # Stop PantryBot
docker-compose logs -f        # View logs
docker ps                     # Check running containers
```

**Mac Commands:**
```bash
./pantrybot_cli.py                          # Interactive mode
./pantrybot_cli.py -m "message"             # Single message
./pantrybot_cli.py --tools                  # List tools
./pantrybot_cli.py --server http://IP:PORT  # Custom server
```

**URLs to Remember:**
- PantryBot: `http://192.168.0.83:9999`
- Grocy: `http://192.168.0.83:9283`
- Ollama: `http://192.168.0.83:11434`

---

## What's Next?

✅ **Working:** Mac CLI → Windows Docker → Grocy + Ollama
✅ **Recipe saving:** E:\pantrybot\recipes
✅ **LAN accessible:** Any device can use the CLI

**Future enhancements:**
- Add shopping list integration
- Meal planning calendar
- Nutrition tracking
- Voice interface
- Mobile app

Enjoy your PantryBot! 🥘
