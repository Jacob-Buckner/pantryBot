export default function RecipeBookPage() {
  return (
    <div className="max-w-7xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Recipe Book</h1>

      <div className="bg-white rounded-lg shadow-sm p-8 text-center text-gray-500">
        <p className="text-lg">No saved recipes yet.</p>
        <p className="text-sm mt-2">
          Save recipes from your chat conversations to see them here.
        </p>
      </div>
    </div>
  );
}
