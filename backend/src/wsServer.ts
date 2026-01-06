/**
 * WebSocket Server for real-time chat
 */

import { WebSocketServer, WebSocket } from 'ws';
import { Server } from 'http';
import { ChatHandler, ChatMessage, ToolCall } from './chatHandler.js';
import crypto from 'crypto';

interface ClientMessage {
  type: 'chat' | 'new_conversation' | 'get_history';
  message?: string;
  conversationId?: string;
}

interface ServerMessage {
  type: 'message' | 'typing' | 'tool_activity' | 'recipes' | 'error' | 'conversation_started';
  message?: ChatMessage;
  tool?: ToolCall;
  recipes?: any[];
  value?: boolean;
  error?: string;
  conversationId?: string;
}

interface ChatSession {
  conversationId: string;
  messages: ChatMessage[];
  ws: WebSocket;
}

export class ChatWebSocketServer {
  private wss: WebSocketServer;
  private sessions: Map<string, ChatSession> = new Map();
  private chatHandler: ChatHandler;

  constructor(server: Server, claudeApiKey: string) {
    this.wss = new WebSocketServer({ server, path: '/ws' });
    this.chatHandler = new ChatHandler(claudeApiKey);

    this.wss.on('connection', (ws: WebSocket) => {
      console.log('👤 New WebSocket connection');

      // Create new conversation
      const conversationId = crypto.randomUUID();
      const session: ChatSession = {
        conversationId,
        messages: [],
        ws,
      };

      this.sessions.set(conversationId, session);

      // Send conversation ID to client
      this.sendMessage(ws, {
        type: 'conversation_started',
        conversationId,
      });

      // Set up ping/pong to keep connection alive
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.ping();
        } else {
          clearInterval(pingInterval);
        }
      }, 30000); // Ping every 30 seconds

      ws.on('pong', () => {
        // Connection is alive
      });

      ws.on('message', async (data: Buffer) => {
        try {
          const clientMsg: ClientMessage = JSON.parse(data.toString());
          await this.handleClientMessage(ws, clientMsg, conversationId);
        } catch (error: any) {
          console.error('❌ Error handling message:', error);
          this.sendMessage(ws, {
            type: 'error',
            error: error.message,
          });
        }
      });

      ws.on('close', () => {
        console.log('👋 WebSocket connection closed');
        clearInterval(pingInterval);
        this.sessions.delete(conversationId);
      });

      ws.on('error', (error) => {
        console.error('❌ WebSocket error:', error);
      });
    });

    console.log('✅ WebSocket server initialized on /ws');
  }

  private async handleClientMessage(
    ws: WebSocket,
    clientMsg: ClientMessage,
    conversationId: string
  ): Promise<void> {
    const session = this.sessions.get(conversationId);
    if (!session) {
      this.sendMessage(ws, {
        type: 'error',
        error: 'Session not found',
      });
      return;
    }

    switch (clientMsg.type) {
      case 'chat':
        if (!clientMsg.message) {
          this.sendMessage(ws, {
            type: 'error',
            error: 'Message content required',
          });
          return;
        }

        await this.handleChatMessage(session, clientMsg.message);
        break;

      case 'new_conversation':
        // Reset conversation
        session.messages = [];
        this.sendMessage(ws, {
          type: 'conversation_started',
          conversationId: session.conversationId,
        });
        break;

      case 'get_history':
        // Send conversation history (implement if needed)
        break;

      default:
        this.sendMessage(ws, {
          type: 'error',
          error: 'Unknown message type',
        });
    }
  }

  private async handleChatMessage(session: ChatSession, userMessage: string): Promise<void> {
    // Add user message to history
    const userMsg: ChatMessage = {
      role: 'user',
      content: userMessage,
      timestamp: new Date(),
    };

    session.messages.push(userMsg);

    // Send typing indicator
    this.sendMessage(session.ws, {
      type: 'typing',
      value: true,
    });

    try {
      // Call Claude with tool support
      const response = await this.chatHandler.handleChat(
        session.messages,
        (toolCall: ToolCall) => {
          // Send real-time tool activity
          this.sendMessage(session.ws, {
            type: 'tool_activity',
            tool: toolCall,
          });
        }
      );

      // Add assistant message to history
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: response.message,
        timestamp: new Date(),
        recipes: response.recipes,
        toolCalls: response.toolCalls,
      };

      session.messages.push(assistantMsg);

      // Send typing indicator off
      this.sendMessage(session.ws, {
        type: 'typing',
        value: false,
      });

      // Send recipes separately if available (for carousel display)
      if (response.recipes && response.recipes.length > 0) {
        this.sendMessage(session.ws, {
          type: 'recipes',
          recipes: response.recipes,
        });
      }

      // Send assistant message
      this.sendMessage(session.ws, {
        type: 'message',
        message: assistantMsg,
      });
    } catch (error: any) {
      console.error('❌ Chat error:', error);

      this.sendMessage(session.ws, {
        type: 'typing',
        value: false,
      });

      this.sendMessage(session.ws, {
        type: 'error',
        error: error.message,
      });
    }
  }

  private sendMessage(ws: WebSocket, message: ServerMessage): void {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    }
  }

  close(): void {
    this.wss.close();
  }
}
