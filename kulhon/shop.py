import discord, aiosqlite
import time
from discord import app_commands
from discord.ext import commands
from .db import get_db_path, ensure_guild_db, get_player, update_player

CATEGORIES = {
    "raid_boost": "⚡ Raid Boost",
    "armor_boost": "🛡️ Armor Boost",
    "money_boost": "💰 Money Boost",
    "dmg_boost": "⚔️ DMG Boost",
    "heal_boost": "❤️ Heal Boost",
    "armory": "🦾 Armory",
    "zbrane": "🔪 Zbraně",
    "joby": "🧰 Joby",
    "upgrade": "⬆️ Upgrady",
    "potion": "🧪 Lektvary"
}

CATEGORY_COLORS = {
    "raid_boost": discord.Color.orange(),
    "armor_boost": discord.Color.blue(),
    "money_boost": discord.Color.gold(),
    "dmg_boost": discord.Color.red(),
    "heal_boost": discord.Color.green(),
    "armory": discord.Color.dark_teal(),
    "zbrane": discord.Color.dark_red(),
    "joby": discord.Color.purple(),
    "upgrade": discord.Color.green(),
    "potion": discord.Color.magenta()
}

RAID_BOOST_ITEMS = [
    ("Raid XP Boost 5%",   200,  "Zvýší XP z raidu o 5% na 1 hodinu",   "raid_boost", {"type": "xp",    "percent": 5,  "duration": 3600, "min_lvl": 1}),
    ("Raid XP Boost 10%",  350,  "Zvýší XP z raidu o 10% na 1 hodinu",  "raid_boost", {"type": "xp",    "percent": 10, "duration": 3600, "min_lvl": 3}),
    ("Raid XP Boost 15%",  550,  "Zvýší XP z raidu o 15% na 1 hodinu",  "raid_boost", {"type": "xp",    "percent": 15, "duration": 3600, "min_lvl": 6}),
    ("Raid XP Boost 20%",  800,  "Zvýší XP z raidu o 20% na 1 hodinu",  "raid_boost", {"type": "xp",    "percent": 20, "duration": 3600, "min_lvl": 10}),
    ("Raid XP Boost 25%", 1200,  "Zvýší XP z raidu o 25% na 1 hodinu",  "raid_boost", {"type": "xp",    "percent": 25, "duration": 3600, "min_lvl": 15}),
]

ARMOR_BOOST_ITEMS = [
    ("Armor Boost 5%",    250,   "Zvýší obranu o 5% na 1 hodinu",       "armor_boost", {"type": "armor", "percent": 5,  "duration": 3600, "min_lvl": 1}),
    ("Armor Boost 10%",   450,   "Zvýší obranu o 10% na 1 hodinu",      "armor_boost", {"type": "armor", "percent": 10, "duration": 3600, "min_lvl": 4}),
    ("Armor Boost 15%",   700,   "Zvýší obranu o 15% na 1 hodinu",      "armor_boost", {"type": "armor", "percent": 15, "duration": 3600, "min_lvl": 8}),
    ("Armor Boost 20%",  1000,   "Zvýší obranu o 20% na 1 hodinu",      "armor_boost", {"type": "armor", "percent": 20, "duration": 3600, "min_lvl": 12}),
    ("Armor Boost 25%",  1400,   "Zvýší obranu o 25% na 1 hodinu",      "armor_boost", {"type": "armor", "percent": 25, "duration": 3600, "min_lvl": 18}),
]

DMG_BOOST_ITEMS = [
    ("DMG Boost 5%",      300,   "Zvýší damage o 5% na 1 hodinu",       "dmg_boost", {"type": "dmg",   "percent": 5,  "duration": 3600, "min_lvl": 2}),
    ("DMG Boost 10%",     550,   "Zvýší damage o 10% na 1 hodinu",      "dmg_boost", {"type": "dmg",   "percent": 10, "duration": 3600, "min_lvl": 5}),
    ("DMG Boost 15%",     850,   "Zvýší damage o 15% na 1 hodinu",      "dmg_boost", {"type": "dmg",   "percent": 15, "duration": 3600, "min_lvl": 9}),
    ("DMG Boost 20%",    1200,   "Zvýší damage o 20% na 1 hodinu",      "dmg_boost", {"type": "dmg",   "percent": 20, "duration": 3600, "min_lvl": 13}),
    ("DMG Boost 25%",    1600,   "Zvýší damage o 25% na 1 hodinu",      "dmg_boost", {"type": "dmg",   "percent": 25, "duration": 3600, "min_lvl": 20}),
]

