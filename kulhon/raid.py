import discord, time, random, aiosqlite
import asyncio
from discord import app_commands
from discord.ext import commands
from .db import get_db_path, ensure_guild_db, get_player, update_player, process_level_up
from .config import LEVEL_UP_KULHON_BONUS, RAID_LEVEL_RANGE, RAID_ALLOW_BOT_ATTACK, get_xp_bonus_percent

async def update_raid_stats(db, user_id, kul_delta=0, xp_delta=0, kills_delta=0, deaths_delta=0):
    # Získání aktuálních hodnot
    row = await db.execute("SELECT kulhon, xp, kills, deaths FROM players WHERE user=?", (user_id,))
    data = await row.fetchone()
    if data:
        kul, xp, kills, deaths = data
    else:
        kul, xp, kills, deaths = 0, 0, 0, 0
    kul = max(0, kul + kul_delta)
    xp = max(0, xp + xp_delta)
    kills = max(0, kills + kills_delta)
    deaths = max(0, deaths + deaths_delta)
    await db.execute(
        "UPDATE players SET kulhon=?, xp=?, kills=?, deaths=? WHERE user=?",
        (kul, xp, kills, deaths, user_id)
    )

class Raid(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(description="⚔️ Zaútoč na hráče")
    @app_commands.describe(target="Hráč, na kterého útočíš")
    async def raid(self, interaction: discord.Interaction, target: discord.Member):
        gid, attacker = interaction.guild_id, interaction.user.id
        defender = target.id
        await ensure_guild_db(gid)

        # Útok na bota podle configu
        if target.bot:
            if not RAID_ALLOW_BOT_ATTACK:
                return await interaction.response.send_message("Nelze útočit na bota!", ephemeral=True)
            # Pokud povoleno, nastav extrémní hodnoty
            def_kills, def_deaths = 0, 0
            def_hp = int(1e10)
            def_dmg = int(1e10)
            def_armor = 0
            def_lvl = 100
        else:
            async with aiosqlite.connect(get_db_path(gid)) as db:
                row = await db.execute("SELECT kills, deaths, hp, dmg, armor, lvl FROM players WHERE user=?", (defender,))
                def_extra = await row.fetchone()
                if def_extra:
                    def_kills, def_deaths, def_hp, def_dmg, def_armor, def_lvl = def_extra
                else:
                    def_kills, def_deaths, def_hp, def_dmg, def_armor, def_lvl = 0, 0, 100, 10, 0, 1

        if attacker == defender:
            return await interaction.response.send_message("Nelze útočit sám na sebe!", ephemeral=True)

        async with aiosqlite.connect(get_db_path(gid)) as db:
            kul, xp, lvl, raid_cd, _ = await get_player(db, attacker)
            row = await db.execute("SELECT kills, deaths, hp, dmg, armor, lvl FROM players WHERE user=?", (attacker,))
            extra = await row.fetchone()
            if extra:
                kills, deaths, att_hp, att_dmg, att_armor, att_lvl = extra
            else:
                kills, deaths, att_hp, att_dmg, att_armor, att_lvl = 0, 0, 100, 10, 0, 1

            row = await db.execute("SELECT potion_protect_until FROM players WHERE user=?", (defender,))
            protect_row = await row.fetchone()
            protect_until = protect_row[0] if protect_row else 0    
            now = time.time()
            if protect_until > now:
                ts = f"<t:{int(protect_until)}:R>"
                return await interaction.response.send_message(f"Hráč je chráněn lektvarem do {ts}.", ephemeral=True)

            # Kontrola rozmezí levelů (jen pokud není bot)
            if not (target.bot and RAID_ALLOW_BOT_ATTACK):
                row = await db.execute("SELECT lvl FROM players WHERE user=?", (defender,))
                def_lvl_row = await row.fetchone()
                def_lvl = def_lvl_row[0] if def_lvl_row else 1
                if abs(att_lvl - def_lvl) > RAID_LEVEL_RANGE:
                    return await interaction.response.send_message(
                        f"Můžeš útočit jen na hráče v rozmezí ±{RAID_LEVEL_RANGE} levelů od tebe.", ephemeral=True
                    )

            # Cooldown až po zahájení souboje
            if now < raid_cd:
                ts = f"<t:{int(raid_cd)}:R>"
                return await interaction.response.send_message(f"Cooldown: {ts}", ephemeral=True)

            # Boosty útočníka
            owned_cursor = await db.execute("SELECT item FROM owned_items WHERE user=?", (attacker,))
            owned_items = [row[0] for row in await owned_cursor.fetchall()]
            dmg_boost = sum([int(item.split(" ")[-1].replace("%", "")) for item in owned_items if "DMG Boost" in item])
            raid_xp_boost = sum([int(item.split(" ")[-1].replace("%", "")) for item in owned_items if "Raid XP Boost" in item])
            hp_boost = sum([int(item.split(" ")[-1].replace("%", "")) for item in owned_items if "HP Boost" in item])
            armor_boost = sum([int(item.split(" ")[-1].replace("%", "")) for item in owned_items if "Armor Boost" in item])

            # Boosty obránce
            owned_cursor = await db.execute("SELECT item FROM owned_items WHERE user=?", (defender,))
            def_owned_items = [row[0] for row in await owned_cursor.fetchall()]
            def_dmg_boost = sum([int(item.split(" ")[-1].replace("%", "")) for item in def_owned_items if "DMG Boost" in item])
            def_hp_boost = sum([int(item.split(" ")[-1].replace("%", "")) for item in def_owned_items if "HP Boost" in item])
            def_armor_boost = sum([int(item.split(" ")[-1].replace("%", "")) for item in def_owned_items if "Armor Boost" in item])

            if now < raid_cd:
                ts = f"<t:{int(raid_cd)}:R>"
                return await interaction.response.send_message(f"Cooldown: {ts}", ephemeral=True)

            # Přičti boosty k DMG, HP, ARMOR
            att_dmg = int(att_dmg * (1 + dmg_boost / 100))
            att_hp = int(att_hp * (1 + hp_boost / 100))
            att_armor = int(att_armor * (1 + armor_boost / 100))

            def_dmg = int(def_dmg * (1 + def_dmg_boost / 100))
            def_hp = int(def_hp * (1 + def_hp_boost / 100))
            def_armor = int(def_armor * (1 + def_armor_boost / 100))

            # Animace souboje v embedech
            round_num = 1
            att_cur_hp = att_hp
            def_cur_hp = def_hp

            att_hp_before = att_hp
            def_hp_before = def_hp

            total_attacker_damage = 0
            total_defender_damage = 0

            await interaction.response.defer()  # bez ephemeral=True
            embed = discord.Embed(
                title="⚔️ Raid začíná!",
                description=(
                    f"{interaction.user.mention} ({att_cur_hp}❤️, 🛡️{att_armor}) vs {target.mention} ({def_cur_hp}❤️, 🛡️{def_armor})\n"
                    f"-----------------------------"
                ),
                color=discord.Color.red()
            )
            msg = await interaction.followup.send(embed=embed)
            await asyncio.sleep(1.5)

            while att_cur_hp > 0 and def_cur_hp > 0:
                # Útočník útočí
                hit = random.randint(int(att_dmg * 0.7), int(att_dmg * 1.3))
                reduced_hit = max(1, hit - def_armor)
                def_cur_hp = max(0, def_cur_hp - reduced_hit)
                total_attacker_damage += reduced_hit
                embed = discord.Embed(
                    title=f"⚔️ Raid – Kolo {round_num}",
                    description=(
                        f"{interaction.user.mention} útočí za {hit} ⚔️ (po štítu {reduced_hit})!\n"
                        f"{interaction.user.mention}: {att_cur_hp}❤️, 🛡️{att_armor}\n"
                        f"{target.mention}: {def_cur_hp}❤️, 🛡️{def_armor}\n"
                        f"-----------------------------"
                    ),
                    color=discord.Color.orange()
                )
                await msg.edit(embed=embed)
                await asyncio.sleep(1.3)
                if def_cur_hp <= 0:
                    break

                # Obránce útočí zpět
                hit = random.randint(int(def_dmg * 0.7), int(def_dmg * 1.3))
                reduced_hit = max(1, hit - att_armor)
                att_cur_hp = max(0, att_cur_hp - reduced_hit)
                total_defender_damage += reduced_hit
                embed = discord.Embed(
                    title=f"⚔️ Raid – Kolo {round_num}",
                    description=(
                        f"{target.mention} útočí zpět za {hit} ⚔️ (po štítu {reduced_hit})!\n"
                        f"{interaction.user.mention}: {att_cur_hp}❤️, 🛡️{att_armor}\n"
                        f"{target.mention}: {def_cur_hp}❤️, 🛡️{def_armor}\n"
                        f"-----------------------------"
                    ),
                    color=discord.Color.blue()
                )
                await msg.edit(embed=embed)
                await asyncio.sleep(1.3)
                round_num += 1

            # Závěrečné shrnutí v embedu
            await asyncio.sleep(1.5)
            embed = discord.Embed(title="🏆 SOUHRN SOUBOJE 🏆", color=discord.Color.gold())
            if def_cur_hp <= 0:
                gain = int(50 * (1 + dmg_boost / 100))
                # ZÍSKEJ XP S RANK BONUS PROCENTEM
                xp_bonus = get_xp_bonus_percent(lvl)
                xp_gain = lvl * 5 * (1 + raid_xp_boost / 100) * (1 + xp_bonus)  # float, NE int()
                kul += gain
                xp += xp_gain
                kills += 1
                def_deaths += 1
                # LEVEL UP + HP NAVÝŠENÍ
                xp, lvl, att_hp, leveled_up = await process_level_up(db, attacker, xp, lvl, att_hp_before)
                if leveled_up:
                    kul += LEVEL_UP_KULHON_BONUS
                embed.description = (
                    f"**Počet kol:** {round_num}\n"
                    f"**Vítěz:** {interaction.user.mention}\n"
                    f"Získal jsi {gain} Kulhon a {xp_gain:.1f} XP.\n"
                    f"{'⬆️ LEVEL UP! (+10 HP, +500 Kulhonů)' if leveled_up else ''}"
                )
                # Úprava statistik obránce (prohra)
                await update_raid_stats(db, defender, kul_delta=-gain, deaths_delta=1)
            else:
                loss = int(30 * (1 - armor_boost / 100))
                kul = max(0, kul - loss)
                deaths += 1
                def_kills += 1
                embed.description = (
                    f"**Počet kol:** {round_num}\n"
                    f"**Vítěz:** {target.mention}\n"
                    f"Prohrál jsi a ztratil {loss} Kulhon."
                )
                # Úprava statistik obránce (výhra)
                await update_raid_stats(db, defender, kul_delta=loss, kills_delta=1)

            # Statistiky
            embed.add_field(
                name="Statistiky",
                value=(
                    f"- {interaction.user.mention} udělil {total_attacker_damage} dmg ({target.mention} přišel o {def_hp - def_cur_hp} HP)\n"
                    f"- {target.mention} udělil {total_defender_damage} dmg ({interaction.user.mention} přišel o {att_hp_before - att_cur_hp} HP)\n"
                    f"- {interaction.user.mention} zbylo {att_cur_hp} HP\n"
                    f"- {target.mention} zbylo {def_cur_hp} HP"
                ),
                inline=False
            )
            embed.add_field(
                name="Aktuální stav",
                value=(
                    f"Kulhony: {kul}\n"
                    f"XP: {xp:.1f}\n"
                    f"Level: {lvl}\n"
                    f"Max HP: {att_hp if def_cur_hp <= 0 else att_hp_before}"
                ),
                inline=False
            )

            # Po souboji nastav zpět HP na původní hodnoty (nebo nové maximum po level upu)
            await update_player(db, attacker, kulhon=kul, xp=xp, lvl=lvl, raid_cd=now + 3600)
            await db.execute("UPDATE players SET kills=?, deaths=?, hp=?, armor=? WHERE user=?", (kills, deaths, att_hp, att_armor, attacker))
            await db.execute("UPDATE players SET kills=?, deaths=?, hp=?, armor=? WHERE user=?", (def_kills, def_deaths, def_hp_before, def_armor, defender))
            await db.commit()

            await msg.edit(embed=embed, content=None)

async def setup(bot):
    await bot.add_cog(Raid(bot))