/**
 * Chat Handler - Orchestrates Claude API with MCP tool calling
 */

import Anthropic from '@anthropic-ai/sdk';
import { getMCPClient } from './mcpClient.js';
import type { MessageParam, Tool } from '@anthropic-ai/sdk/resources/messages.js';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
  recipes?: any[];
  toolCalls?: ToolCall[];
}

export interface ToolCall {
  name: string;
  status: 'executing' | 'completed' | 'failed';
  input?: any;
  output?: any;
}

export interface ChatResponse {
  message: string;
  toolCalls: ToolCall[];
  recipes?: any[];
}

const SYSTEM_PROMPT = `You are PantryBot, a cooking assistant with access to Grocy pantry inventory and Spoonacular recipes.

Recipe Search Priority:
1. FIRST: Check list_saved_recipes() for user's saved Grocy recipes
2. If saved recipes exist and match, suggest those first (user already likes them!)
3. Then supplement with Spoonacular if needed

Tool Selection:
- list_saved_recipes(): Check user's saved recipes in Grocy
- get_saved_recipe(name): Get full details of a saved recipe
- find_recipes(ingredients): Search Spoonacular by ingredients
- search_recipes(query): Search Spoonacular by recipe name

Workflow:
1. Search: Call tools, say "Here are some recipes:" (UI shows cards)
2. Details: When clicked, call get_recipe_instructions() or get_saved_recipe()
3. Save: Use save_recipe_to_grocy_db with ALL fields

Be helpful and concise.`;

// Helper function to extract text from MCP content
function extractTextFromContent(content: any): string {
  if (!content) return '';

  if (Array.isArray(content)) {
    const textContent = content.find((item) => item.type === 'text');
    return textContent ? textContent.text : JSON.stringify(content);
  }

  if (typeof content === 'object' && content.type === 'text') {
    return content.text;
  }

  return JSON.stringify(content);
}

export class ChatHandler {
  private anthropic: Anthropic;

  constructor(apiKey: string) {
    this.anthropic = new Anthropic({
      apiKey,
    });
  }

  async handleChat(
    messages: ChatMessage[],
    onToolActivity?: (toolCall: ToolCall) => void
  ): Promise<ChatResponse> {
    const mcpClient = await getMCPClient();

    // Get available tools from MCP server
    const toolsList = await mcpClient.listTools();
    const claudeTools: Tool[] = toolsList.tools.map((tool) => ({
      name: tool.name,
      description: tool.description || '',
      input_schema: tool.inputSchema as any,
    }));

    // Convert ChatMessage[] to Anthropic MessageParam[] and limit history to last 10 messages
    const recentMessages = messages.slice(-10);
    const anthropicMessages: MessageParam[] = recentMessages.map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));

    const maxIterations = 10;
    const toolCalls: ToolCall[] = [];
    let extractedRecipes: any[] = [];

    for (let iteration = 0; iteration < maxIterations; iteration++) {
      console.log(`🔄 Iteration ${iteration + 1}/${maxIterations}`);

      const response = await this.anthropic.messages.create({
        model: process.env.CLAUDE_MODEL || 'claude-haiku-4-5-20251001',
        max_tokens: 2048,
        system: SYSTEM_PROMPT,
        messages: anthropicMessages,
        tools: claudeTools,
      });

      // Check if Claude wants to use tools
      if (response.stop_reason === 'tool_use') {
        const toolUseBlocks = response.content.filter(
          (block) => block.type === 'tool_use'
        );

        // Execute tools
        const toolResults = await Promise.all(
          toolUseBlocks.map(async (toolUse: any) => {
            const toolCall: ToolCall = {
              name: toolUse.name,
              status: 'executing',
              input: toolUse.input,
            };

            toolCalls.push(toolCall);
            onToolActivity?.(toolCall);

            try {
              const result = await mcpClient.callTool(toolUse.name, toolUse.input);

              // Extract recipe data if this was find_recipes or search_recipes
              if ((toolUse.name === 'find_recipes' || toolUse.name === 'search_recipes') && result.content) {
                const contentText = extractTextFromContent(result.content);
                const toolOutput = JSON.parse(contentText);
                if (toolOutput.recipes) {
                  extractedRecipes = toolOutput.recipes;
                }
              }

              toolCall.status = 'completed';
              toolCall.output = result.content;
              onToolActivity?.(toolCall);

              return {
                type: 'tool_result' as const,
                tool_use_id: toolUse.id,
                content: extractTextFromContent(result.content),
              };
            } catch (error: any) {
              toolCall.status = 'failed';
              toolCall.output = error.message;
              onToolActivity?.(toolCall);

              return {
                type: 'tool_result' as const,
                tool_use_id: toolUse.id,
                content: `Error: ${error.message}`,
                is_error: true,
              };
            }
          })
        );

        // Add assistant response with tool use
        anthropicMessages.push({
          role: 'assistant',
          content: response.content,
        });

        // Add tool results
        anthropicMessages.push({
          role: 'user',
          content: toolResults,
        });

        continue; // Next iteration
      }

      // Final response (no more tools)
      const textContent = response.content
        .filter((block) => block.type === 'text')
        .map((block: any) => block.text)
        .join('\n');

      return {
        message: textContent,
        toolCalls,
        recipes: extractedRecipes.length > 0 ? extractedRecipes : undefined,
      };
    }

    // Hit max iterations
    console.warn('⚠️ Hit max iterations for tool calling');
    return {
      message: 'I apologize, but I encountered an issue processing your request. Please try again.',
      toolCalls,
    };
  }
}
