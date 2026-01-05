# PantryBot Custom Client

**AI-Powered Meal Planning with Custom Web Interface**

A complete meal planning system combining Grocy (pantry management) + Spoonacular (recipes) + Claude AI with a beautiful, custom web interface designed specifically for family meal planning.

## Features

- **Real-time Chat Interface** - Natural conversation with Claude about meal planning
- **Visual Recipe Cards** - Spoonacular recipes with professional images
- **Match Percentage Display** - See how much of each recipe you can make right now
- **Recipe Carousel** - Swipeable recipe browsing with the best matches first
- **Recipe Book** - Save and organize your favorite recipes
- **Pantry Integration** - Direct connection to your Grocy instance
- **WebSocket Real-time Updates** - See tool activity as it happens
- **Mobile Responsive** - Works great on phones, tablets, and desktops
- **Docker Deployment** - One command to run everything

## Architecture

```
┌─────────────────────────────────────────┐
│         Docker Compose Stack            │
├─────────────────────────────────────────┤
│  Grocy (Port 9283)                      │
│  Backend (Port 8080)                    │
│  Frontend (Port 3000)                   │
└─────────────────────────────────────────┘

Backend:
- Node.js + Express + WebSocket
- MCP Client (connects to Python MCP server)
- Claude API integration
- REST API for recipes/pantry

Frontend:
- React 18 + TypeScript
- Tailwind CSS
- Zustand state management
- Real-time WebSocket connection
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Grocy instance (or use the bundled one)
- Claude API key
- Spoonacular API key (free tier available)

### Installation

1. **Clone the repository**
   ```bash
   cd pantryBot
   ```

2. **Create `.env` file**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` with your API keys**
   ```bash
   # Grocy
   GROCY_API_KEY=your_grocy_api_key_here

   # Spoonacular
   SPOONACULAR_API_KEY=your_spoonacular_api_key_here

   # Claude
   CLAUDE_API_KEY=your_claude_api_key_here
   ```

4. **Start everything**
   ```bash
   docker-compose up -d
   ```

5. **Access the app**
   - **PantryBot UI:** http://localhost:3000
   - **Grocy:** http://localhost:9283
   - **Backend API:** http://localhost:8080

### First Time Setup

1. Open Grocy at http://localhost:9283
2. Create your Grocy admin account
3. Go to Settings → API → Generate API key
4. Copy the API key into your `.env` file
5. Restart the backend: `docker-compose restart backend`

## Usage

### Chat Interface

Ask natural questions like:
- "What can I make for supper?"
- "Find me salmon recipes"
- "I bought 3 cans of salmon today"
- "Show me recipes I can make right now"

The bot will:
1. Check your pantry inventory
2. Search for matching recipes
3. Display recipe cards with match percentages
4. Show what you're missing (if anything)
5. Provide full instructions when you choose a recipe

### Recipe Cards

Each recipe card shows:
- **Professional image** from Spoonacular
- **Match percentage** - How much you can make with current ingredients
  - 🟢 Green (80%+): You have almost everything
  - 🟡 Yellow (50-80%): Some shopping needed
  - 🔴 Red (<50%): Significant shopping needed
- **Missing ingredients** - What you need to buy
- **Cook time & servings**

### Recipe Book

- Save favorite recipes from chat
- Browse all saved recipes
- Quick access to full instructions
- Delete recipes you no longer want

## Development

### Project Structure

```
pantryBot/
├── backend/                  # Node.js backend
│   ├── src/
│   │   ├── mcpClient.ts     # MCP server communication
│   │   ├── chatHandler.ts   # Claude API + tool calling
│   │   ├── wsServer.ts      # WebSocket server
│   │   ├── routes.ts        # REST API endpoints
│   │   └── index.ts         # Express app
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── stores/
│   │   └── App.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── pantrybot_mcp_server.py  # Python MCP server
├── pantry_tools.py           # Shared tool implementations
├── requirements.txt          # Python dependencies
├── docker-compose.yml        # Full stack orchestration
└── README.md                 # This file
```

### Running Locally (without Docker)

**Backend:**
```bash
cd backend
npm install
cp ../.env .env
npm run dev
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**MCP Server:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python pantrybot_mcp_server.py
```

### Multi-Architecture Support

