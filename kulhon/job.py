import discord
import time
import random
import asyncio
import aiosqlite
from discord import app_commands
from discord.ext import commands
from .db import get_db_path, ensure_guild_db, get_player, update_player, process_level_up
from .config import LEVEL_UP_KULHON_BONUS, JOBS, get_xp_bonus_percent

class JobView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id
        for job_name, job_info in JOBS.items():
            label = f"{job_info['emoji']} {job_name.title()}"
            self.add_item(discord.ui.Button(label=label, custom_id=job_name, style=discord.ButtonStyle.primary))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

class Job(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="💼 Vykonej job pro Kulhony a XP")
    async def job(self, interaction: discord.Interaction):
        gid, uid = interaction.guild_id, interaction.user.id
        await ensure_guild_db(gid)

        jobs_list = "\n".join(
            f"{JOBS[name]['emoji']} **{name.title()}** – {JOBS[name]['money'][0]}-{JOBS[name]['money'][1]} Kulhonů, {JOBS[name]['xp'][0]}-{JOBS[name]['xp'][1]} XP"
            for name in JOBS
        )
        msg = (
            "🧰 Vyber si job, který chceš vykonat pomocí tlačítek níže:\n\n"
            f"{jobs_list}\n\n"
            "Tlačítka jsou aktivní pouze pro tebe po dobu 60 sekund."
        )
        view = JobView(uid)
        sent = await interaction.response.send_message(msg, view=view, ephemeral=True)
        message = await interaction.original_response()

        def check(i: discord.Interaction):
            return i.user.id == uid and i.message.id == message.id

        try:
            button_interaction = await interaction.client.wait_for("interaction", check=check, timeout=60)
        except asyncio.TimeoutError:
            await message.edit(content="⏰ Čas na výběr jobu vypršel.", view=None)
            return

        job = button_interaction.data["custom_id"]
        job_info = JOBS[job]

        async with aiosqlite.connect(get_db_path(gid)) as db:
            kul, xp, lvl, raid_cd, job_cd = await get_player(db, uid)
            # Načti jobs_done z DB
            row = await db.execute("SELECT jobs_done FROM players WHERE user=?", (uid,))
            jobs_done_row = await row.fetchone()
            jobs_done = jobs_done_row[0] if jobs_done_row else 0

            # Načti boosty z owned_items
            boost_cursor = await db.execute("SELECT item FROM owned_items WHERE user=?", (uid,))
            owned_items = [row[0] for row in await boost_cursor.fetchall()]
            xp_boost = 0
            for item in owned_items:
                if "Job XP Boost" in item:
                    xp_boost += 10  # každá Job XP Boost přidá 10%

            # Načti aktivní money boosty
            now = time.time()
            boost_cursor = await db.execute("SELECT percent FROM active_boosts WHERE user=? AND boost_type=? AND expires_at>?", (uid, "money", now))
            money_boosts = await boost_cursor.fetchall()
            money_boost = sum([row[0] for row in money_boosts]) if money_boosts else 0

            if now < job_cd:
                ts = f"<t:{int(job_cd)}:R>"
                await button_interaction.response.send_message(f"⏱️ Job cooldown: {ts}", ephemeral=True)
                return

            # Získej aktuální HP pro případný level up
            row = await db.execute("SELECT hp FROM players WHERE user=?", (uid,))
            hp_row = await row.fetchone()
            hp = hp_row[0] if hp_row else 100

            # Výpočet výdělku a XP včetně boostů a bonusu za rank
            earn = int(random.randint(*job_info["money"]) * (1 + money_boost / 100))
            # ZAPOČTI BONUS ZA RANK
            xp_rank_bonus = get_xp_bonus_percent(lvl)
            xp_gain = random.randint(*job_info["xp"]) * (1 + xp_boost / 100) * (1 + xp_rank_bonus)
            kul += earn
            xp += xp_gain

            # Level-up přes univerzální metodu
            xp, lvl, hp, leveled_up = await process_level_up(db, uid, xp, lvl, hp)
            if leveled_up:
                kul += LEVEL_UP_KULHON_BONUS  # bonus za level up

            await update_player(db, uid, kulhon=kul, xp=xp, lvl=lvl, job_cd=now + 1800)
            await db.execute("UPDATE players SET jobs_done=?, hp=? WHERE user=?", (jobs_done, hp, uid))
            await db.commit()

        result_msg = (
            f"{job_info['emoji']} Pracoval jsi jako **{job.title()}** a získal {earn} Kulhonů a {xp_gain:.1f} XP.\n"
        )
        if money_boost:
            result_msg += f"💸 Aktivní Money Boost: +{money_boost}%\n"
        if xp_boost:
            result_msg += f"📚 Aktivní Job XP Boost: +{xp_boost}%\n"
        if xp_rank_bonus:
            result_msg += f"🏅 Bonus za rank: +{int(xp_rank_bonus*100)}%\n"
        if leveled_up:
            result_msg += f"📈 Level up! Jsi nyní na levelu {lvl}. (+10 HP, +500 Kulhonů)\n"
        result_msg += f"🧰 Počet jobů celkem: {jobs_done}."

        await button_interaction.response.send_message(result_msg, ephemeral=True)
        await message.edit(view=None)

async def setup(bot):
    await bot.add_cog(Job(bot))