MONEY_BOOST_ITEMS = [
    ("Money Boost 5%",    250,   "Zvýší výdělek z jobu o 5% na 1 hodinu",   "money_boost", {"type": "money", "percent": 5,  "duration": 3600, "min_lvl": 1}),
    ("Money Boost 10%",   500,   "Zvýší výdělek z jobu o 10% na 1 hodinu",  "money_boost", {"type": "money", "percent": 10, "duration": 3600, "min_lvl": 4}),
    ("Money Boost 15%",   800,   "Zvýší výdělek z jobu o 15% na 1 hodinu",  "money_boost", {"type": "money", "percent": 15, "duration": 3600, "min_lvl": 8}),
    ("Money Boost 20%",  1100,   "Zvýší výdělek z jobu o 20% na 1 hodinu",  "money_boost", {"type": "money", "percent": 20, "duration": 3600, "min_lvl": 13}),
    ("Money Boost 25%",  1500,   "Zvýší výdělek z jobu o 25% na 1 hodinu",  "money_boost", {"type": "money", "percent": 25, "duration": 3600, "min_lvl": 19}),
]

HEAL_BOOST_ITEMS = [
    ("Heal Boost 10HP", 400, "Okamžitě přidá 10 životů", "heal_boost", {"type": "hp", "amount": 10, "duration": 0, "min_lvl": 1}),
    ("Heal Boost 25HP", 900, "Okamžitě přidá 25 životů", "heal_boost", {"type": "hp", "amount": 25, "duration": 0, "min_lvl": 5}),
    ("Heal Boost 50HP", 1800, "Okamžitě přidá 50 životů", "heal_boost", {"type": "hp", "amount": 50, "duration": 0, "min_lvl": 10}),
]

# Příklad dalších itemů pro kategorie
ARMORY_ITEMS = [
    ("Iron Chestplate", 100, "Základní železný plát", "armory", {}),
    ("Steel Armor", 300, "Pevná ocelová zbroj", "armory", {}),
    ("Dragon Scale Mail", 1000, "Exotická dračí zbroj", "armory", {}),
]
WEAPON_ITEMS = [
    ("Iron Sword", 150, "Základní železný meč", "zbrane", {"dmg": 5, "min_lvl": 1}),
    ("Diamond Sword", 700, "Diamantový meč", "zbrane", {"dmg": 15, "min_lvl": 5}),
    ("Steel Axe", 400, "Silná ocelová sekera", "zbrane", {"dmg": 10, "min_lvl": 3}),
    ("Golden Dagger", 350, "Rychlá zlatá dýka", "zbrane", {"dmg": 7, "min_lvl": 2}),
    ("Bow", 500, "Dlouhý luk pro útok na dálku", "zbrane", {"dmg": 8, "min_lvl": 4}),
    ("Crossbow", 900, "Silná kuše s velkým průrazem", "zbrane", {"dmg": 13, "min_lvl": 7}),
    ("Magic Staff", 1200, "Magická hůl pro speciální útoky", "zbrane", {"dmg": 18, "min_lvl": 10}),
    ("Fire Sword", 2000, "Meč s ohnivým efektem", "zbrane", {"dmg": 25, "min_lvl": 15}),
    ("Shadow Blade", 3000, "Legendární čepel stínů", "zbrane", {"dmg": 35, "min_lvl": 25}),
]
JOB_ITEMS = [
    ("Job Level Up", 500, "Zvýší level jobu o 1", "joby", {}),
    ("Job XP Boost", 400, "Zvýší XP z jobu o 10% na 1 hodinu", "joby", {"type": "xp", "percent": 10, "duration": 3600}),
]

UPGRADE_ITEMS = [
    ("HP Upgrade", 500, "Zvýší životy o 10", "upgrade", {"type": "hp", "amount": 10, "duration": 0, "min_lvl": 1}),
    ("DMG Upgrade", 700, "Zvýší damage o 2", "upgrade", {"type": "dmg_stat", "amount": 2, "duration": 0, "min_lvl": 2}),
    ("Armor Upgrade", 600, "Zvýší obranu o 3", "upgrade", {"type": "armor_stat", "amount": 3, "duration": 0, "min_lvl": 2}),
    ("Skip Job Cooldown", 800, "Okamžitě zruší cooldown na job", "upgrade", {"type": "skip_job_cd"}),
    ("Skip Raid Cooldown", 1200, "Okamžitě zruší cooldown na raid", "upgrade", {"type": "skip_raid_cd"}),
]

