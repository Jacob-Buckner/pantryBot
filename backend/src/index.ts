/**
 * PantryBot Backend Server
 * Express API + WebSocket chat
 */

import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { createServer } from 'http';
import routes from './routes.js';
import { ChatWebSocketServer } from './wsServer.js';
import { getMCPClient, closeMCPClient } from './mcpClient.js';

// Load environment variables
dotenv.config();

const app = express();
const PORT = parseInt(process.env.PORT || '8080', 10);

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request logging
app.use((req, res, next) => {
  console.log(`${req.method} ${req.path}`);
  next();
});

// Routes
app.use(routes);

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    service: 'PantryBot Backend',
    version: '1.0.0',
    endpoints: {
      websocket: '/ws',
      health: '/health',
      recipes: '/api/recipes',
      pantry: '/api/pantry/summary',
      shopping: '/api/shopping',
      tools: '/api/tools',
    },
  });
});

// Create HTTP server
const server = createServer(app);

// Initialize WebSocket server
let wsServer: ChatWebSocketServer;

async function startServer() {
  try {
    // Validate environment variables
    if (!process.env.CLAUDE_API_KEY) {
      throw new Error('CLAUDE_API_KEY is required');
    }

    if (!process.env.GROCY_API_URL) {
      console.warn('⚠️ GROCY_API_URL not set');
    }

    if (!process.env.SPOONACULAR_API_KEY) {
      console.warn('⚠️ SPOONACULAR_API_KEY not set');
    }

    // Initialize MCP client (connects to Python MCP server)
    console.log('🔧 Starting PantryBot Backend...');
    await getMCPClient();

    // Initialize WebSocket server
    wsServer = new ChatWebSocketServer(server, process.env.CLAUDE_API_KEY);

    // Start HTTP server
    server.listen(PORT, () => {
      console.log(`✅ PantryBot Backend running on port ${PORT}`);
      console.log(`   HTTP: http://localhost:${PORT}`);
      console.log(`   WebSocket: ws://localhost:${PORT}/ws`);
      console.log(`   Health: http://localhost:${PORT}/health`);
    });
  } catch (error) {
    console.error('❌ Failed to start server:', error);
    process.exit(1);
  }
}

// Graceful shutdown
async function shutdown() {
  console.log('\n🛑 Shutting down gracefully...');

  if (wsServer) {
    wsServer.close();
  }

  await closeMCPClient();

  server.close(() => {
    console.log('👋 Server closed');
    process.exit(0);
  });

  // Force exit after 10 seconds
  setTimeout(() => {
    console.error('⚠️ Forced shutdown');
    process.exit(1);
  }, 10000);
}

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

// Start the server
startServer();
