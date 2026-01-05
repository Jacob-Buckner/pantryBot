# PantryBot Custom Client - Technical Design Document

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose Stack                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Grocy     │  │   PantryBot  │  │   Frontend   │      │
│  │  (existing)  │  │  MCP Server  │  │   (React)    │      │
│  │  Port 9283   │  │              │  │  Port 3000   │      │
│  └──────┬───────┘  └──────────────┘  └──────┬───────┘      │
│         │                                     │               │
│         │          ┌──────────────┐          │               │
│         └──────────┤   Backend    ├──────────┘               │
│                    │  MCP Client  │                          │
│                    │ (Node.js +   │                          │
│                    │  WebSocket)  │                          │
│                    │  Port 8080   │                          │
│                    └──────┬───────┘                          │
│                           │                                   │
│                           ├─── MCP Server (stdio)            │
│                           ├─── Grocy API (HTTP)              │
│                           ├─── Spoonacular API (HTTP)        │
│                           └─── Claude API (HTTP)             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Frontend
- **Framework:** React 18 with TypeScript
- **UI Library:** Tailwind CSS + shadcn/ui components
- **State Management:** Zustand (lightweight, simple)
- **Chat Interface:** react-markdown for message rendering
- **Recipe Carousel:** Swiper.js or embla-carousel
- **HTTP Client:** Axios
- **WebSocket:** native WebSocket API
- **Build Tool:** Vite

### Backend (MCP Client)
- **Runtime:** Node.js 20 LTS
- **Framework:** Express.js
- **WebSocket:** ws library
- **MCP Client:** @modelcontextprotocol/sdk
- **Process Management:** node-pty for MCP server stdio communication
- **API Clients:** axios for Grocy/Spoonacular/Claude
- **Environment:** dotenv for configuration

### Deployment
- **Containerization:** Docker + Docker Compose
- **Reverse Proxy:** Nginx (optional, for production SSL)
- **Data Persistence:** Docker volumes for recipes, conversation history

---

## Frontend Architecture

### Component Hierarchy

```
App
├── Layout
│   ├── Header
│   │   └── Navigation (Chat, Recipes, Grocy, Settings)
│   └── Main
│       └── Router
│           ├── ChatPage
│           │   ├── ChatSidebar (conversation history)
│           │   ├── ChatMessages
│           │   │   ├── MessageBubble (user/assistant)
│           │   │   └── RecipeCard (inline recipe display)
│           │   ├── RecipeCarousel (when multiple recipes returned)
│           │   └── ChatInput
│           ├── RecipeBookPage
│           │   ├── RecipeGrid
│           │   │   └── RecipeCard (saved favorites)
│           │   └── RecipeDetail (modal/drawer)
│           ├── SettingsPage
│           │   ├── ApiKeyInput (Claude, Spoonacular)
│           │   ├── GrocyConnection
│           │   └── Preferences (theme, notifications)
│           └── GrocyPage
│               └── IFrame (embedded Grocy UI)
```

### State Management (Zustand)

```typescript
// stores/chatStore.ts
interface ChatStore {
  messages: Message[];
  currentRecipes: Recipe[];
  isLoading: boolean;
  conversationId: string;

  sendMessage: (content: string) => Promise<void>;
  clearConversation: () => void;
}

// stores/recipeStore.ts
interface RecipeStore {
  savedRecipes: Recipe[];
  currentRecipe: Recipe | null;

  fetchSavedRecipes: () => Promise<void>;
  saveRecipe: (recipe: Recipe) => Promise<void>;
  deleteRecipe: (id: string) => Promise<void>;
}

// stores/settingsStore.ts
interface SettingsStore {
  claudeApiKey: string;
  spoonacularApiKey: string;
  grocyUrl: string;
  grocyApiKey: string;

  updateSettings: (settings: Partial<Settings>) => Promise<void>;
}
```

### Key Components Specification

#### RecipeCard Component
```typescript
interface RecipeCardProps {
  recipe: {
    id: number;
    title: string;
    image: string;
    matchPercentage: number;
    usedIngredients: number;
    missedIngredients: string[];
    readyInMinutes: number;
    servings: number;
  };
  onSelect?: () => void;
  onSave?: () => void;
  compact?: boolean;
}

// Features:
// - Display Spoonacular recipe image
// - Prominent match % badge (color-coded: green >80%, yellow 50-80%, red <50%)
// - Quick glance info: cook time, servings
// - "Missing items" expandable section
// - "Get Recipe" button → fetches full instructions
// - "Save to Favorites" button
// - Responsive: grid on desktop, stack on mobile
```

