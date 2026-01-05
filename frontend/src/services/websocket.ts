/**
 * WebSocket service for real-time chat
 */

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
  recipes?: Recipe[];
}

export interface Recipe {
  id: number;
  title: string;
  image: string;
  matchPercentage: number;
  usedIngredients: number;
  missedIngredients: string[];
  readyInMinutes?: number;
  servings?: number;
}

export interface ToolActivity {
  name: string;
  status: 'executing' | 'completed' | 'failed';
}

type MessageHandler = (message: ChatMessage) => void;
type TypingHandler = (isTyping: boolean) => void;
type ToolActivityHandler = (activity: ToolActivity) => void;
type RecipesHandler = (recipes: Recipe[]) => void;
type ErrorHandler = (error: string) => void;
type ConnectedHandler = (conversationId: string) => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private conversationId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  // Event handlers
  private onMessageHandler: MessageHandler | null = null;
  private onTypingHandler: TypingHandler | null = null;
  private onToolActivityHandler: ToolActivityHandler | null = null;
  private onRecipesHandler: RecipesHandler | null = null;
  private onErrorHandler: ErrorHandler | null = null;
  private onConnectedHandler: ConnectedHandler | null = null;

  constructor() {
    // Get WebSocket URL from environment or use default
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_BACKEND_WS || `${protocol}//${window.location.hostname}:8080`;
    this.url = `${host}/ws`;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    console.log('🔌 Connecting to WebSocket:', this.url);

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('✅ WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        console.error('❌ Error parsing WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      console.log('🔌 WebSocket disconnected');
      this.attemptReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      this.onErrorHandler?.('WebSocket connection error');
    };
  }

  private handleMessage(data: any): void {
    switch (data.type) {
      case 'conversation_started':
        this.conversationId = data.conversationId;
        this.onConnectedHandler?.(data.conversationId);
        break;

      case 'message':
        if (data.message) {
          this.onMessageHandler?.(data.message);
        }
        break;

      case 'typing':
        this.onTypingHandler?.(data.value);
        break;

      case 'tool_activity':
        if (data.tool) {
          this.onToolActivityHandler?.(data.tool);
        }
        break;

      case 'recipes':
        if (data.recipes) {
          this.onRecipesHandler?.(data.recipes);
        }
        break;

      case 'error':
        this.onErrorHandler?.(data.error);
        break;

      default:
        console.warn('Unknown message type:', data.type);
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('❌ Max reconnection attempts reached');
      this.onErrorHandler?.('Unable to connect to server');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * this.reconnectAttempts;

    console.log(`🔄 Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      this.connect();
    }, delay);
  }

  sendMessage(message: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.onErrorHandler?.('Not connected to server');
      return;
    }

    this.ws.send(
      JSON.stringify({
        type: 'chat',
        message,
      })
    );
  }

  newConversation(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    this.ws.send(
      JSON.stringify({
        type: 'new_conversation',
      })
    );
  }

  // Event handler setters
  onMessage(handler: MessageHandler): void {
    this.onMessageHandler = handler;
  }

  onTyping(handler: TypingHandler): void {
    this.onTypingHandler = handler;
  }

  onToolActivity(handler: ToolActivityHandler): void {
    this.onToolActivityHandler = handler;
  }

  onRecipes(handler: RecipesHandler): void {
    this.onRecipesHandler = handler;
  }

  onError(handler: ErrorHandler): void {
    this.onErrorHandler = handler;
  }

  onConnected(handler: ConnectedHandler): void {
    this.onConnectedHandler = handler;
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  getConversationId(): string | null {
    return this.conversationId;
  }
}

// Singleton instance
let wsInstance: WebSocketService | null = null;

export function getWebSocketService(): WebSocketService {
  if (!wsInstance) {
    wsInstance = new WebSocketService();
  }
  return wsInstance;
}
