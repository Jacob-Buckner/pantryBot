# PantryBot Roadmap

## v2.0.0-alpha ✓ (current)

Server-rendered pantry + recipe manager. No external dependencies.

- Pantry — add, edit, delete ingredients; best-by expiry warnings
- Recipes — Markdown instructions, ingredient-to-pantry comparison, add missing to shopping list, mark as made
- Shopping list — add/remove items; auto-populated from recipe shortfalls
- `seed.py` for importing recipes from JSON

## v2.0.0 final

- `/ask` route — natural language queries via a local llama.cpp model
- MCP server wrapper so Claude Desktop can query the local SQLite DB
- Unit conversion for weight (g ↔ kg ↔ oz ↔ lb)
- Category filter/browser on pantry view

## Future ideas

- Barcode / UPC scan for adding pantry items
- Servings multiplier on recipe detail ("I'm making this for 2, not 4")
- Meal planning calendar view
- Print-friendly shopping list
- Recipe import from URL (parse structured recipe data)
- Export / backup as JSON
