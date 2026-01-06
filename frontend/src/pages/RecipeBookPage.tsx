import { useState, useEffect } from 'react';

interface SavedRecipe {
  id: number;
  name: string;
  description: string;
  servings: number;
  image_url: string | null;
  modified: string;
}

export default function RecipeBookPage() {
  const [recipes, setRecipes] = useState<SavedRecipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRecipe, setSelectedRecipe] = useState<{ name: string; content: string } | null>(null);

  useEffect(() => {
    fetchRecipes();
  }, []);

  const fetchRecipes = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8080/api/recipes');
      const data = await response.json();

      if (data.success) {
        setRecipes(data.recipes || []);
      } else {
        setError(data.error || 'Failed to load recipes');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const viewRecipe = async (recipeId: number, recipeName: string) => {
    try {
      const response = await fetch(`http://localhost:8080/api/recipes/${recipeId}`);
      const data = await response.json();

      if (data.success) {
        setSelectedRecipe({ name: recipeName, content: data.content });
      } else {
        alert('Failed to load recipe: ' + data.error);
      }
    } catch (err: any) {
      alert('Error loading recipe: ' + err.message);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">Recipe Book</h1>
        <div className="text-center text-gray-500">Loading recipes...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">Recipe Book</h1>
        <div className="bg-red-100 text-red-700 p-4 rounded-lg">
          Error: {error}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Recipe Book</h1>
        <button
          onClick={fetchRecipes}
          className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
        >
          Refresh
        </button>
      </div>

      {recipes.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm p-8 text-center text-gray-500">
          <p className="text-lg">No saved recipes yet.</p>
          <p className="text-sm mt-2">
            Save recipes from your chat conversations to see them here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {recipes.map((recipe) => (
            <div
              key={recipe.id}
              className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => viewRecipe(recipe.id, recipe.name)}
            >
              {/* Recipe Image */}
              {recipe.image_url ? (
                <img
                  src={recipe.image_url}
                  alt={recipe.name}
                  className="w-full h-48 object-cover"
                />
              ) : (
                <div className="w-full h-48 bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
                  <span className="text-white text-6xl">🍳</span>
                </div>
              )}

              {/* Recipe Info */}
              <div className="p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {recipe.name}
                </h3>
                <div className="text-sm text-gray-600 space-y-1">
                  {recipe.servings && (
                    <p className="flex items-center gap-2">
                      <span>🍽️</span>
                      <span>{recipe.servings} servings</span>
                    </p>
                  )}
                  <p className="text-xs text-gray-400">
                    Added: {new Date(recipe.modified).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Recipe Modal */}
      {selectedRecipe && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedRecipe(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <h2 className="text-2xl font-bold">{selectedRecipe.name}</h2>
              <button
                onClick={() => setSelectedRecipe(null)}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ×
              </button>
            </div>
            <div className="p-6">
              <pre className="whitespace-pre-wrap font-sans text-gray-800">
                {selectedRecipe.content}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
