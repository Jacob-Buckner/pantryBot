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

const SYSTEM_PROMPT = `You are PantryBot, a helpful cooking assistant for a busy family.

You have access to:
- Real pantry inventory via Grocy
- Recipe search via Spoonacular API
- Saved family recipes

IMPORTANT - Choose the right recipe search tool:
- User asks for SPECIFIC recipe by name (e.g., "recipe for reuben sandwich", "how to make chicken parmesan")
  → Use search_recipes(query) - searches by recipe name
- User asks "what can I make?" or mentions ingredients they have
  → Use find_recipes(ingredients) - searches by ingredients and shows match %

Workflow:
1. If asking for specific recipe: search_recipes("recipe name")
2. If asking what to make: Check pantry with get_pantry, then find_recipes(ingredients)
3. Present recipe options (with match % if using find_recipes)
4. When user chooses, get full recipe with get_recipe_instructions
5. When user wants to save recipe:
   - ALWAYS use save_recipe_to_grocy_db (NOT save_favorite_recipe!)
   - Call get_recipe_instructions first if you don't have the details
   - Pass ALL fields: recipe_id, recipe_title, servings, ready_in_minutes, ingredients, instructions, AND image_url
   - CRITICAL: Use the 'image' field from get_recipe_instructions as the image_url parameter
   - This stores in Grocy database with pantry integration and Spoonacular image

IMPORTANT: After calling find_recipes, present results with:
- Recipe title
- Match percentage (prominent - this shows how much they can make with current ingredients)
- Missing ingredients (if any)
- Cook time and servings
- Why it's a good choice

Example format after getting recipes:
"Here are your best options (sorted by what you have in stock):

1. **Salmon Cakes - 92% match** ⭐
   Missing: panko breadcrumbs
   Ready in 30 minutes - Perfect for using your canned salmon!

2. **Salmon Pasta - 67% match**
   Missing: pasta, parmesan cheese, cream
   A bit more shopping needed but delicious!"

Be warm, practical, and family-friendly. Keep it simple and helpful.`;

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

    // Convert ChatMessage[] to Anthropic MessageParam[]
    const anthropicMessages: MessageParam[] = messages.map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));

    const maxIterations = 10;
    const toolCalls: ToolCall[] = [];
    let extractedRecipes: any[] = [];

    for (let iteration = 0; iteration < maxIterations; iteration++) {
      console.log(`🔄 Iteration ${iteration + 1}/${maxIterations}`);

      const response = await this.anthropic.messages.create({
        model: process.env.CLAUDE_MODEL || 'claude-sonnet-4-5-20250929',
        max_tokens: 4096,
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
