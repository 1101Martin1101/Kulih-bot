import discord, aiosqlite
from discord.ext import commands
from discord import app_commands
from .db import get_db_path, ensure_guild_db, get_player, update_player
from .config import xp_for_next_level, total_xp_for_level, get_rank
import datetime

LEADERBOARD_CATEGORIES = {
    "kulhon": "💰 Top Kulhon",
    "lvl": "📈 Top Level",
    "xp": "⭐ Top XP",
    "jobs_done": "🧰 Top hotové joby",
    "kills": "🗡️ Top zabití",
    "deaths": "💀 Top smrti"
}

class LeaderboardSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=v, value=k)
            for k, v in LEADERBOARD_CATEGORIES.items()
        ]
        super().__init__(placeholder="Vyber kategorii žebříčku...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view: LeaderboardView = self.view
        await view.show_category(interaction, self.values[0])

class LeaderboardView(discord.ui.View):
    def __init__(self, bot, gid, guild):
        super().__init__(timeout=None)
        self.bot = bot
        self.gid = gid
        self.guild = guild
        self.add_item(LeaderboardSelect())

    async def show_category(self, interaction, category):
        async with aiosqlite.connect(get_db_path(self.gid)) as db:
            cursor = await db.execute(f"SELECT user, {category} FROM players ORDER BY {category} DESC LIMIT 10")
            rows = await cursor.fetchall()
        async def format_top(rows):
            result = ""
            for i, (uid, value) in enumerate(rows, 1):
                member = self.guild.get_member(uid)
                if not member:
                    try:
                        member = await self.guild.fetch_member(uid)
                    except Exception:
                        member = None
                name = member.display_name if member else f"Uživatel {uid}"
                result += f"{i}. {name}: {value}\n"
            return result if result else "Žádná data"
        embed = discord.Embed(
            title=f"{LEADERBOARD_CATEGORIES[category]}",
            color=discord.Color.purple()
        )
        embed.description = await format_top(rows)
        await interaction.response.edit_message(embed=embed, view=self)

class GameInfoInfoSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Základy", value="zaklady", emoji="📘"),
            discord.SelectOption(label="Levelování & Joby", value="level_job", emoji="🧰"),
            discord.SelectOption(label="Raiding & Ochrana", value="raid_potion", emoji="⚔️"),
            discord.SelectOption(label="Obchod & Vylepšení", value="shop_upgrade", emoji="🛒"),
        ]
        super().__init__(placeholder="Vyber kategorii nápovědy...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view: GameInfoInfoView = self.view
        await view.show_category(interaction, self.values[0])

class GameInfoInfoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(GameInfoInfoSelect())

    async def show_category(self, interaction, category):
        embed = discord.Embed(color=discord.Color.blue())
        if category == "zaklady":
            embed.title = "📘 Základy ekonomického systému"
            embed.description = (
                "👋 Vítej v **ekonomické hře**!\n\n"
                "💰 Sbírej **Kulhony**, 📈 leveluj, ⚙️ vylepšuj statistiky, "
                "🛒 kupuj boosty a vybavení, 🧪 používej lektvary na ochranu a ⚔️ soupeř s ostatními hráči.\n\n"
                "👇 Níže najdeš základní informace a další kategorie v menu."
            )
        elif category == "level_job":
            embed.title = "📈 Levelování & 🧰 Joby"
            embed.description = (
                "📈 **Levelování:**\n"
                "Získávej ⭐ XP za joby a útoky. Každá další úroveň vyžaduje více XP než předchozí.\n"
                "Např. Level 2 = 100 XP, Level 3 = 150 XP, Level 4 = 225 XP atd.\n"
                "Za vyšší rank získáváš XP rychleji! 🏅\n\n"
                "🧰 **Joby:**\n"
                "/job – Vydělej 💰 Kulhony a ⭐ XP. Cooldown ⏳ 30 min.\n"
                "Joby mají různé odměny a XP. Čím vyšší level, tím lepší joby a větší výdělky!"
            )
        elif category == "raid_potion":
            embed.title = "⚔️ Raiding & 🧪 Ochrana"
            embed.description = (
                "⚔️ **Raiding:**\n"
                "/raid @uživatel – Zaútoč na jiného hráče. Cooldown ⏳ 1h.\n"
                "Nelze útočit na hráče s aktivním lektvarem 🧪 nebo moc rozdílným levelem.\n"
                "Za úspěšný útok získáš 💰 a ⭐ XP, za prohru můžeš přijít o Kulhony!\n\n"
                "🧪 **Lektvary:**\n"
                "Lektvar chrání před útokem na 1/2/4/6 hodin. Cooldown na koupení je 5× delší než doba ochrany.\n"
                "Pro koupení je potřeba level: 1h = lvl 10, 2h = lvl 20, 4h = lvl 40, 6h = lvl 60."
            )
        elif category == "shop_upgrade":
            embed.title = "🛒 Obchod & ⚙️ Vylepšení"
            embed.description = (
                "🛒 **Obchod:**\n"
                "/shop – Zobraz obchod s boosty, upgrady a lektvary.\n\n"
                "⚙️ **Vylepšování statů:**\n"
                "V shopu můžeš vylepšovat ❤️ životy, ⚔️ damage a 🛡️ obranu. Každý upgrade má cooldown ⏳ 6h.\n\n"
                "🔒 **Výbava:**\n"
                "Některé předměty lze koupit až od určitého levelu.\n\n"
                "⏳ **Cooldowny:**\n"
                "Cooldowny na joby, raidy, boosty a lektvary se zobrazují jako čas do dalšího použití.\n\n"
                "🏆 **Žebříčky:**\n"
                "/leaderboard – Zobrazí žebříček nejlepších hráčů v různých kategoriích."
            )
        await interaction.response.edit_message(embed=embed, view=self)

class GameInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="🏆 Zobrazí žebříček nejlepších hráčů")
    async def leaderboard(self, interaction: discord.Interaction):
        gid = interaction.guild_id
        guild = interaction.guild
        view = LeaderboardView(self.bot, gid, guild)
        embed = discord.Embed(
            title="🏆 Žebříček",
            description="Vyber kategorii žebříčku pomocí menu níže.",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="player-info", description="📊 Zobrazí statistiku hráče")
    @app_commands.describe(user="Uživatel, jehož statistiku chceš vidět")
    async def player_info(self, interaction: discord.Interaction, user: discord.Member = None):
        from .config import xp_for_next_level
        # Pokud není zadán user, použij autora příkazu
        if user is None:
            user = interaction.user
        gid, uid = interaction.guild_id, user.id
        await ensure_guild_db(gid)
        async with aiosqlite.connect(get_db_path(gid)) as db:
            kulhon, xp, lvl, raid_cd, job_cd = await get_player(db, uid)
            # Načti kills, deaths, jobs_done, hp, dmg, armor, potion_protect_until
            row = await db.execute("SELECT kills, deaths, jobs_done, hp, dmg, armor, potion_protect_until FROM players WHERE user=?", (uid,))
            extra = await row.fetchone()
            if extra:
                kills, deaths, jobs_done, hp, dmg, armor, potion_protect_until = extra
            else:
                kills, deaths, jobs_done, hp, dmg, armor, potion_protect_until = 0, 0, 0, 100, 10, 0, 0

            # Načti vlastněné itemy
            owned_cursor = await db.execute("SELECT item FROM owned_items WHERE user=?", (uid,))
            owned_items = [row[0] for row in await owned_cursor.fetchall()]
            bonuses = []
            armory = []
            for item in owned_items:
                if "Boost" in item:
                    bonuses.append(item)
                if "Armor" in item or "Chestplate" in item or "Mail" in item:
                    armory.append(item)

            # Načti aktivní boosty
            now = datetime.datetime.now().timestamp()
            boost_cursor = await db.execute("SELECT boost_type, percent, expires_at FROM active_boosts WHERE user=? AND expires_at>?", (uid, now))
            active_boosts = await boost_cursor.fetchall()
            boost_list = []
            for boost_type, percent, expires_at in active_boosts:
                boost_list.append(f"{boost_type.capitalize()} Boost +{percent}% (<t:{int(expires_at)}:R>)")

        raid_remain = max(0, int(raid_cd - now))
        job_remain = max(0, int(job_cd - now))

        raid_ts = f"<t:{int(raid_cd)}:R>" if raid_remain > 0 else "✅"
        job_ts = f"<t:{int(job_cd)}:R>" if job_remain > 0 else "✅"

        # Ochrana lektvarem
        potion_ts = ""
        if potion_protect_until and potion_protect_until > now:
            potion_ts = f"🧪 Chráněn lektvarem do <t:{int(potion_protect_until)}:R>"
        else:
            potion_ts = "🧪 Bez ochrany"

        # Výpočet XP do dalšího levelu a progress bar (kumulativně)
        xp_current = xp
        xp_prev = total_xp_for_level(lvl)
        xp_next = total_xp_for_level(lvl + 1)
        xp_this_level = xp_next - xp_prev
        xp_done = xp_current - xp_prev
        xp_to_next = xp_next - xp_current
        progress = min(max(xp_done / xp_this_level, 0), 1) if xp_this_level > 0 else 1

        # Textový progress bar (10 dílků)
        filled = int(progress * 10)
        empty = 10 - filled
        progress_bar = "🟩" * filled + "⬜" * empty

        rank = get_rank(lvl)

        embed = discord.Embed(
            title=f"📋 Statistiky hráče {user.display_name}",
            color=discord.Color.gold()
        )
        embed.add_field(name="Životy ❤️", value=str(hp), inline=True)
        embed.add_field(name="Průměrný Damage ⚔️", value=str(dmg), inline=True)
        embed.add_field(name="Obrana 🛡️", value=str(armor), inline=True)
        embed.add_field(name="Kulhon 💰", value=f"{kulhon:.2f}", inline=True)
        embed.add_field(name="Level 📈", value=str(lvl), inline=True)
        embed.add_field(name="Rank 🏅", value=rank, inline=True)  # <-- přidáno
        embed.add_field(name="XP ⭐", value=f"{xp:.1f} / {xp_next:.1f} ({xp_to_next:.1f} do dalšího levelu)", inline=True)
        embed.add_field(name="XP na tento level", value=f"{xp_done:.1f} / {xp_this_level:.1f}", inline=True)
        embed.add_field(name="XP postup", value=f"{progress_bar} {int(progress*100)}%", inline=False)
        embed.add_field(name="⏳ Raid cooldown", value=raid_ts, inline=True)
        embed.add_field(name="🕒 Job cooldown", value=job_ts, inline=True)
        embed.add_field(name="🗡️ Zabití", value=str(kills), inline=True)
        embed.add_field(name="💀 Smrti", value=str(deaths), inline=True)
        embed.add_field(name="🧰 Joby hotovo", value=str(jobs_done), inline=True)
        embed.add_field(name="Aktivní boosty", value="\n".join(boost_list) if boost_list else "Žádné", inline=False)
        embed.add_field(name="Bonusy", value=", ".join(bonuses) if bonuses else "Žádné", inline=False)
        embed.add_field(name="Vybavení", value=", ".join(armory) if armory else "Žádné", inline=False)
        embed.add_field(name="Ochrana lektvarem", value=potion_ts, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="game-info", description="ℹ️ Nápověda a užitečné příkazy")
    async def game_info(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📘 Nápověda k ekonomickému systému",
            description="Vyber kategorii nápovědy v menu níže.",
            color=discord.Color.blue()
        )
        view = GameInfoInfoView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(GameInfo(bot))