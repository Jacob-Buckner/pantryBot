from flask import Flask, render_template, request, redirect, url_for, g, flash
import markdown as md
from datetime import datetime, timedelta
import db as _db

app = Flask(__name__)
app.secret_key = "pantrybot-local-v2"

NUM_RI_SLOTS = 20


def get_db():
    if "db" not in g:
        g.db = _db.get_db()
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db:
        db.close()


def expiry_status(best_by):
    if not best_by:
        return None
    try:
        exp = datetime.fromisoformat(best_by)
        now = datetime.now()
        if exp < now:
            return "expired"
        if exp <= now + timedelta(days=7):
            return "expiring"
    except ValueError:
        pass
    return None


# ── PANTRY ──────────────────────────────────────────────────────────────────

@app.route("/")
def pantry():
    sort = request.args.get("sort", "name")
    direction = request.args.get("dir", "asc")
    editing_id = request.args.get("editing", type=int)

    allowed = {"name", "quantity", "best_by", "category"}
    if sort not in allowed:
        sort = "name"
    order = "ASC" if direction == "asc" else "DESC"

    db = get_db()
    rows = db.execute(
        f"SELECT * FROM ingredients ORDER BY {sort} {order} NULLS LAST"
    ).fetchall()

    ingredients = []
    for row in rows:
        d = dict(row)
        d["expiry_status"] = expiry_status(d.get("best_by"))
        ingredients.append(d)

    return render_template(
        "pantry.html",
        ingredients=ingredients,
        sort=sort,
        direction=direction,
        editing_id=editing_id,
    )