All Docker images support multiple architectures:
- `linux/amd64` - Intel/AMD x64 (most servers, Windows)
- `linux/arm64` - Apple Silicon, ARM servers
- `linux/arm/v7` - Raspberry Pi

Build for specific platform:
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t pantrybot-backend ./backend
```

## API Endpoints

### REST API

- `GET /health` - Health check
- `GET /api/recipes` - List saved recipes
- `GET /api/recipes/:name` - Get specific recipe
- `POST /api/recipes` - Save new recipe
- `GET /api/pantry/summary` - Get pantry summary
- `GET /api/pantry/:category` - Get pantry by category
- `GET /api/shopping` - Get shopping list
- `GET /api/tools` - List available MCP tools

### WebSocket

Connect to `ws://localhost:8080/ws`

**Client → Server:**
```json
{
  "type": "chat",
  "message": "What can I make for supper?"
}
```

**Server → Client:**
```json
{
  "type": "message",
  "message": {
    "role": "assistant",
    "content": "Here are your best options...",
    "recipes": [...]
  }
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROCY_API_URL` | Grocy API endpoint | `http://grocy/api` |
| `GROCY_API_KEY` | Grocy API key | Required |
| `SPOONACULAR_API_KEY` | Spoonacular API key | Required |
| `CLAUDE_API_KEY` | Claude API key | Required |
| `CLAUDE_MODEL` | Claude model to use | `claude-sonnet-4-5-20250929` |
| `PORT` | Backend port | `8080` |

## Troubleshooting

### Backend won't start

**Error:** `CLAUDE_API_KEY is required`
- Make sure `.env` file exists with valid API key

**Error:** `MCP client not initialized`
- Check that Python and dependencies are installed
- Verify `pantrybot_mcp_server.py` exists

### Frontend shows "Disconnected"

- Check backend is running: `docker-compose logs backend`
- Verify WebSocket connection: Browser dev tools → Network → WS

### No recipes returned

**Error:** `Spoonacular API limit reached`
- Free tier: 150 requests/day
- Wait 24 hours or upgrade plan

**Error:** `No matching recipes`
- Try broader ingredient search
- Check pantry has items

## Cost Estimates

### Claude API (Backend)
- **Sonnet 4.5:** ~$3/million input tokens, ~$15/million output tokens
- **Typical conversation:** $0.10-$0.30
- **Monthly estimate (daily use):** $5-$10

### Spoonacular API
- **Free tier:** 150 requests/day (plenty for family use)
- **Paid:** Starting at $0.004/request

## Tech Stack

**Backend:**
- Node.js 20 + TypeScript
- Express + WebSocket (ws)
- @modelcontextprotocol/sdk
- Anthropic SDK

**Frontend:**
- React 18 + TypeScript
- Vite
- Tailwind CSS
- Zustand
- React Router

**Infrastructure:**
- Docker + Docker Compose
- Nginx (frontend)
- Python 3.11 (MCP server)

## Roadmap

### Phase 1 (Complete)
- ✅ Backend MCP client
- ✅ WebSocket chat handler
- ✅ Express REST API
- ✅ React frontend scaffolding
- ✅ Docker compose setup

### Phase 2 (In Progress)
- [ ] Recipe card component
- [ ] Recipe carousel
- [ ] Recipe book page
- [ ] WebSocket integration
- [ ] Recipe save/delete

### Phase 3
- [ ] Settings page with API key inputs
- [ ] Mobile responsive polish
- [ ] Error handling & loading states
- [ ] Toast notifications

### Phase 4
- [ ] Recipe search/filter
- [ ] Recipe tags & categorization
- [ ] Shopping list integration
- [ ] Dark mode

## Contributing

This is a personal project, but contributions welcome:
- Report bugs
- Suggest features
- Submit pull requests
- Share your experience

## License

MIT License - Free to use, modify, and share!

## Acknowledgments

- **Grocy** - Self-hosted grocery management
- **Spoonacular** - Recipe API
- **Anthropic Claude** - AI intelligence
- **FastMCP** - Model Context Protocol framework
- **Built with Claude Code**

---

**Questions?** Open an issue or check the [technical design document](./PANTRYBOT_CUSTOM_CLIENT_DESIGN.md) for more details.
