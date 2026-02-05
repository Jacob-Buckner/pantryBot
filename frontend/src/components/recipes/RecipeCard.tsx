/**
 * Recipe Card Component
 * Displays a recipe with Spoonacular image, match percentage, and missing ingredients
 */

import { Recipe } from '../../services/websocket';

interface RecipeCardProps {
  recipe: Recipe;
  onSelect?: () => void;
  compact?: boolean;
}

export default function RecipeCard({ recipe, onSelect, compact = false }: RecipeCardProps) {
  // Color-code match percentage
  const getMatchColor = (percentage: number): string => {
    if (percentage >= 80) return 'bg-green-500';
    if (percentage >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getMatchTextColor = (percentage: number): string => {
    if (percentage >= 80) return 'text-green-700';
    if (percentage >= 50) return 'text-yellow-700';
    return 'text-red-700';
  };

  return (
    <div
      className={`bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow cursor-pointer ${
        compact ? 'max-w-sm' : 'w-full'
      }`}
      onClick={onSelect}
    >
      {/* Recipe Image */}
      <div className="relative">
        <img
          src={recipe.image || 'https://via.placeholder.com/400x300?text=No+Image'}
          alt={recipe.title}
          className="w-full h-48 object-cover"
        />
        {/* Match Percentage Badge - only show for ingredient-based searches */}
        {(recipe.matchPercentage !== 100 || recipe.usedIngredients > 0) && (
          <div className="absolute top-2 right-2">
            <div
              className={`${getMatchColor(
                recipe.matchPercentage
              )} text-white font-bold px-3 py-1 rounded-full text-sm shadow-lg`}
            >
              {recipe.matchPercentage}% match
            </div>
          </div>
        )}
      </div>

      {/* Recipe Info */}
      <div className="p-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{recipe.title}</h3>

        {/* Quick Stats */}
        <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
          {recipe.readyInMinutes && (
            <div className="flex items-center gap-1">
              <span>⏱️</span>
              <span>{recipe.readyInMinutes} min</span>
            </div>
          )}
          {recipe.servings && (
            <div className="flex items-center gap-1">
              <span>🍽️</span>
              <span>{recipe.servings} servings</span>
            </div>
          )}
        </div>

        {/* Match Details */}
        <div className="space-y-2">
          {/* Only show ingredient match info if this was an ingredient-based search */}
          {recipe.matchPercentage !== 100 || recipe.usedIngredients > 0 ? (
            <>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-green-600">✓</span>
                <span className="text-gray-700">
                  You have {recipe.usedIngredients} ingredients
                </span>
              </div>

              {recipe.missedIngredients.length > 0 && (
                <div className="text-sm">
                  <span className="text-gray-600">Missing: </span>
                  <span className={getMatchTextColor(recipe.matchPercentage)}>
                    {recipe.missedIngredients.slice(0, 3).join(', ')}
                    {recipe.missedIngredients.length > 3 &&
                      ` +${recipe.missedIngredients.length - 3} more`}
                  </span>
                </div>
              )}

              {recipe.missedIngredients.length === 0 && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-green-600">⭐</span>
                  <span className="text-green-700 font-medium">
                    You have everything!
                  </span>
                </div>
              )}
            </>
          ) : (
            <div className="text-sm text-gray-600">
              Click "Get Recipe" to see full ingredient list
            </div>
          )}
        </div>

        {/* Action Button */}
        {onSelect && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect();
            }}
            className="mt-4 w-full bg-primary-600 text-white py-2 px-4 rounded-md hover:bg-primary-700 transition-colors"
          >
            Get Recipe
          </button>
        )}
      </div>
    </div>
  );
}