#### ChatMessages Component
```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  recipes?: Recipe[]; // If message includes recipe results
  toolCalls?: ToolCall[]; // For displaying tool activity
}

// Features:
// - Auto-scroll to latest message
// - Typing indicator when assistant is responding
// - Tool call visualizations (e.g., "Checking your pantry...")
// - Inline recipe cards when recipes are returned
// - Markdown rendering for formatted responses
```

#### RecipeCarousel Component
```typescript
interface RecipeCarouselProps {
  recipes: Recipe[];
  onRecipeSelect: (recipe: Recipe) => void;
}

// Features:
// - Swipeable on mobile, arrows on desktop
// - Shows 1 card on mobile, 3 on tablet, 4 on desktop
// - Sorted by match percentage (best first)
// - Pagination dots
// - "View All" button → opens grid view
```

---

## Backend Architecture

### MCP Client Implementation

The backend acts as a bridge between the frontend and the MCP server, handling:
1. WebSocket connections for real-time chat
2. stdio communication with MCP server
3. Claude API calls with tool orchestration
4. Direct API calls to Grocy/Spoonacular when needed

```typescript
// server/mcpClient.ts
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

class PantryBotMCPClient {
  private client: Client;
  private transport: StdioClientTransport;

  async initialize() {
    // Spawn MCP server as child process
    this.transport = new StdioClientTransport({
      command: 'python3',
      args: ['/app/pantrybot_mcp_server.py'],
      env: {
        GROCY_API_URL: process.env.GROCY_API_URL,
        GROCY_API_KEY: process.env.GROCY_API_KEY,
        SPOONACULAR_API_KEY: process.env.SPOONACULAR_API_KEY,
        RECIPE_DIR: '/app/recipes'
      }
    });

    this.client = new Client({
      name: 'pantrybot-web-client',
      version: '1.0.0'
    }, {
      capabilities: {}
    });

    await this.client.connect(this.transport);
  }

  async listTools() {
    return await this.client.listTools();
  }

  async callTool(name: string, args: any) {
    return await this.client.callTool({ name, arguments: args });
  }
}
```

### WebSocket Chat Handler

```typescript
// server/chatHandler.ts
import Anthropic from '@anthropic-ai/sdk';
import WebSocket from 'ws';

interface ChatSession {
  conversationId: string;
  messages: Message[];
  ws: WebSocket;
}

class ChatHandler {
  private sessions: Map<string, ChatSession> = new Map();
  private anthropic: Anthropic;
  private mcpClient: PantryBotMCPClient;

  async handleMessage(ws: WebSocket, userMessage: string, conversationId: string) {
    const session = this.sessions.get(conversationId);

    // Add user message to history
    session.messages.push({
      role: 'user',
      content: userMessage
    });

    // Send typing indicator
    ws.send(JSON.stringify({ type: 'typing', value: true }));

    // Call Claude API with tools
    let currentMessages = [...session.messages];
    const maxIterations = 10;

    for (let i = 0; i < maxIterations; i++) {
      const response = await this.anthropic.messages.create({
        model: process.env.CLAUDE_MODEL || 'claude-sonnet-4-5-20250929',
        max_tokens: 4096,
        system: this.getSystemPrompt(),
        messages: currentMessages,
        tools: await this.getToolDefinitions()
      });

      // Handle tool use
      if (response.stop_reason === 'tool_use') {
        const toolUseBlocks = response.content.filter(
          block => block.type === 'tool_use'
        );

        // Execute tools via MCP client
        const toolResults = await Promise.all(
          toolUseBlocks.map(async (toolUse) => {
            // Send real-time tool activity to frontend
            ws.send(JSON.stringify({
              type: 'tool_activity',
              tool: toolUse.name,
              status: 'executing'
            }));

            const result = await this.mcpClient.callTool(
              toolUse.name,
              toolUse.input
            );

            ws.send(JSON.stringify({
              type: 'tool_activity',
              tool: toolUse.name,
              status: 'completed'
            }));

            return {
              type: 'tool_result',
              tool_use_id: toolUse.id,
              content: JSON.stringify(result)
            };
          })
        );

        // Add assistant response + tool results to messages
        currentMessages.push({
          role: 'assistant',
          content: response.content
        });

        currentMessages.push({
          role: 'user',
          content: toolResults
        });

        continue; // Next iteration
      }

      // Final response - send to client
      const textContent = response.content
        .filter(block => block.type === 'text')
        .map(block => block.text)
        .join('');

      session.messages.push({
        role: 'assistant',
        content: textContent
      });

      ws.send(JSON.stringify({
        type: 'message',
        message: {
          role: 'assistant',
          content: textContent,
          timestamp: new Date()
        }
      }));

      ws.send(JSON.stringify({ type: 'typing', value: false }));
      break;
    }
  }

  private getSystemPrompt(): string {
    return `You are PantryBot, a helpful cooking assistant for a busy family.

