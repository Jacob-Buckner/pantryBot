/**
 * REST API Routes
 */

import express, { Request, Response } from 'express';
import { getMCPClient } from './mcpClient.js';

const router = express.Router();

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

// Health check
router.get('/health', async (req: Request, res: Response) => {
  try {
    const mcpClient = await getMCPClient();
    const isConnected = mcpClient.getConnectionStatus();

    res.json({
      status: 'healthy',
      mcpServer: isConnected ? 'connected' : 'disconnected',
      grocy: process.env.GROCY_API_URL || 'not configured',
      timestamp: new Date().toISOString(),
    });
  } catch (error: any) {
    res.status(500).json({
      status: 'unhealthy',
      error: error.message,
    });
  }
});

// Get saved recipes from Grocy
router.get('/api/recipes', async (req: Request, res: Response) => {
  try {
    const mcpClient = await getMCPClient();
    const result = await mcpClient.callTool('call_grocy_api', {
      endpoint: '/objects/recipes',
      method: 'GET'
    });

    const contentText = extractTextFromContent(result.content);
    let recipes = JSON.parse(contentText);

    // Extract image URLs from descriptions and format response
    const formattedRecipes = recipes.map((recipe: any) => {
      const description = recipe.description || '';
      let imageUrl = null;

      // Extract image URL if present
      if (description.includes('Image: ')) {
        const lines = description.split('\n');
        for (const line of lines) {
          if (line.startsWith('Image: ')) {
            imageUrl = line.replace('Image: ', '').trim();
            break;
          }
        }
      }

      return {
        id: recipe.id,
        name: recipe.name,
        description: description,
        servings: recipe.base_servings,
        image_url: imageUrl,
        modified: recipe.row_created_timestamp
      };
    });

    res.json({
      success: true,
      total_recipes: formattedRecipes.length,
      recipes: formattedRecipes
    });
  } catch (error: any) {
    console.error('❌ Error fetching recipes:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get specific recipe by ID from Grocy
router.get('/api/recipes/:id', async (req: Request, res: Response) => {
  try {
    const mcpClient = await getMCPClient();
    const result = await mcpClient.callTool('call_grocy_api', {
      endpoint: `/objects/recipes/${req.params.id}`,
      method: 'GET'
    });

    const contentText = extractTextFromContent(result.content);
    const recipe = JSON.parse(contentText);

    res.json({
      success: true,
      recipe: recipe,
      content: recipe.description
    });
  } catch (error: any) {
    console.error('❌ Error fetching recipe:', error);
    res.status(500).json({ error: error.message });
  }
});

// Save recipe
router.post('/api/recipes', async (req: Request, res: Response) => {
  try {
    const { name, content } = req.body;

    if (!name || !content) {
      return res.status(400).json({ error: 'Name and content required' });
    }

    const mcpClient = await getMCPClient();
    const result = await mcpClient.callTool('save_favorite_recipe', {
      recipe_name: name,
      recipe_content: content,
    });

    const contentText = extractTextFromContent(result.content);
    const resultContent = JSON.parse(contentText);

    res.json(resultContent);
  } catch (error: any) {
    console.error('❌ Error saving recipe:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get pantry summary
router.get('/api/pantry/summary', async (req: Request, res: Response) => {
  try {
    const mcpClient = await getMCPClient();
    const result = await mcpClient.callTool('get_pantry', {
      category: 'all',
    });

    const contentText = extractTextFromContent(result.content);
    const content = JSON.parse(contentText);

    res.json(content);
  } catch (error: any) {
    console.error('❌ Error fetching pantry:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get pantry by category
router.get('/api/pantry/:category', async (req: Request, res: Response) => {
  try {
    const mcpClient = await getMCPClient();
    const result = await mcpClient.callTool('get_pantry', {
      category: req.params.category,
    });

    const contentText = extractTextFromContent(result.content);
    const content = JSON.parse(contentText);

    res.json(content);
  } catch (error: any) {
    console.error('❌ Error fetching pantry:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get shopping list
router.get('/api/shopping', async (req: Request, res: Response) => {
  try {
    const mcpClient = await getMCPClient();
    const result = await mcpClient.callTool('view_shopping_list', {});

    const contentText = extractTextFromContent(result.content);
    const content = JSON.parse(contentText);

    res.json(content);
  } catch (error: any) {
    console.error('❌ Error fetching shopping list:', error);
    res.status(500).json({ error: error.message });
  }
});

// List available MCP tools
router.get('/api/tools', async (req: Request, res: Response) => {
  try {
    const mcpClient = await getMCPClient();
    const tools = await mcpClient.listTools();

    res.json({
      tools: tools.tools.map((tool) => ({
        name: tool.name,
        description: tool.description,
        inputSchema: tool.inputSchema,
      })),
    });
  } catch (error: any) {
    console.error('❌ Error listing tools:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;
