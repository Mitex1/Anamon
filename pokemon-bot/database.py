# database.py
import aiosqlite
import json

DB_FILE = "custom_cards.db"

async def initialize():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_cards (
                card_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                card_type TEXT NOT NULL,
                kp INTEGER,
                pokemon_typ TEXT,
                stage INTEGER,
                evolves_from TEXT,
                attack1_name TEXT,
                attack1_schaden INTEGER,
                attack1_cost TEXT,
                attack2_name TEXT,
                attack2_schaden INTEGER,
                attack2_cost TEXT,
                weakness_typ TEXT,
                resistance_typ TEXT,
                resistance_value INTEGER,
                retreat_cost INTEGER,
                illustrator TEXT,
                card_number TEXT,
                bild_url TEXT,
                trainer_type TEXT,
                effect_description TEXT,
                effect_type TEXT,
                effect_value TEXT,
                energy_typ TEXT
            )
        """)
        await db.commit()

async def add_card(card_data: dict):
    async with aiosqlite.connect(DB_FILE) as db:
        card_data = {k: v for k, v in card_data.items() if v is not None}
        columns = ', '.join(card_data.keys())
        placeholders = ', '.join('?' for _ in card_data)
        values = tuple(card_data.values())
        query = f"INSERT INTO custom_cards ({columns}) VALUES ({placeholders})"
        cursor = await db.execute(query, values)
        await db.commit()
        return cursor.lastrowid

async def get_card_by_id(card_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM custom_cards WHERE card_id = ?", (card_id,))
        row = await cursor.fetchone()
        if not row: return None
        card_dict = dict(row)
        for cost_field in ['attack1_cost', 'attack2_cost']:
            if card_dict.get(cost_field):
                card_dict[cost_field] = json.loads(card_dict[cost_field])
        return card_dict

async def get_user_cards(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT card_id, name, card_type, kp FROM custom_cards WHERE user_id = ?", (user_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]