You have access to:
- Real pantry inventory via Grocy
- Recipe search via Spoonacular API
- Saved family recipes

When asked for meal suggestions:
1. Check pantry with get_pantry
2. Search recipes with find_recipes (use 3-5 key ingredients)
3. Present options sorted by match % (best first)
4. When user chooses, get full recipe with get_recipe_instructions
5. Offer to save favorites

IMPORTANT: After calling find_recipes, present results with:
- Recipe title
- Match percentage (prominent)
- Missing ingredients (if any)
- Cook time and servings
- Why it's a good choice

Be warm, practical, and family-friendly.`;
  }

  private async getToolDefinitions() {
    const tools = await this.mcpClient.listTools();

    // Convert MCP tool definitions to Claude format
    return tools.tools.map(tool => ({
      name: tool.name,
      description: tool.description,
      input_schema: tool.inputSchema
    }));
  }
}
```

### REST API Endpoints

```typescript
// server/routes.ts
import express from 'express';

const router = express.Router();

// Health check
router.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    grocy: process.env.GROCY_API_URL,
    mcpServer: 'connected'
  });
});

// Get saved recipes (bypasses MCP for performance)
router.get('/api/recipes', async (req, res) => {
  const result = await mcpClient.callTool('list_saved_recipes', {});
  res.json(result);
});

// Get recipe details
router.get('/api/recipes/:id', async (req, res) => {
  const result = await mcpClient.callTool('get_saved_recipe', {
    recipe_name: req.params.id
  });
  res.json(result);
});

// Save recipe
router.post('/api/recipes', async (req, res) => {
  const { name, content } = req.body;
  const result = await mcpClient.callTool('save_favorite_recipe', {
    recipe_name: name,
    recipe_content: content
  });
  res.json(result);
});

// Get pantry summary (for dashboard widget)
router.get('/api/pantry/summary', async (req, res) => {
  const result = await mcpClient.callTool('get_pantry', {
    category: 'all'
  });
  res.json(result);
});

// Update settings
router.post('/api/settings', async (req, res) => {
  // Store in environment or config file
  // Restart MCP client with new settings
  res.json({ success: true });
});

export default router;
```

---

## WebSocket Protocol

### Client → Server Messages

```typescript
// User sends a chat message
{
  type: 'chat',
  message: string,
  conversationId: string
}

// User starts new conversation
{
  type: 'new_conversation'
}

// User requests conversation history
{
  type: 'get_history',
  conversationId: string
}
```

### Server → Client Messages

```typescript
// Assistant message
{
  type: 'message',
  message: {
    role: 'assistant',
    content: string,
    timestamp: Date,
    recipes?: Recipe[]
  }
}

// Typing indicator
{
  type: 'typing',
  value: boolean
}

// Tool activity (real-time feedback)
{
  type: 'tool_activity',
  tool: string,
  status: 'executing' | 'completed' | 'failed'
}

// Recipe results (special handling for carousel)
{
  type: 'recipes',
  recipes: Recipe[],
  messageId: string
}

// Error
{
  type: 'error',
  message: string
}
```

---

## Docker Compose Configuration

```yaml
version: '3.8'

services:
  # Grocy - Pantry Management
  grocy:
    image: linuxserver/grocy:latest
    container_name: pantrybot-grocy
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/Chicago
    volumes:
      - grocy-data:/config
    ports:
      - "9283:80"
    restart: unless-stopped

  # PantryBot Backend (MCP Client + API)
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: pantrybot-backend
    environment:
      - GROCY_API_URL=http://grocy/api
      - GROCY_API_KEY=${GROCY_API_KEY}
      - SPOONACULAR_API_KEY=${SPOONACULAR_API_KEY}
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - CLAUDE_MODEL=claude-sonnet-4-5-20250929
      - RECIPE_DIR=/app/recipes
      - PORT=8080
    volumes:
      - recipe-data:/app/recipes
      - conversation-data:/app/conversations
    ports:
      - "8080:8080"
    depends_on:
      - grocy
    restart: unless-stopped

  # PantryBot Frontend (React UI)
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    container_name: pantrybot-frontend
    environment:
      - VITE_BACKEND_URL=http://localhost:8080
      - VITE_BACKEND_WS=ws://localhost:8080
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  grocy-data:
  recipe-data:
  conversation-data:
```

