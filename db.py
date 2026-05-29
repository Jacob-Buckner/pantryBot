import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "pantrybot.db"


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            quantity    REAL NOT NULL DEFAULT 0,
            unit        TEXT NOT NULL DEFAULT 'count',
            category    TEXT,
            notes       TEXT,
            opened_at   TEXT,
            best_by     TEXT,
            created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M', 'now'))
        );

        CREATE TABLE IF NOT EXISTS recipes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            instructions TEXT NOT NULL DEFAULT '',
            servings     INTEGER NOT NULL DEFAULT 4,
            prep_minutes INTEGER NOT NULL DEFAULT 0,
            notes        TEXT,
            created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M', 'now'))
        );

        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            recipe_id     INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
            ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
            amount        REAL NOT NULL,
            unit          TEXT NOT NULL,
            PRIMARY KEY (recipe_id, ingredient_id)
        );

        CREATE TABLE IF NOT EXISTS shopping_list (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL,
            quantity REAL NOT NULL DEFAULT 1,
            unit     TEXT NOT NULL DEFAULT 'count',
            added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M', 'now'))
        );
    """)
    db.commit()
    db.close()
