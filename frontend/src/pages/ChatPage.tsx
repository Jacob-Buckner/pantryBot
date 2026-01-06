import { useState, useEffect, useRef } from 'react';
import { getWebSocketService, ChatMessage, Recipe } from '../services/websocket';
import RecipeCarousel from '../components/recipes/RecipeCarousel';
import ReactMarkdown from 'react-markdown';

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [currentRecipes, setCurrentRecipes] = useState<Recipe[]>([]);
  const [toolActivity, setToolActivity] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const ws = getWebSocketService();

  useEffect(() => {
    // Set up event handlers BEFORE connecting
    ws.onConnected((conversationId) => {
      console.log('Connected with conversation ID:', conversationId);
      setIsConnected(true);
    });

    ws.onMessage((message) => {
      setMessages((prev) => [...prev, message]);
      setIsTyping(false);
      setToolActivity('');
    });

    ws.onTyping((typing) => {
      setIsTyping(typing);
      if (!typing) {
        setToolActivity('');
      }
    });

    ws.onToolActivity((activity) => {
      if (activity.status === 'executing') {
        setToolActivity(`${getToolDisplayName(activity.name)}...`);
      }
    });

    ws.onRecipes((recipes) => {
      setCurrentRecipes(recipes);
    });

    ws.onError((error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    });

    // Check if already connected and update state
    if (ws.isConnected()) {
      setIsConnected(true);
      const convId = ws.getConversationId();
      if (convId) {
        console.log('Already connected with conversation ID:', convId);
      }
    }

    // Connect to WebSocket
    ws.connect();

    // Cleanup
    return () => {
      ws.disconnect();
    };
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping, currentRecipes]);

  const handleSend = () => {
    if (!input.trim() || !isConnected) return;

    // Add user message to UI immediately
    const userMessage: ChatMessage = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setCurrentRecipes([]); // Clear previous recipes

    // Send to server
    ws.sendMessage(input);
  };

  const handleRecipeSelect = (recipe: Recipe) => {
    // Ask for full recipe instructions
    const message = `Get me the full recipe for "${recipe.title}"`;
    ws.sendMessage(message);

    // Add user message to UI
    setMessages((prev) => [
      ...prev,
      {
        role: 'user',
        content: message,
        timestamp: new Date(),
      },
    ]);

    setCurrentRecipes([]); // Clear carousel
  };

  const getToolDisplayName = (toolName: string): string => {
    const names: Record<string, string> = {
      get_pantry: 'Checking your pantry',
      find_recipes: 'Searching for recipes',
      get_recipe_instructions: 'Getting recipe details',
      use_ingredients: 'Updating inventory',
      purchase_groceries: 'Adding to pantry',
      save_favorite_recipe: 'Saving recipe',
    };
    return names[toolName] || toolName;
  };

  return (
    <div className="max-w-5xl mx-auto h-[calc(100vh-4rem)]">
      <div className="flex flex-col h-full p-4">
        {/* Connection Status */}
        <div className="mb-4">
          <span
            className={`inline-flex items-center px-3 py-1 rounded-full text-sm ${
              isConnected
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {isConnected ? '● Connected' : '○ Disconnected'}
          </span>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto bg-white rounded-lg shadow-sm p-4 mb-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-20">
              <h2 className="text-2xl font-semibold mb-2">Welcome to PantryBot!</h2>
              <p className="mb-4">Ask me "What can I make for supper?" to get started.</p>
              <div className="text-sm text-gray-400">
                <p>I can help you:</p>
                <ul className="mt-2 space-y-1">
                  <li>• Find recipes based on what's in your pantry</li>
                  <li>• Track your grocery purchases</li>
                  <li>• Manage your shopping list</li>
                  <li>• Save your favorite recipes</li>
                </ul>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg, idx) => (
                <div key={idx}>
                  <div
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[70%] rounded-lg px-4 py-2 ${
                        msg.role === 'user'
                          ? 'bg-primary-600 text-white'
                          : 'bg-gray-100 text-gray-900'
                      }`}
                    >
                      <ReactMarkdown className="prose prose-sm max-w-none">
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  </div>

                  {/* Show recipe carousel if this message has recipes */}
                  {msg.recipes && msg.recipes.length > 0 && (
                    <div className="mt-4">
                      <RecipeCarousel
                        recipes={msg.recipes}
                        onRecipeSelect={handleRecipeSelect}
                      />
                    </div>
                  )}
                </div>
              ))}

              {/* Recipe carousel for current search (before assistant responds) */}
              {currentRecipes.length > 0 && (
                <div className="mt-4">
                  <RecipeCarousel
                    recipes={currentRecipes}
                    onRecipeSelect={handleRecipeSelect}
                  />
                </div>
              )}

              {/* Typing indicator */}
              {isTyping && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg px-4 py-2">
                    <div className="flex items-center gap-2">
                      {toolActivity ? (
                        <span className="text-sm text-gray-600">{toolActivity}</span>
                      ) : (
                        <>
                          <div className="flex space-x-1">
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
                          </div>
                          <span className="text-sm text-gray-500">Thinking...</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about recipes, pantry, or meal planning..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            disabled={!isConnected}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || !isConnected}
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
      </div>

      {/* Custom animations */}
      <style>{`
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-0.5rem); }
        }
        .animate-bounce {
          animation: bounce 1s infinite;
        }
        .delay-100 {
          animation-delay: 0.1s;
        }
        .delay-200 {
          animation-delay: 0.2s;
        }
      `}</style>
    </div>
  );
}
