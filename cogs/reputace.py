import os
import discord
import aiosqlite
from discord.ext import commands
from discord import app_commands
from typing import List, Tuple
from datetime import datetime, timedelta
import re
import time

ATEAM_ROLE_IDS = {994372956836864041, 1137727775462150144}  # <-- doplň sem více ID rolí
REPDEL_ROLE_IDS = {1363539560616693912, 994372956836864041}  # <-- sem vlož ID rolí, které mohou mazat reputace
COOLDOWN_MINUTES = 60  # cooldown mezi hodnoceními stejného cíle od stejného hodnotitele

def is_ateam_member(member: discord.Member) -> bool:
    """Vrátí True pokud má uživatel některou z rolí A-týmu."""
    return any(r.id in ATEAM_ROLE_IDS for r in getattr(member, "roles", []))

def get_db_path(guild_id: int) -> str:
    os.makedirs("db/rep", exist_ok=True)
    return f"db/rep/reputace_{guild_id}.db"

async def ensure_db(guild_id: int):
    path = get_db_path(guild_id)
    async with aiosqlite.connect(path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reputace (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_id INTEGER,
                stars INTEGER,
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

class RepListView(discord.ui.View):
    def __init__(self, rows: List[Tuple], uzivatel: discord.Member, interaction: discord.Interaction,
                 overall_avg: float, givers_count: int, total_reviews: int, requester_avg: float, requester_count: int):
        super().__init__(timeout=120)
        self.rows = rows
        self.uzivatel = uzivatel
        self.interaction = interaction
        self.page = 0
        self.per_page = 10
        self.max_page = max(0, (len(rows) - 1) // self.per_page)

        self.overall_avg = overall_avg
        self.givers_count = givers_count
        self.total_reviews = total_reviews
        self.requester_avg = requester_avg
        self.requester_count = requester_count

        self.prev = discord.ui.Button(label="⬅️", style=discord.ButtonStyle.secondary)
        self.next = discord.ui.Button(label="➡️", style=discord.ButtonStyle.secondary)
        self.prev.callback = self.prev_page
        self.next.callback = self.next_page

        if len(rows) > self.per_page:
            self.add_item(self.prev)
            self.add_item(self.next)

    async def prev_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("Nejsi autor tohoto zobrazení.", ephemeral=True)
            return
        if self.page > 0:
            self.page -= 1
            await self.update_embed(interaction)

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("Nejsi autor tohoto zobrazení.", ephemeral=True)
            return
        if self.page < self.max_page:
            self.page += 1
            await self.update_embed(interaction)

    async def update_embed(self, interaction: discord.Interaction):
        start = self.page * self.per_page
        slice_rows = self.rows[start:start + self.per_page]

        # Autor embedu = cílový uživatel + avatar
        embed = discord.Embed(
            title=f"Reputace — {self.uzivatel.display_name}",
            color=discord.Color.blue()
        )
        if self.uzivatel.display_avatar:
            embed.set_thumbnail(url=self.uzivatel.display_avatar.url)

        # Hlavní statistiky jako pole
        embed.add_field(
            name="📊 Statistiky",
            value=f"Průměr (per hodnotitel): **{self.overall_avg:.2f}** ⭐\n"
                  f"Hodnotitelů: **{self.givers_count}** • Celkem hodnocení: **{self.total_reviews}**\n"
                  + (f"Tvůj průměr: **{self.requester_avg:.2f}** ⭐ (z {self.requester_count})" if self.requester_count > 0 else "Ty jsi tohoto člena ještě nehodnotil."),
            inline=False
        )

        # Sestav řádky hodnocení (čitelné, se zobrazením ID)
        lines = []
        for i, (entry_id, from_id, stars, reason, timestamp) in enumerate(slice_rows, start=1):
            date = timestamp[:19] if isinstance(timestamp, str) else str(timestamp)
            reason_text = reason if reason else "-"
            member = interaction.guild.get_member(from_id)
            giver = f"{member.name}#{member.discriminator}" if member else f"<@{from_id}>"
            # display id jako id{číslo}
            lines.append(f"**{i}.** [id{entry_id}] {stars}⭐ — {giver} — {date}\n**Důvod:** {reason_text}")

        # Přidej pole s hodnoceními (rozdělené podle stránky)
        if lines:
            embed.add_field(name=f"📝 Hodnocení (strana {self.page+1}/{self.max_page+1})",
                            value="\n\n".join(lines),
                            inline=False)
        else:
            embed.add_field(name="📝 Hodnocení", value="Žádná hodnocení na této straně.", inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

class TopView(discord.ui.View):
    def __init__(self, at_top: List[Tuple], overall_top: List[Tuple], guild: discord.Guild, per_page: int = 10, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.at_top = at_top
        self.overall_top = overall_top
        self.guild = guild
        self.per_page = per_page
        self.category = "at"  # 'at' nebo 'all'
        self.page = 0

        # tlačítka
        self.btn_at = discord.ui.Button(label="🔰 A-tým", style=discord.ButtonStyle.primary)
        self.btn_all = discord.ui.Button(label="🌍 Všichni", style=discord.ButtonStyle.secondary)
        self.prev = discord.ui.Button(label="⬅️", style=discord.ButtonStyle.secondary)
        self.next = discord.ui.Button(label="➡️", style=discord.ButtonStyle.secondary)

        self.btn_at.callback = self.show_at
        self.btn_all.callback = self.show_all
        self.prev.callback = self.prev_page
        self.next.callback = self.next_page

        self.add_item(self.btn_at)
        self.add_item(self.btn_all)
        self.add_item(self.prev)
        self.add_item(self.next)

    def _get_current_list(self) -> List[Tuple]:
        return self.at_top if self.category == "at" else self.overall_top

    def max_page(self) -> int:
        lst = self._get_current_list()
        if not lst:
            return 0
        return max(0, (len(lst) - 1) // self.per_page)

    async def prev_page(self, interaction: discord.Interaction):
        if interaction.user.id != getattr(self, "owner_id", interaction.user.id):
            await interaction.response.send_message("Nejsi autor tohoto zobrazení.", ephemeral=True)
            return
        if self.page > 0:
            self.page -= 1
            await self.update_embed(interaction)
        else:
            await interaction.response.defer()

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user.id != getattr(self, "owner_id", interaction.user.id):
            await interaction.response.send_message("Nejsi autor tohoto zobrazení.", ephemeral=True)
            return
        if self.page < self.max_page():
            self.page += 1
            await self.update_embed(interaction)
        else:
            await interaction.response.defer()

    async def show_at(self, interaction: discord.Interaction):
        self.category = "at"
        self.page = 0
        await self.update_embed(interaction)

    async def show_all(self, interaction: discord.Interaction):
        self.category = "all"
        self.page = 0
        await self.update_embed(interaction)

    def _format_entry(self, rank: int, user_id: int, avg_rep: float, count: int) -> str:
        member = self.guild.get_member(user_id)
        name = member.display_name if member else f"<@{user_id}>"
        emoji = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"{rank}️⃣"))
        return f"{emoji} **{name}** — {avg_rep:.2f} ⭐ ({count}×)"

    async def build_embed(self) -> discord.Embed:
        lst = self._get_current_list()
        title = "🔰 Top A-tým" if self.category == "at" else "🌍 Top všichni"
        embed = discord.Embed(title=f"🏆 {title}", color=discord.Color.gold())

        if not lst:
            embed.description = "Žádná hodnocení."
            return embed

        # vyber 1. položku pro thumbnail pokud existuje
        start = self.page * self.per_page
        slice_rows = lst[start:start + self.per_page]

        top1 = lst[0] if lst else None
        if top1:
            top1_member = self.guild.get_member(top1[0])
            if top1_member and getattr(top1_member, "display_avatar", None):
                try:
                    embed.set_thumbnail(url=top1_member.display_avatar.url)
                except Exception:
                    pass

        # hezké rozčlenění: první tři zvlášť, pak zbytek
        lines = []
        for i, (user_id, avg_rep, count) in enumerate(slice_rows, start=1 + start):
            lines.append(self._format_entry(i, user_id, avg_rep, count))
        embed.add_field(name=f"{title} — strana {self.page+1}/{self.max_page()+1}", value="\n".join(lines), inline=False)

        # doplňující informace
        embed.set_footer(text=f"Přepni kategorie / stránky pomocí tlačítek • Počet zobrazených: {len(lst)}")
        return embed

    async def update_embed(self, interaction: discord.Interaction):
        embed = await self.build_embed()
        # editovat původní zprávu
        await interaction.response.edit_message(embed=embed, view=self)

class Reputace(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # zajistit DB pro všechny guildy při načtení cogu
        for guild in self.bot.guilds:
            await ensure_db(guild.id)
        # NEREGISTROVAT RUČNĚ app_commands zde — bot.add_cog už je přidá.

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await ensure_db(guild.id)

    @app_commands.command(name="rep", description="Dej reputaci komukoliv (1-10) s důvodem")
    @app_commands.describe(
        uzivatel="Komu chceš dát reputaci",
        hvezdicky="Počet hvězdiček (1-10)",
        duvod="Důvod reputace"
    )
    async def rep(self, interaction: discord.Interaction, uzivatel: discord.Member, hvezdicky: int, duvod: str):
        if hvezdicky < 1 or hvezdicky > 10:
            await interaction.response.send_message("Počet hvězdiček musí být mezi 1 a 10.", ephemeral=False)
            return
        if uzivatel.id == interaction.user.id:
            # odeslat jako soukromou zprávu uživateli (ne veřejný embed)
            await interaction.response.send_message("Nemůžeš hodnotit sám sebe.", ephemeral=True)
            return

        await ensure_db(interaction.guild.id)
        path = get_db_path(interaction.guild.id)

        # cooldown: zkontrolovat poslední hodnocení od uživatele na tohoto cíle
        async with aiosqlite.connect(path) as db:
            async with db.execute("""
                SELECT id, timestamp FROM reputace
                WHERE user_id = ? AND from_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (uzivatel.id, interaction.user.id)) as cur:
                last = await cur.fetchone()

            if last:
                last_ts = last[1]
                try:
                    last_dt = datetime.strptime(last_ts, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    last_dt = datetime.utcnow()
                diff = datetime.utcnow() - last_dt
                remaining = timedelta(minutes=COOLDOWN_MINUTES) - diff
                if remaining.total_seconds() > 0:
                    # vypočítat epoch jako aktuální epoch + zbývající sekundy (bez timezone problémů)
                    end_epoch = int(time.time() + remaining.total_seconds())
                    await interaction.response.send_message(
                        f"Cooldown: ještě můžeš hodnotit tohoto uživatele za <t:{end_epoch}:R>.",
                        ephemeral=True
                    )
                    return

            # vložit nové hodnocení
            cur = await db.execute(
                "INSERT INTO reputace (user_id, from_id, stars, reason) VALUES (?, ?, ?, ?)",
                (uzivatel.id, interaction.user.id, hvezdicky, duvod)
            )
            await db.commit()
            entry_id = cur.lastrowid

            # získat průměr a počet
            async with db.execute(
                """
                SELECT
                    SUM(avg_stars) as overall_sum,
                    COUNT(*) as givers_count,
                    (SELECT COUNT(*) FROM reputace WHERE user_id = ?) as total_reviews
                FROM (
                    SELECT from_id, AVG(stars) AS avg_stars
                    FROM reputace
                    WHERE user_id = ?
                    GROUP BY from_id
                )
                """, (uzivatel.id, uzivatel.id)
            ) as cur2:
                row2 = await cur2.fetchone()
                overall_sum = row2[0] or 0.0
                givers_count = row2[1] or 0
                total_reviews = row2[2] or 0

            # průměr od dotazujícího uživatele (stejné jako dřív)
            async with db.execute("SELECT AVG(stars), COUNT(*) FROM reputace WHERE user_id = ? AND from_id = ?", (uzivatel.id, interaction.user.id)) as cur3:
                row3 = await cur3.fetchone()
                requester_avg = row3[0] or 0.0
                requester_count = row3[1] or 0

            # získat timestamp vloženého záznamu
            async with db.execute("SELECT timestamp FROM reputace WHERE id = ?", (entry_id,)) as cur3:
                rowt = await cur3.fetchone()
                ts = rowt[0] if rowt else None

        embed = discord.Embed(
            title="🌟 Nová reputace!",
            description=f"{uzivatel.mention} získal reputaci",
            color=discord.Color.orange()
        )

        # Thumbnail cílového uživatele
        try:
            embed.set_thumbnail(url=uzivatel.display_avatar.url)
        except Exception:
            pass

        # Hlavní pole
        embed.add_field(name="Důvod", value=duvod or "-", inline=False)
        embed.add_field(name="Počet hvězd", value=f"{hvezdicky} ⭐", inline=True)
        embed.add_field(name="Součet průměrů", value=f"{overall_sum:.2f} ⭐ (od {givers_count} hodnotitelů, {total_reviews} hodnocení celkem)", inline=True)
        embed.add_field(name="ID záznamu", value=f"id{entry_id}", inline=True)

        # Footer s informací kdo dal rep a čitelným časem vložení
        footer_time = ts if ts else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        footer_text = f"Od {interaction.user.display_name} • {footer_time}"
        embed.set_footer(text=footer_text, icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="reptop", description="Zobrazí top členy A-týmu a top všichni podle reputace")
    async def reptop(self, interaction: discord.Interaction):
        await ensure_db(interaction.guild.id)
        path = get_db_path(interaction.guild.id)
        # použij per-giver průměr (každý giver má stejnou váhu)
        async with aiosqlite.connect(path) as db:
            async with db.execute("""
                SELECT user_id, SUM(avg_stars) as sum_rep, COUNT(*) as givers
                FROM (
                    SELECT user_id, from_id, AVG(stars) as avg_stars
                    FROM reputace
                    GROUP BY user_id, from_id
                )
                GROUP BY user_id
                ORDER BY sum_rep DESC, givers DESC
                LIMIT 200
            """) as cur:
                rows = await cur.fetchall()

        guild = interaction.guild
        # rozděl na at_top (jen členové s AROLE) a overall_top (všichni)
        overall_top = rows
        at_top = []
        for user_id, avg_rep, givers in rows:
            member = guild.get_member(user_id)
            if member and is_ateam_member(member):
                at_top.append((user_id, avg_rep, givers))

        view = TopView(at_top=at_top, overall_top=overall_top, guild=guild, per_page=10)
        # nastavit owner_id pro kontrolu buttonů (autor interakce)
        view.owner_id = interaction.user.id
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

    @app_commands.command(name="replist", description="Zobrazí detailní seznam reputací pro člena")
    @app_commands.describe(uzivatel="Člen (nebo kdokoliv)")
    async def replist(self, interaction: discord.Interaction, uzivatel: discord.Member):
        await ensure_db(interaction.guild.id)
        path = get_db_path(interaction.guild.id)

        async with aiosqlite.connect(path) as db:
            async with db.execute("""
                SELECT id, from_id, stars, reason, timestamp
                FROM reputace
                WHERE user_id = ?
                ORDER BY timestamp DESC
            """, (uzivatel.id,)) as cur:
                rows = await cur.fetchall()

            # per-giver průměr + počty
            async with db.execute("""
                SELECT
                    SUM(avg_stars) as overall_sum,
                    COUNT(*) as givers_count,
                    (SELECT COUNT(*) FROM reputace WHERE user_id = ?) as total_reviews
                FROM (
                    SELECT from_id, AVG(stars) AS avg_stars
                    FROM reputace
                    WHERE user_id = ?
                    GROUP BY from_id
                )
            """, (uzivatel.id, uzivatel.id)) as cur2:
                row2 = await cur2.fetchone()
                overall_sum = row2[0] or 0.0
                givers_count = row2[1] or 0
                total_reviews = row2[2] or 0

            # průměr od dotazujícího uživatele
            async with db.execute("SELECT AVG(stars), COUNT(*) FROM reputace WHERE user_id = ? AND from_id = ?", (uzivatel.id, interaction.user.id)) as cur3:
                row3 = await cur3.fetchone()
                requester_avg = row3[0] or 0.0
                requester_count = row3[1] or 0

        if not rows:
            await interaction.response.send_message("Tento člen zatím nemá žádnou reputaci.", ephemeral=True)
            return

        view = RepListView(rows, uzivatel, interaction, overall_sum, givers_count, total_reviews, requester_avg, requester_count)

        # Stránkování
        start = 0
        slice_rows = rows[start:start + view.per_page]

        # Embed
        embed = discord.Embed(
            title=f"🌟 Reputace pro {uzivatel.display_name}",
            color=discord.Color.blurple()
        )
        if uzivatel.display_avatar:
            embed.set_thumbnail(url=uzivatel.display_avatar.url)

        # Statistika
        embed.add_field(
            name="📊 Součet průměrů od hodnotitelů",
            value=f"**{overall_sum:.2f}** ⭐\n"
                  f"Hodnotitelů: **{givers_count}**\n"
                  f"Celkem hodnocení: **{total_reviews}**",
            inline=False
        )

        # Tvé hodnocení
        if requester_count > 0:
            embed.add_field(
                name="🧑‍💻 Tvé hodnocení",
                value=f"Průměr: **{requester_avg:.2f}** ⭐ (z {requester_count})",
                inline=False
            )
        else:
            embed.add_field(
                name="🧑‍💻 Tvé hodnocení",
                value="Ty jsi tohoto člena ještě nehodnotil.",
                inline=False
            )

        # Seznam hodnocení
        if slice_rows:
            lines = []
            for i, (entry_id, from_id, stars, reason, timestamp) in enumerate(slice_rows, start=1):
                date = timestamp[:19] if isinstance(timestamp, str) else str(timestamp)
                reason_text = reason if reason else "-"
                member = interaction.guild.get_member(from_id)
                giver = f"{member.name}#{member.discriminator}" if member else f"<@{from_id}>"
                lines.append(
                    f"**{i}.** [id{entry_id}] {stars}⭐ — {giver} — {date}\n"
                    f"> *{reason_text}*"
                )
            embed.add_field(
                name=f"📝 Hodnocení (strana 1/{view.max_page+1})",
                value="\n\n".join(lines),
                inline=False
            )
        else:
            embed.add_field(
                name="📝 Hodnocení",
                value="Žádná hodnocení na této straně.",
                inline=False
            )

        embed.set_footer(text="Pouze ty vidíš tento seznam • Stránkování pomocí tlačítek dole")

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="repdel", description="Smaž reputaci podle ID (ten kdo ji vytvořil nebo admin může mazat)")
    @app_commands.describe(rep_id="ID reputace (z /replist) — napiš např. id1 nebo 1", uzivatel="Uživatel, jehož záznam mažeš (volitelné)")
    async def repdel(self, interaction: discord.Interaction, rep_id: str, uzivatel: discord.Member = None):
        # přijímáme rep_id jako string (možno "id1" nebo "1")
        rep_id_raw = rep_id.strip()
        m = re.search(r'(\d+)$', rep_id_raw)
        if not m:
            await interaction.response.send_message("Neplatné ID. Použij formát id123 nebo 123.", ephemeral=False)
            return
        rep_id_int = int(m.group(1))

        await ensure_db(interaction.guild.id)
        path = get_db_path(interaction.guild.id)
        async with aiosqlite.connect(path) as db:
            async with db.execute("SELECT user_id, from_id, stars, reason, timestamp FROM reputace WHERE id = ?", (rep_id_int,)) as cur:
                row = await cur.fetchone()

            if not row:
                await interaction.response.send_message("Záznam s tímto ID neexistuje.", ephemeral=False)
                return

            target_id, author_id, stars, reason, ts = row
            if uzivatel and uzivatel.id != target_id:
                await interaction.response.send_message("Zadaný uživatel neodpovídá tomuto záznamu.", ephemeral=False)
                return

            is_owner = interaction.user.id == interaction.guild.owner_id
            has_repdel_role = any(role.id in REPDEL_ROLE_IDS for role in getattr(interaction.user, "roles", []))
            if interaction.user.id != author_id and not is_owner and not has_repdel_role:
                await interaction.response.send_message("Nemáš oprávnění smazat tento záznam (jen autor nebo uživatel s povolenou rolí).", ephemeral=False)
                return

            await db.execute("DELETE FROM reputace WHERE id = ?", (rep_id_int,))
            await db.commit()

        embed = discord.Embed(title="🗑️ Reputace smazána", color=discord.Color.red())
        target_mention = f"<@{target_id}>"
        embed.add_field(name="Smazáno z", value=target_mention, inline=True)
        embed.add_field(name="ID záznamu", value=f"id{rep_id_int}", inline=True)
        embed.add_field(name="Hvězdy", value=str(stars), inline=True)
        embed.set_footer(text=f"Smazal {interaction.user.display_name} • {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="rephelp", description="Nápověda k rep systému")
    async def rephelp(self, interaction: discord.Interaction):
        """Krátká nápověda k použití rep příkazů (odesláno pouze tobě)."""
        embed = discord.Embed(title="🌟 Reputace — Nápověda", color=discord.Color.blurple())
        # thumbnail (bot avatar) pokud dostupný
        try:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        except Exception:
            pass

        embed.add_field(
            name="➕ /rep <uživatel> <1-10> <důvod>",
            value="Přidá reputaci komukoliv (nemůžeš hodnotit sám sebe).\nCooldown: **5 min** na hodnocení stejného cíle.\nPříklad: `/rep @Bolt 9 Skvělá práce`",
            inline=False
        )
        embed.add_field(
            name="📋 /replist <uživatel>",
            value="Zobrazí detailní, stránkovaný seznam hodnocení pro uživatele.\nZobrazuje průměr přepočítaný per hodnotitel, počet hodnotitelů a celkový počet hodnocení.",
            inline=False
        )
        embed.add_field(
            name="🏆 /reptop",
            value="Zobrazí dva TOPy: 🔰 A-tým a 🌍 všichni. Přepínání kategorií a stránkování pomocí tlačítek.",
            inline=False
        )
        embed.add_field(
            name="🗑️ /repdel <id|id123> [uživatel]",
            value="Smaže reputaci podle ID (z `/replist` → např. `id12`). Smaže autor reputace nebo správce/owner.",
            inline=False
        )
        embed.add_field(
            name="ℹ️ Formát ID",
            value="ID se zobrazuje jako `id{číslo}`. Při mazání akceptujeme `id123` i `123`.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Reputace(bot))

async def setup_rep_command(bot: commands.Bot):
    await bot.add_cog(Reputace(bot))