POTION_ITEMS = [
    ("Potion 1h", 1000, "Chrání před útokem na 1 hodinu", "potion", {"type": "potion", "protect": 3600, "cd": 18000, "min_lvl": 10}),
    ("Potion 2h", 1800, "Chrání před útokem na 2 hodiny", "potion", {"type": "potion", "protect": 7200, "cd": 36000, "min_lvl": 20}),
    ("Potion 4h", 3200, "Chrání před útokem na 4 hodiny", "potion", {"type": "potion", "protect": 14400, "cd": 72000, "min_lvl": 40}),
    ("Potion 6h", 5000, "Chrání před útokem na 6 hodin", "potion", {"type": "potion", "protect": 21600, "cd": 108000, "min_lvl": 60}),
]

ALL_ITEMS = (
    RAID_BOOST_ITEMS +
    ARMOR_BOOST_ITEMS +
    MONEY_BOOST_ITEMS +
    DMG_BOOST_ITEMS +
    HEAL_BOOST_ITEMS +
    ARMORY_ITEMS +
    WEAPON_ITEMS +
    JOB_ITEMS +
    UPGRADE_ITEMS +
    POTION_ITEMS
)

class CategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=v, value=k)
            for k, v in CATEGORIES.items()
        ]
        super().__init__(placeholder="Vyber kategorii...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view: ShopView = self.view
        await view.show_category(interaction, self.values[0])

class ItemSelect(discord.ui.Select):
    def __init__(self, items, owned):
        options = [
            discord.SelectOption(
                label=f"{'✅ ' if name in owned else ''}{name}",
                description=desc,
                value=name,
                default=name in owned
            )
            for name, price, desc, cat, extra in items
            if name not in owned
        ][:25]
        super().__init__(placeholder="Vyber item k nákupu...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        gid, uid = interaction.guild_id, interaction.user.id
        await ensure_guild_db(gid)
        async with aiosqlite.connect(get_db_path(gid)) as db:
            item = next((i for i in ALL_ITEMS if i[0] == self.values[0]), None)
            if not item:
                return await interaction.response.send_message("Neplatný item.", ephemeral=True)
            name, price, desc, cat, extra = item
            kul, xp, lvl, raid_cd, job_cd = await get_player(db, uid)
            now = time.time()
            # --- cooldown na boosty, upgrade, potion ---
            # --- cooldown na boosty, upgrade, potion ---
            if extra.get("type") in ["hp", "dmg_stat", "armor_stat"]:
                row = await db.execute("SELECT expires_at FROM active_boosts WHERE user=? AND boost_type=? ORDER BY expires_at DESC LIMIT 1", (uid, extra["type"]))
                last = await row.fetchone()
                if last and last[0] + 21600 > now:  # 6h cooldown
                    ts = f"<t:{int(last[0] + 21600)}:R>"
                    return await interaction.response.send_message(f"⏳ Cooldown na upgrade: {ts}", ephemeral=True)
            # --- speciální cooldown pro skip_job_cd ---
            if extra.get("type") == "skip_job_cd":
                row = await db.execute("SELECT expires_at FROM active_boosts WHERE user=? AND boost_type=? ORDER BY expires_at DESC LIMIT 1", (uid, "skip_job_cd"))
                last = await row.fetchone()
                if last and last[0] + 1800 > now:  # 30 minut cooldown
                    ts = f"<t:{int(last[0] + 1800)}:R>"
                    return await interaction.response.send_message(f"⏳ Cooldown na Skip Job CD: {ts}", ephemeral=True)
            # --- speciální cooldown pro skip_raid_cd ---
            if extra.get("type") == "skip_raid_cd":
                row = await db.execute("SELECT expires_at FROM active_boosts WHERE user=? AND boost_type=? ORDER BY expires_at DESC LIMIT 1", (uid, "skip_raid_cd"))
                last = await row.fetchone()
                if last and last[0] + 1800 > now:  # 30 minut cooldown
                    ts = f"<t:{int(last[0] + 1800)}:R>"
                    return await interaction.response.send_message(f"⏳ Cooldown na Skip Raid CD: {ts}", ephemeral=True)
            if extra.get("type") == "potion":
                row = await db.execute("SELECT potion_cd FROM players WHERE user=?", (uid,))
                potion_cd = (await row.fetchone())[0]
                if potion_cd > now:
                    ts = f"<t:{int(potion_cd)}:R>"
                    return await interaction.response.send_message(f"⏳ Cooldown na lektvar: {ts}", ephemeral=True)
                if lvl < extra["min_lvl"]:
                    return await interaction.response.send_message(f"Potřebuješ level {extra['min_lvl']} pro tento lektvar.", ephemeral=True)
            # --- ostatní kontroly ---
            owned_row = await db.execute("SELECT 1 FROM owned_items WHERE user=? AND item=?", (uid, name))
            owned = await owned_row.fetchone()
            if owned and cat != "boosty":
                return await interaction.response.send_message("Tento item už vlastníš.", ephemeral=True)
            if kul < price:
                return await interaction.response.send_message("Na to nemáš Kulhony.", ephemeral=True)
            if "min_lvl" in extra and lvl < extra["min_lvl"]:
                return await interaction.response.send_message(f"Potřebuješ level {extra['min_lvl']} pro tento item.", ephemeral=True)
            kul -= price
            await update_player(db, uid, kulhon=kul)
            await db.execute("INSERT OR IGNORE INTO owned_items (user, item) VALUES (?, ?)", (uid, name))
            # --- aplikace boostů, upgrade, potion ---
            if extra.get("type") == "skip_job_cd":
                await db.execute("UPDATE players SET job_cd=? WHERE user=?", (now, uid))  # zruší cooldown
                expires = now
                await db.execute("INSERT INTO active_boosts (user, boost_type, percent, expires_at) VALUES (?, ?, ?, ?)", (uid, "skip_job_cd", 0, expires))
            if extra.get("type") == "skip_raid_cd":
                await db.execute("UPDATE players SET raid_cd=? WHERE user=?", (now, uid))  # zruší cooldown
                expires = now
                await db.execute("INSERT INTO active_boosts (user, boost_type, percent, expires_at) VALUES (?, ?, ?, ?)", (uid, "skip_raid_cd", 0, expires))
            if cat == "zbrane" and "dmg" in extra:
                await db.execute("UPDATE players SET dmg = dmg + ? WHERE user=?", (extra["dmg"], uid))
            if extra.get("type") == "hp":
                await db.execute("UPDATE players SET hp = hp + ? WHERE user=?", (extra["amount"], uid))
                expires = now
                await db.execute("INSERT INTO active_boosts (user, boost_type, percent, expires_at) VALUES (?, ?, ?, ?)", (uid, "hp", extra["amount"], expires))
            if extra.get("type") == "dmg_stat":
                await db.execute("UPDATE players SET dmg = dmg + ? WHERE user=?", (extra["amount"], uid))
                expires = now
                await db.execute("INSERT INTO active_boosts (user, boost_type, percent, expires_at) VALUES (?, ?, ?, ?)", (uid, "dmg_stat", extra["amount"], expires))
            if extra.get("type") == "armor_stat":
                await db.execute("UPDATE players SET armor = armor + ? WHERE user=?", (extra["amount"], uid))
                expires = now
                await db.execute("INSERT INTO active_boosts (user, boost_type, percent, expires_at) VALUES (?, ?, ?, ?)", (uid, "armor_stat", extra["amount"], expires))
            if extra.get("type") == "potion":
                protect_until = now + extra["protect"]
                potion_cd = now + extra["cd"]
                await db.execute("UPDATE players SET potion_protect_until=?, potion_cd=? WHERE user=?", (protect_until, potion_cd, uid))
            if "duration" in extra:
                expires = now + extra["duration"]
                await db.execute("INSERT INTO active_boosts (user, boost_type, percent, expires_at) VALUES (?, ?, ?, ?)", (uid, extra["type"], extra.get("percent", 0), expires))
            await db.commit()
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"✅ Koupě úspěšná!",
                description=f"Koupil jsi **{name}** za **{price} Kulhonů**.\nZbývá ti **{kul} Kulhonů**.",
                color=discord.Color.green()
            ),
            ephemeral=True
        )