@app.route("/ingredients/add", methods=["POST"])
def add_ingredient():
    db = get_db()
    db.execute(
        """INSERT INTO ingredients (name, quantity, unit, category, notes, opened_at, best_by)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            request.form["name"].strip(),
            float(request.form.get("quantity") or 0),
            request.form.get("unit", "count").strip() or "count",
            request.form.get("category", "").strip() or None,
            request.form.get("notes", "").strip() or None,
            request.form.get("opened_at", "").strip() or None,
            request.form.get("best_by", "").strip() or None,
        ),
    )
    db.commit()
    return redirect(url_for("pantry"))


@app.route("/ingredients/<int:id>/edit", methods=["POST"])
def edit_ingredient(id):
    db = get_db()
    db.execute(
        """UPDATE ingredients
           SET name=?, quantity=?, unit=?, category=?, notes=?, opened_at=?, best_by=?
           WHERE id=?""",
        (
            request.form["name"].strip(),
            float(request.form.get("quantity") or 0),
            request.form.get("unit", "count").strip() or "count",
            request.form.get("category", "").strip() or None,
            request.form.get("notes", "").strip() or None,
            request.form.get("opened_at", "").strip() or None,
            request.form.get("best_by", "").strip() or None,
            id,
        ),
    )
    db.commit()
    return redirect(url_for("pantry"))


@app.route("/ingredients/<int:id>/delete", methods=["POST"])
def delete_ingredient(id):
    db = get_db()
    db.execute("DELETE FROM ingredients WHERE id=?", (id,))
    db.commit()
    return redirect(url_for("pantry"))


# ── RECIPES ─────────────────────────────────────────────────────────────────

@app.route("/recipes")
def recipes():
    db = get_db()
    rows = db.execute("SELECT * FROM recipes ORDER BY name").fetchall()
    return render_template("recipes.html", recipes=rows)


@app.route("/recipes/new", methods=["GET", "POST"])
def recipe_new():
    if request.method == "POST":
        return _save_recipe(None)
    return render_template("recipe_form.html", recipe=None, recipe_ingredients=[])


@app.route("/recipes/<int:id>")
def recipe_detail(id):
    db = get_db()
    recipe = db.execute("SELECT * FROM recipes WHERE id=?", (id,)).fetchone()
    if not recipe:
        return "Recipe not found", 404

    ris = db.execute(
        """SELECT ri.amount, ri.unit, i.name, i.quantity AS pantry_qty, i.id AS ingredient_id
           FROM recipe_ingredients ri
           JOIN ingredients i ON ri.ingredient_id = i.id
           WHERE ri.recipe_id = ?""",
        (id,),
    ).fetchall()

    annotated = []
    for ri in ris:
        needed = ri["amount"]
        have = ri["pantry_qty"]
        shortfall = max(0, needed - have)
        annotated.append(
            {
                "name": ri["name"],
                "amount": ri["amount"],
                "unit": ri["unit"],
                "pantry_qty": have,
                "status": "ok" if shortfall == 0 else "short",
                "shortfall": shortfall,
                "ingredient_id": ri["ingredient_id"],
            }
        )

    instructions_html = md.markdown(recipe["instructions"] or "", extensions=["nl2br"])

    return render_template(
        "recipe_detail.html",
        recipe=recipe,
        ingredients=annotated,
        instructions_html=instructions_html,
        can_make=all(i["status"] == "ok" for i in annotated),
    )


@app.route("/recipes/<int:id>/edit", methods=["GET", "POST"])
def recipe_edit(id):
    db = get_db()
    recipe = db.execute("SELECT * FROM recipes WHERE id=?", (id,)).fetchone()
    if not recipe:
        return "Recipe not found", 404

    if request.method == "POST":
        return _save_recipe(id)

    ris = db.execute(
        """SELECT ri.amount, ri.unit, i.name
           FROM recipe_ingredients ri
           JOIN ingredients i ON ri.ingredient_id = i.id
           WHERE ri.recipe_id = ?""",
        (id,),
    ).fetchall()

    return render_template(
        "recipe_form.html", recipe=dict(recipe), recipe_ingredients=list(ris)
    )


@app.route("/recipes/<int:id>/delete", methods=["POST"])
def recipe_delete(id):
    db = get_db()
    db.execute("DELETE FROM recipes WHERE id=?", (id,))
    db.commit()
    return redirect(url_for("recipes"))


def _save_recipe(recipe_id):
    db = get_db()
    name = request.form["name"].strip()
    instructions = request.form.get("instructions", "").strip()
    servings = int(request.form.get("servings") or 4)
    prep_minutes = int(request.form.get("prep_minutes") or 0)
    notes = request.form.get("notes", "").strip() or None

    if recipe_id is None:
        cur = db.execute(
            "INSERT INTO recipes (name, instructions, servings, prep_minutes, notes) VALUES (?, ?, ?, ?, ?)",
            (name, instructions, servings, prep_minutes, notes),
        )
        recipe_id = cur.lastrowid
    else:
        db.execute(
            "UPDATE recipes SET name=?, instructions=?, servings=?, prep_minutes=?, notes=? WHERE id=?",
            (name, instructions, servings, prep_minutes, notes, recipe_id),
        )
        db.execute("DELETE FROM recipe_ingredients WHERE recipe_id=?", (recipe_id,))

    for i in range(NUM_RI_SLOTS):
        ri_name = request.form.get(f"ri_name_{i}", "").strip()
        ri_amount = request.form.get(f"ri_amount_{i}", "").strip()
        ri_unit = request.form.get(f"ri_unit_{i}", "").strip() or "count"

        if not ri_name or not ri_amount:
            continue
        try:
            ri_amount_f = float(ri_amount)
        except ValueError:
            continue

        existing = db.execute(
            "SELECT id FROM ingredients WHERE LOWER(name) = LOWER(?)", (ri_name,)
        ).fetchone()

        if existing:
            ingredient_id = existing["id"]
        else:
            cur = db.execute(
                "INSERT INTO ingredients (name, quantity, unit) VALUES (?, 0, ?)",
                (ri_name, ri_unit),
            )
            ingredient_id = cur.lastrowid

        db.execute(
            "INSERT OR REPLACE INTO recipe_ingredients (recipe_id, ingredient_id, amount, unit) VALUES (?, ?, ?, ?)",
            (recipe_id, ingredient_id, ri_amount_f, ri_unit),
        )

    db.commit()
    return redirect(url_for("recipe_detail", id=recipe_id))


@app.route("/recipes/<int:id>/add-missing", methods=["POST"])
def recipe_add_missing(id):
    db = get_db()
    ris = db.execute(
        """SELECT ri.amount, ri.unit, i.name, i.quantity AS pantry_qty
           FROM recipe_ingredients ri
           JOIN ingredients i ON ri.ingredient_id = i.id
           WHERE ri.recipe_id = ?""",
        (id,),
    ).fetchall()

    added = 0
    for ri in ris:
        shortfall = ri["amount"] - ri["pantry_qty"]
        if shortfall > 0:
            db.execute(
                "INSERT INTO shopping_list (name, quantity, unit) VALUES (?, ?, ?)",
                (ri["name"], round(shortfall, 4), ri["unit"]),
            )
            added += 1

    db.commit()
    flash(f"Added {added} item(s) to your shopping list.")
    return redirect(url_for("recipe_detail", id=id))


@app.route("/recipes/<int:id>/mark-made", methods=["POST"])
def recipe_mark_made(id):
    db = get_db()
    ris = db.execute(
        """SELECT ri.amount, ri.ingredient_id, i.quantity AS pantry_qty
           FROM recipe_ingredients ri
           JOIN ingredients i ON ri.ingredient_id = i.id
           WHERE ri.recipe_id = ?""",
        (id,),
    ).fetchall()

    for ri in ris:
        new_qty = max(0.0, ri["pantry_qty"] - ri["amount"])
        db.execute(
            "UPDATE ingredients SET quantity=? WHERE id=?",
            (new_qty, ri["ingredient_id"]),
        )

    db.commit()
    flash("Pantry updated — ingredients deducted.")
    return redirect(url_for("recipe_detail", id=id))


# ── SHOPPING LIST ────────────────────────────────────────────────────────────

@app.route("/shopping")
def shopping():
    db = get_db()
    items = db.execute(
        "SELECT * FROM shopping_list ORDER BY added_at DESC"
    ).fetchall()
    return render_template("shopping.html", items=items)


@app.route("/shopping/add", methods=["POST"])
def shopping_add():
    db = get_db()
    db.execute(
        "INSERT INTO shopping_list (name, quantity, unit) VALUES (?, ?, ?)",
        (
            request.form["name"].strip(),
            float(request.form.get("quantity") or 1),
            request.form.get("unit", "count").strip() or "count",
        ),
    )
    db.commit()
    return redirect(url_for("shopping"))


@app.route("/shopping/<int:id>/got-it", methods=["POST"])
def shopping_got_it(id):
    """Mark item as purchased: add its quantity to the pantry, then remove from list."""
    db = get_db()
    item = db.execute("SELECT * FROM shopping_list WHERE id=?", (id,)).fetchone()
    if item:
        existing = db.execute(
            "SELECT id, quantity FROM ingredients WHERE LOWER(name) = LOWER(?)",
            (item["name"],),
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE ingredients SET quantity = quantity + ? WHERE id=?",
                (item["quantity"], existing["id"]),
            )
        else:
            db.execute(
                "INSERT INTO ingredients (name, quantity, unit) VALUES (?, ?, ?)",
                (item["name"], item["quantity"], item["unit"]),
            )
        db.execute("DELETE FROM shopping_list WHERE id=?", (id,))
        db.commit()
        flash(f"Added {item['quantity']} {item['unit']} of {item['name']} to pantry.")
    return redirect(url_for("shopping"))


@app.route("/shopping/<int:id>/delete", methods=["POST"])
def shopping_delete(id):
    """Remove from shopping list without touching the pantry."""
    db = get_db()
    db.execute("DELETE FROM shopping_list WHERE id=?", (id,))
    db.commit()
    return redirect(url_for("shopping"))


# ── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _db.init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