---

## User Experience Flow

### First-Time Setup
1. User runs `docker-compose up`
2. Services start: Grocy, Backend, Frontend
3. User navigates to `http://localhost:3000`
4. Frontend detects no API keys configured
5. Redirects to Settings page
6. User enters:
   - Claude API key
   - Spoonacular API key
   - Grocy URL (pre-filled: http://grocy)
   - Grocy API key (from Grocy UI)
7. Backend validates and saves settings
8. User redirected to Chat page

### Typical Chat Session
1. User: "What can I make for supper?"
2. UI shows typing indicator
3. UI shows tool activity: "Checking your pantry..."
4. Tool completes, typing resumes
5. UI shows tool activity: "Searching for recipes..."
6. Tool completes
7. **Recipe carousel appears** with 3-5 recipe cards
8. Each card shows:
   - Spoonacular recipe image
   - Match % badge (e.g., "92% match")
   - Missing items: "panko breadcrumbs"
   - Cook time: "30 min"
9. User clicks on "Salmon Cakes - 92% match"
10. UI shows tool activity: "Getting recipe details..."
11. Full recipe appears in chat:
    - Ingredients list
    - Step-by-step instructions
    - "Save to Favorites" button
12. User clicks "Save to Favorites"
13. Recipe saved, appears in Recipe Book page

### Recipe Book Page
1. User navigates to "Recipes" tab
2. Grid view of saved recipes (3-4 per row)
3. Each card shows:
   - Recipe image
   - Title
   - Last made date
   - Quick tags (dinner, quick meal, etc.)
4. User clicks card → modal opens with full recipe
5. Modal has buttons:
   - "Make This" → opens chat, adds context
   - "Delete"
   - "Share" (copy link)

---

## Data Persistence

### Conversation Storage
```typescript
// conversations/{conversationId}.json
{
  "id": "conv-abc123",
  "created": "2025-01-05T10:30:00Z",
  "updated": "2025-01-05T11:45:00Z",
  "title": "Salmon dinner ideas", // Auto-generated from first message
  "messages": [
    {
      "role": "user",
      "content": "What can I make for supper?",
      "timestamp": "2025-01-05T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Let me check your pantry...",
      "timestamp": "2025-01-05T10:30:15Z",
      "recipes": [...] // Embedded recipe data
    }
  ]
}
```

### Recipe Storage
```typescript
// recipes/{recipe-name}.json
{
  "id": "recipe-123",
  "source": "spoonacular", // or "custom"
  "spoonacularId": 663050,
  "title": "Salmon Cakes",
  "image": "https://spoonacular.com/...",
  "servings": 4,
  "readyInMinutes": 30,
  "ingredients": [...],
  "instructions": [...],
  "savedAt": "2025-01-05T11:00:00Z",
  "timesCooked": 3,
  "lastCooked": "2025-01-05T18:30:00Z",
  "tags": ["dinner", "seafood", "quick"]
}
```

---

## Mobile Responsiveness

### Breakpoints
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

### Mobile Optimizations
1. **Chat Page:**
   - Full-screen chat (no sidebar)
   - Hamburger menu for conversation history
   - Recipe cards: 1 per view in carousel
   - Sticky chat input at bottom

2. **Recipe Book:**
   - Single column grid
   - Larger touch targets
   - Swipe to delete recipes

3. **Settings:**
   - Vertical form layout
   - Larger input fields
   - Native mobile keyboard support

---

## Performance Considerations

### Frontend
- Code splitting by route (lazy load pages)
- Image lazy loading for recipe images
- Virtual scrolling for long conversation history
- Debounced search in recipe book
- Service worker for offline recipe viewing

### Backend
- Connection pooling for database
- Redis cache for Spoonacular API responses (reduce API calls)
- WebSocket connection reuse
- Conversation history pagination (load last 50 messages)

### Docker
- Multi-stage builds for smaller images
- Frontend: nginx alpine (< 50 MB)
- Backend: node:20-alpine (< 200 MB)
- Shared volumes for data persistence

---

## Security

### API Key Management
- Store in .env file (not in code)
- Backend validates keys on startup
- Frontend never sees API keys
- Settings endpoint requires authentication (future: add user auth)

### CORS
- Frontend configured to only accept requests from allowed origins
- WebSocket origin validation

### Input Validation
- Sanitize all user inputs
- Validate recipe IDs before fetching
- Rate limiting on API endpoints (prevent abuse)

---

## Development Phases

### Phase 1: Core Infrastructure (Week 1)
- [x] Backend MCP client implementation
- [x] WebSocket chat handler
- [x] Basic Express API
- [x] Frontend React scaffolding
- [x] Chat UI with WebSocket connection
- [x] Docker compose setup

### Phase 2: Recipe Features (Week 2)
- [ ] Recipe card component
- [ ] Recipe carousel
- [ ] Recipe book page
- [ ] Save/delete recipes
- [ ] Spoonacular image integration
- [ ] Match percentage display

### Phase 3: Polish & Settings (Week 3)
- [ ] Settings page with API key inputs
- [ ] Grocy iframe integration
- [ ] Conversation history sidebar
- [ ] Mobile responsive design
- [ ] Error handling & loading states
- [ ] Toast notifications

### Phase 4: Advanced Features (Week 4)
- [ ] Recipe search/filter in book
- [ ] Recipe tags & categorization
- [ ] "Make this recipe" → track inventory
- [ ] Shopping list integration
- [ ] Export recipes to PDF
- [ ] Dark mode

---

## File Structure

```
pantrybot-client/
├── backend/
│   ├── src/
│   │   ├── mcpClient.ts         # MCP server communication
│   │   ├── chatHandler.ts       # Claude API + WebSocket
│   │   ├── routes.ts            # REST API endpoints
│   │   ├── wsServer.ts          # WebSocket server setup
│   │   └── index.ts             # Express app entry point
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile.backend
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatMessages.tsx
│   │   │   │   ├── ChatInput.tsx
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   └── TypingIndicator.tsx
│   │   │   ├── recipes/
│   │   │   │   ├── RecipeCard.tsx
│   │   │   │   ├── RecipeCarousel.tsx
│   │   │   │   ├── RecipeGrid.tsx
│   │   │   │   └── RecipeDetail.tsx
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Navigation.tsx
│   │   │   │   └── Layout.tsx
│   │   │   └── settings/
│   │   │       └── SettingsForm.tsx
│   │   ├── pages/
│   │   │   ├── ChatPage.tsx
│   │   │   ├── RecipeBookPage.tsx
│   │   │   ├── SettingsPage.tsx
│   │   │   └── GrocyPage.tsx
│   │   ├── stores/
│   │   │   ├── chatStore.ts
│   │   │   ├── recipeStore.ts
│   │   │   └── settingsStore.ts
│   │   ├── services/
│   │   │   ├── websocket.ts
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── Dockerfile.frontend
├── pantrybot_mcp_server.py      # Existing MCP server
├── pantry_tools.py               # Existing tool implementations
├── docker-compose.yml            # Complete stack
├── .env.example
└── README.md
```

---

## Advantages Over Claude Desktop

| Feature | Claude Desktop | Custom Client |
|---------|---------------|---------------|
| Visual Recipe Cards | ❌ Text only | ✅ Images + match % |
| Recipe Carousel | ❌ No | ✅ Swipeable cards |
| Recipe Book | ❌ No | ✅ Dedicated page |
| Grocy Integration | ❌ Links only | ✅ Embedded UI |
| Mobile Friendly | ⚠️ Desktop only | ✅ Responsive design |
| Family Access | ❌ Individual app | ✅ Web browser |
| Conversation History | ✅ Built-in | ✅ Persistent |
| Tool Activity | ⚠️ Hidden | ✅ Real-time display |
| Recipe Images | ❌ No | ✅ Spoonacular photos |
| One-Click Deploy | ❌ Manual setup | ✅ docker-compose up |

---

## Next Steps

1. Review this design document
2. Confirm tech stack choices (React vs Vue, Node vs Python backend)
3. Begin Phase 1 implementation
4. Set up development environment
5. Build backend MCP client first (can test with Postman)
6. Build frontend incrementally (chat → recipes → settings)

Ready to start building? Let me know if you want to adjust any architectural decisions or proceed with implementation!
