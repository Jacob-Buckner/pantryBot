export default function SettingsPage() {
  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Settings</h1>

      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-semibold mb-4">API Configuration</h2>
            <p className="text-sm text-gray-600 mb-4">
              API keys are configured via environment variables in docker-compose.yml
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Claude API Key
                </label>
                <input
                  type="password"
                  value="••••••••••••••••"
                  disabled
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Spoonacular API Key
                </label>
                <input
                  type="password"
                  value="••••••••••••••••"
                  disabled
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Grocy API URL
                </label>
                <input
                  type="text"
                  value="http://grocy/api"
                  disabled
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                />
              </div>
            </div>
          </div>

          <div className="border-t pt-6">
            <h2 className="text-lg font-semibold mb-2">About PantryBot</h2>
            <p className="text-sm text-gray-600">
              Version 1.0.0 - AI-Powered Pantry Management
            </p>
            <p className="text-sm text-gray-600 mt-2">
              Built with Claude Code
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