class ShopView(discord.ui.View):
    def __init__(self, items, owned, category=None):
        super().__init__(timeout=None)
        self.items = items
        self.owned = owned
        self.category = category
        self.add_item(CategorySelect())
        if category:
            self.add_item(ItemSelect([i for i in items if i[3] == category], owned))

    async def show_category(self, interaction, category):
        self.clear_items()
        self.category = category
        self.add_item(CategorySelect())
        self.add_item(ItemSelect([i for i in self.items if i[3] == category], self.owned))

        embed = discord.Embed(
            title=f"{CATEGORIES[category]}",
            description="Vyber item k nákupu z nabídky níže.",
            color=CATEGORY_COLORS.get(category, discord.Color.blurple())
        )

        uid = interaction.user.id
        now = time.time()
        boost_cooldowns = {}

        # Všechny dotazy na db musí být uvnitř tohoto bloku!
        async with aiosqlite.connect(get_db_path(interaction.guild_id)) as db:
            for btype in ["xp", "armor", "dmg", "money", "skip_job_cd", "skip_raid_cd"]:
                cursor = await db.execute(
                    "SELECT expires_at FROM active_boosts WHERE user=? AND boost_type=? ORDER BY expires_at DESC LIMIT 1",
                    (uid, btype)
                )
                row = await cursor.fetchone()
                if row and row[0] > now:
                    boost_cooldowns[btype] = row[0] + 21600
                else:
                    cursor2 = await db.execute(
                        "SELECT MAX(expires_at) FROM active_boosts WHERE user=? AND boost_type=?",
                        (uid, btype)
                    )
                    last = await cursor2.fetchone()
                    if last and last[0]:
                        boost_cooldowns[btype] = max(last[0] + 21600, now)
                    else:
                        boost_cooldowns[btype] = None

            # Přehledné zobrazení pro boosty
            if category in ["raid_boost", "armor_boost", "money_boost", "dmg_boost", "heal_boost", "upgrade", "potion"]:
                items = [i for i in self.items if i[3] == category]
                for name, price, desc, cat, extra in items:
                    owned = name in self.owned
                    emoji = CATEGORIES[category].split()[0]
                    min_lvl = extra.get("min_lvl")
                    lvl_text = f"\n🔒 Potřebný level: {min_lvl}" if min_lvl else ""
                    cooldown_text = ""
                    # Zjisti cooldown podle typu
                    cd_seconds = 21600 if extra.get("type") in ["hp", "dmg_stat", "armor_stat"] else 1800 if extra.get("type") in ["skip_job_cd", "skip_raid_cd"] else extra.get("cd", 0)
                    expires = None
                    if extra.get("type") in ["hp", "dmg_stat", "armor_stat", "skip_job_cd", "skip_raid_cd"]:
                        btype = extra.get("type")
                        expires = boost_cooldowns.get(btype)
                    elif extra.get("type") == "potion":
                        row = await db.execute("SELECT potion_cd FROM players WHERE user=?", (uid,))
                        potion_row = await row.fetchone()
                        if potion_row and potion_row[0] > now:
                            expires = potion_row[0]
                    if expires and expires > now:
                        cooldown_text = f"\n⏳ Další nákup možný: <t:{int(expires)}:R>"
                    if owned or cooldown_text:
                        embed.add_field(
                            name=f"{emoji} ~~{name}~~",
                            value=f"~~{desc} | {price} Kulhon{lvl_text}~~{cooldown_text if cooldown_text else '\n✅ Vlastníš'}",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name=f"{emoji} {name}",
                            value=f"{desc} | {price} Kulhon{lvl_text}",
                            inline=False
                        )
            else:
                # Ostatní kategorie zůstanou jako dřív
                for name, price, desc, cat, extra in self.items:
                    if cat != category:
                        continue
                    emoji = ""
                    if cat in CATEGORIES:
                        emoji = CATEGORIES[cat].split()[0]
                    min_lvl = extra.get("min_lvl")
                    lvl_text = f"\n🔒 Potřebný level: {min_lvl}" if min_lvl else ""
                    if name in self.owned:
                        embed.add_field(
                            name=f"{emoji} ~~{name}~~",
                            value=f"~~{desc} | {price} Kulhon{lvl_text}~~\n✅ Vlastníš",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name=f"{emoji} {name}",
                            value=f"{desc} | {price} Kulhon{lvl_text}",
                            inline=False
                        )
        await interaction.response.edit_message(embed=embed, view=self)

class Shop(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(description="🛒 Zobraz obchod a kup items")
    async def shop(self, interaction: discord.Interaction):
        gid, uid = interaction.guild_id, interaction.user.id
        await ensure_guild_db(gid)
        async with aiosqlite.connect(get_db_path(gid)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS owned_items (
                    user INTEGER,
                    item TEXT,
                    PRIMARY KEY (user, item)
                )
            """)
            owned_cursor = await db.execute("SELECT item FROM owned_items WHERE user=?", (uid,))
            owned_items = [row[0] for row in await owned_cursor.fetchall()]
            embed = discord.Embed(
                title="🛒 Obchod",
                description="Vítej v obchodě! Vyber si sekci, kde chceš utratit své Kulhony.",
                color=discord.Color.blurple()
            )
            embed.add_field(
                name="Sekce",
                value="\n".join([f"{CATEGORIES[k]}" for k in CATEGORIES]),
                inline=False
            )
            await interaction.response.send_message(embed=embed, view=ShopView(ALL_ITEMS, owned_items), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Shop(bot))