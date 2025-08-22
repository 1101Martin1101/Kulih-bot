import aiosqlite
import os
from .config import xp_for_next_level, LEVEL_UP_HP_BONUS, LEVEL_UP_DMG_BONUS, total_xp_for_level

async def process_level_up(db, user_id, xp, lvl, hp):
    leveled_up = False
    old_lvl = lvl
    # OPRAVA: Kontrola podle kumulativních XP
    while xp >= total_xp_for_level(lvl + 1):
        lvl += 1
        leveled_up = True
    if leveled_up:
        hp += LEVEL_UP_HP_BONUS * (lvl - old_lvl)
        row = await db.execute("SELECT dmg FROM players WHERE user=?", (user_id,))
        dmg_row = await row.fetchone()
        dmg = dmg_row[0] if dmg_row else 10
        dmg += LEVEL_UP_DMG_BONUS * (lvl - old_lvl)
        await db.execute("UPDATE players SET hp=?, dmg=? WHERE user=?", (hp, dmg, user_id))
    return xp, lvl, hp, leveled_up

def get_db_path(guild_id: int) -> str:
    os.makedirs("db/kulhon", exist_ok=True)
    return f"db/kulhon/economy_{guild_id}.db"

async def ensure_guild_db(guild_id: int):
    path = get_db_path(guild_id)
    new = not os.path.exists(path)
    async with aiosqlite.connect(path) as db:
        await db.executescript("""
           CREATE TABLE IF NOT EXISTS players (
               user INTEGER PRIMARY KEY,
               kulhon REAL DEFAULT 0,
               xp REAL DEFAULT 0,
               lvl INTEGER DEFAULT 1,
               raid_cd REAL DEFAULT 0,
               job_cd REAL DEFAULT 0,
               kills INTEGER DEFAULT 0,
               deaths INTEGER DEFAULT 0,
               jobs_done INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS items (
                name TEXT PRIMARY KEY,
                price REAL,
                defence REAL,
                description TEXT,
                min_lvl INTEGER
            );
            CREATE TABLE IF NOT EXISTS owned_items (
                user INTEGER,
                item TEXT,
                PRIMARY KEY (user, item)
            );
            CREATE TABLE IF NOT EXISTS active_boosts (
                user INTEGER,
                boost_type TEXT,
                percent INTEGER,
                expires_at REAL
            );
        """)
        # --- DODÁNÍ NOVÝCH SLOUPCŮ ---
        # HP
        cursor = await db.execute("PRAGMA table_info(players)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "hp" not in columns:
            await db.execute("ALTER TABLE players ADD COLUMN hp INTEGER DEFAULT 100")
        if "dmg" not in columns:
            await db.execute("ALTER TABLE players ADD COLUMN dmg INTEGER DEFAULT 10")
        if "armor" not in columns:
            await db.execute("ALTER TABLE players ADD COLUMN armor INTEGER DEFAULT 0")
        if "potion_cd" not in columns:
            await db.execute("ALTER TABLE players ADD COLUMN potion_cd REAL DEFAULT 0")
        if "potion_protect_until" not in columns:
            await db.execute("ALTER TABLE players ADD COLUMN potion_protect_until REAL DEFAULT 0")
        # ...původní ukázkové itemy...
        if new:
            await db.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?)",
                ("Iron Chestplate", 100, 10, "Základní železný plát", 1))
            await db.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?)",
                ("Steel Armor", 300, 25, "Pevná ocelová zbroj", 5))
            await db.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?)",
                ("Dragon Scale Mail", 1000, 60, "Exotická dračí zbroj", 10))
        await db.commit()

async def get_player(db, user: int):
    cur = await db.execute("SELECT kulhon, xp, lvl, raid_cd, job_cd FROM players WHERE user=?", (user,))
    row = await cur.fetchone()
    if not row:
        await db.execute("INSERT INTO players (user) VALUES (?)", (user,))
        await db.commit()
        return 0, 0, 1, 0, 0
    return row

async def update_player(db, user: int, kulhon=None, xp=None, lvl=None, raid_cd=None, job_cd=None):
    print(f"UPDATE: user={user}, kulhon={kulhon}, xp={xp}")
    parts, params = [], []
    if kulhon is not None:
        parts.append("kulhon=?"); params.append(kulhon)
    if xp is not None:
        parts.append("xp=?"); params.append(xp)
    if lvl is not None:
        parts.append("lvl=?"); params.append(lvl)
    if raid_cd is not None:
        parts.append("raid_cd=?"); params.append(raid_cd)
    if job_cd is not None:
        parts.append("job_cd=?"); params.append(job_cd)
    params.append(user)
    await db.execute(f"UPDATE players SET {', '.join(parts)} WHERE user=?", params)
    await db.commit()  # <-- DOPLŇ TENTO ŘÁDEK