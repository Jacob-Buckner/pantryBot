/**
 * MCP Client for PantryBot
 * Communicates with the Python MCP server via stdio transport
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { ListToolsResult, CallToolResult } from '@modelcontextprotocol/sdk/types.js';

export interface MCPTool {
  name: string;
  description?: string;
  inputSchema: {
    type: string;
    properties?: Record<string, any>;
    required?: string[];
  };
}

export class PantryBotMCPClient {
  private client: Client | null = null;
  private transport: StdioClientTransport | null = null;
  private isConnected = false;

  async initialize(): Promise<void> {
    console.log('🔧 Initializing MCP client...');

    // Spawn Python MCP server as child process
    this.transport = new StdioClientTransport({
      command: 'python3',
      args: ['/app/pantrybot_mcp_server.py'],
      env: {
        GROCY_API_URL: process.env.GROCY_API_URL || '',
        GROCY_API_KEY: process.env.GROCY_API_KEY || '',
        SPOONACULAR_API_KEY: process.env.SPOONACULAR_API_KEY || '',
        RECIPE_DIR: '/app/recipes',
      },
    });

    this.client = new Client(
      {
        name: 'pantrybot-web-client',
        version: '1.0.0',
      },
      {
        capabilities: {},
      }
    );

    await this.client.connect(this.transport);
    this.isConnected = true;

    console.log('✅ MCP client connected to PantryBot server');
  }

  async listTools(): Promise<ListToolsResult> {
    if (!this.client || !this.isConnected) {
      throw new Error('MCP client not initialized');
    }

    return await this.client.listTools();
  }

  async callTool(name: string, args: Record<string, any> = {}): Promise<CallToolResult> {
    if (!this.client || !this.isConnected) {
      throw new Error('MCP client not initialized');
    }

    console.log(`🔧 Calling tool: ${name}`, args);

    const result = await this.client.callTool({
      name,
      arguments: args,
    });

    console.log(`✅ Tool ${name} completed`);

    return result;
  }

  async close(): Promise<void> {
    if (this.client && this.isConnected) {
      await this.client.close();
      this.isConnected = false;
      console.log('🔌 MCP client disconnected');
    }
  }

  getConnectionStatus(): boolean {
    return this.isConnected;
  }
}

// Singleton instance
let mcpClientInstance: PantryBotMCPClient | null = null;

export async function getMCPClient(): Promise<PantryBotMCPClient> {
  if (!mcpClientInstance) {
    mcpClientInstance = new PantryBotMCPClient();
    await mcpClientInstance.initialize();
  }
  return mcpClientInstance;
}

export async function closeMCPClient(): Promise<void> {
  if (mcpClientInstance) {
    await mcpClientInstance.close();
    mcpClientInstance = null;
  }
}
