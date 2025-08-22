import discord, random, aiosqlite, asyncio, time
from discord import app_commands
from discord.ext import commands
from .db import get_db_path, ensure_guild_db, get_player, update_player, process_level_up
from .config import (
    LEVEL_UP_KULHON_BONUS,
    COINFLIP_WIN_CHANCE,
    SHELLGAME_WIN_CHANCE,
    SLOTMACHINE_JACKPOT_CHANCE,
    SLOTMACHINE_DOUBLE_CHANCE,
    COINFLIP_COOLDOWN,
    SHELLGAME_COOLDOWN,
    SLOTMACHINE_COOLDOWN,
    DICEDUEL_COOLDOWN,
    get_xp_bonus_percent,
)

COOLDOWN_TABLE = "game_cooldowns"

async def ensure_cooldown_table(db):
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS {COOLDOWN_TABLE} (
            user INTEGER,
            command TEXT,
            expires_at REAL,
            PRIMARY KEY (user, command)
        );
    """)

async def get_cooldown(db, user_id, command):
    await ensure_cooldown_table(db)
    row = await db.execute(
        f"SELECT expires_at FROM {COOLDOWN_TABLE} WHERE user=? AND command=?",
        (user_id, command)
    )
    data = await row.fetchone()
    return data[0] if data else 0

async def set_cooldown(db, user_id, command, seconds):
    await ensure_cooldown_table(db)
    expires_at = time.time() + seconds
    await db.execute(
        f"INSERT OR REPLACE INTO {COOLDOWN_TABLE} (user, command, expires_at) VALUES (?, ?, ?)",
        (user_id, command, expires_at)
    )
    await db.commit()
    return expires_at

class Coinflip(commands.Cog):
    def __init__(self, bot): self.bot = bot

    async def check_cooldown(self, interaction, cmd_name, cooldown_seconds):
        uid = interaction.user.id
        gid = interaction.guild_id
        async with aiosqlite.connect(get_db_path(gid)) as db:
            now = time.time()
            expires_at = await get_cooldown(db, uid, cmd_name)
            if expires_at > now:
                ts = f"<t:{int(expires_at)}:R>"
                embed = discord.Embed(
                    description=f"⏳ Tento příkaz má cooldown! Zkus to znovu {ts}.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return False
            await set_cooldown(db, uid, cmd_name, cooldown_seconds)
        return True

    @app_commands.command(description="🪙 Coinflip sázení")
    @app_commands.describe(amount="Sázka v Kulhonech")
    async def coinflip(self, interaction: discord.Interaction, amount: float):
        if not await self.check_cooldown(interaction, "coinflip", COINFLIP_COOLDOWN):
            return
        gid, uid = interaction.guild_id, interaction.user.id
        await ensure_guild_db(gid)
        embed = discord.Embed(title="🪙 Coinflip", color=discord.Color.gold())
        embed.set_footer(text=f"{interaction.user.display_name} | Coinflip", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(0.7)
        # Animace coinflip
        for flip in ["🪙 **Hodím mincí...**", "🪙 **Točí se...**", "🪙 **Padne...**"]:
            embed.description = flip
            await interaction.edit_original_response(embed=embed)
            await asyncio.sleep(0.7)
        async with aiosqlite.connect(get_db_path(gid)) as db:
            kul, xp, lvl, _, _ = await get_player(db, uid)
            row = await db.execute("SELECT hp FROM players WHERE user=?", (uid,))
            hp_row = await row.fetchone()
            hp = hp_row[0] if hp_row else 100
            if amount <= 0 or amount > kul:
                await interaction.edit_original_response(embed=discord.Embed(
                    description=f"❌ Neplatná sázka. Máš {kul} Kulhonů.", color=discord.Color.red()))
                return
            if random.randint(1, 100) <= COINFLIP_WIN_CHANCE:
                kul += amount
                # ZAPOČTI BONUS ZA RANK
                xp_rank_bonus = get_xp_bonus_percent(lvl)
                xp_gain = 5 * (1 + xp_rank_bonus)
                xp += xp_gain
                result = f"🎉 Padla **výhra**! Vyhráváš {amount} Kulhonů a {xp_gain:.1f} XP!"
            else:
                kul -= amount
                xp_gain = 0
                result = f"😢 Padla **prohra**! Přicházíš o {amount} Kulhonů."
            xp, lvl, hp, leveled_up = await process_level_up(db, uid, xp, lvl, hp)
            if leveled_up:
                kul += LEVEL_UP_KULHON_BONUS
            await update_player(db, uid, kulhon=kul, xp=xp, lvl=lvl)
            await db.execute("UPDATE players SET hp=? WHERE user=?", (hp, uid))
            await db.commit()
            embed.description = result
            embed.add_field(name="Kulhony", value=f"{kul}", inline=True)
            embed.add_field(name="XP", value=f"{xp:.1f}", inline=True)
            embed.add_field(name="Level", value=f"{lvl}", inline=True)
            if xp_gain:
                embed.add_field(name="🏅 Bonus za rank", value=f"+{int(xp_rank_bonus*100)}%", inline=True)
            if leveled_up:
                embed.add_field(name="⬆️ LEVEL UP!", value=f"+10 HP, +500 Kulhonů, +2 DMG", inline=False)
            await interaction.edit_original_response(embed=embed)

    @app_commands.command(description="🎲 Skořápky – hádej pod kterou je výhra")
    @app_commands.describe(amount="Sázka v Kulhonech", shell="Vyber skořápku (1-3)")
    async def shellgame(self, interaction: discord.Interaction, amount: float, shell: int):
        if not await self.check_cooldown(interaction, "shellgame", SHELLGAME_COOLDOWN):
            return
        gid, uid = interaction.guild_id, interaction.user.id
        await ensure_guild_db(gid)
        if shell not in [1, 2, 3]:
            await interaction.response.send_message("Vyber skořápku 1, 2 nebo 3.", ephemeral=True)
            return
        embed = discord.Embed(title="🎲 Skořápky", color=discord.Color.green())
        embed.set_footer(text=f"{interaction.user.display_name} | Skořápky", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(0.7)
        # Animace míchání skořápek
        for anim in [
            "🥚🥚🥚 **Míchám skořápky...**",
            "🥚🥚🥚 **Točím...**",
            "🥚🥚🥚 **Kde je výhra?**"
        ]:
            embed.description = anim
            await interaction.edit_original_response(embed=embed)
            await asyncio.sleep(0.7)
        win_shell = random.randint(1, 3)
        cracked = ["🥚", "🥚", "🥚"]
        cracked[win_shell-1] = "💥"
        embed.description = f"{' '.join(cracked)}"
        await interaction.edit_original_response(embed=embed)
        await asyncio.sleep(0.7)

        async with aiosqlite.connect(get_db_path(gid)) as db:
            kul, xp, lvl, _, _ = await get_player(db, uid)
            row = await db.execute("SELECT hp FROM players WHERE user=?", (uid,))
            hp_row = await row.fetchone()
            hp = hp_row[0] if hp_row else 100
            if amount <= 0 or amount > kul:
                embed = discord.Embed(
                    description=f"❌ Neplatná sázka. Máš {kul} Kulhonů.", color=discord.Color.red())
                await interaction.edit_original_response(embed=embed)
                return
            # Vyhodnocení podle šance v configu
            if shell == win_shell and random.randint(1, 100) <= SHELLGAME_WIN_CHANCE:
                kul += amount
                xp_rank_bonus = get_xp_bonus_percent(lvl)
                xp_gain = 10 * (1 + xp_rank_bonus)
                xp += xp_gain
                result = f"🎉 Našel jsi výhru pod skořápkou {win_shell}! Získáváš {amount} Kulhonů a {xp_gain:.1f} XP!"
            else:
                kul -= amount
                xp_gain = 0
                result = f"😢 Výhra byla pod skořápkou {win_shell}. Přicházíš o {amount} Kulhonů."
            xp, lvl, hp, leveled_up = await process_level_up(db, uid, xp, lvl, hp)
            if leveled_up:
                kul += LEVEL_UP_KULHON_BONUS
            await update_player(db, uid, kulhon=kul, xp=xp, lvl=lvl)
            await db.execute("UPDATE players SET hp=? WHERE user=?", (hp, uid))
            await db.commit()
            embed.description = result
            embed.clear_fields()
            embed.add_field(name="Kulhony", value=f"{kul}", inline=True)
            embed.add_field(name="XP", value=f"{xp:.1f}", inline=True)
            embed.add_field(name="Level", value=f"{lvl}", inline=True)
            if xp_gain:
                embed.add_field(name="🏅 Bonus za rank", value=f"+{int(xp_rank_bonus*100)}%", inline=True)
            if leveled_up:
                embed.add_field(name="⬆️ LEVEL UP!", value=f"+10 HP, +500 Kulhonů, +2 DMG", inline=False)
            await interaction.edit_original_response(embed=embed)

    @app_commands.command(description="🎰 Slot Machine – zatoč automatem")
    @app_commands.describe(amount="Sázka v Kulhonech")
    async def slotmachine(self, interaction: discord.Interaction, amount: float):
        if not await self.check_cooldown(interaction, "slotmachine", SLOTMACHINE_COOLDOWN):
            return
        gid, uid = interaction.guild_id, interaction.user.id
        await ensure_guild_db(gid)
        embed = discord.Embed(title="🎰 Slot Machine", color=discord.Color.purple())
        embed.set_footer(text=f"{interaction.user.display_name} | Slot Machine", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(0.7)
        symbols = ["🍒", "🍋", "🔔", "⭐", "💎"]
        for _ in range(5):
            fake_spin = [random.choice(symbols) for _ in range(3)]
            embed.description = f"🎰 {' '.join(fake_spin)}"
            await interaction.edit_original_response(embed=embed)
            await asyncio.sleep(0.5)
        async with aiosqlite.connect(get_db_path(gid)) as db:
            kul, xp, lvl, _, _ = await get_player(db, uid)
            row = await db.execute("SELECT hp FROM players WHERE user=?", (uid,))
            hp_row = await row.fetchone()
            hp = hp_row[0] if hp_row else 100
            if amount <= 0 or amount > kul:
                embed = discord.Embed(
                    description=f"❌ Neplatná sázka. Máš {kul} Kulhonů.", color=discord.Color.red())
                await interaction.edit_original_response(embed=embed)
                return
            spin = [random.choice(symbols) for _ in range(3)]
            result_str = " ".join(spin)
            jackpot = spin[0] == spin[1] == spin[2]
            double = spin[0] == spin[1] or spin[1] == spin[2] or spin[0] == spin[2]
            if jackpot and random.randint(1, 100) <= SLOTMACHINE_JACKPOT_CHANCE:
                win = amount * 5
                kul += win
                xp_rank_bonus = get_xp_bonus_percent(lvl)
                xp_gain = 15 * (1 + xp_rank_bonus)
                xp += xp_gain
                result = f"🎉 {result_str}\nJackpot! Vyhráváš {win} Kulhonů a {xp_gain:.1f} XP!"
            elif double and random.randint(1, 100) <= SLOTMACHINE_DOUBLE_CHANCE:
                win = amount * 2
                kul += win
                xp_rank_bonus = get_xp_bonus_percent(lvl)
                xp_gain = 7 * (1 + xp_rank_bonus)
                xp += xp_gain
                result = f"✨ {result_str}\nDva stejné! Vyhráváš {win} Kulhonů a {xp_gain:.1f} XP!"
            else:
                kul -= amount
                xp_gain = 0
                result = f"😢 {result_str}\nNic moc! Přicházíš o {amount} Kulhonů."
            xp, lvl, hp, leveled_up = await process_level_up(db, uid, xp, lvl, hp)
            if leveled_up:
                kul += LEVEL_UP_KULHON_BONUS
            await update_player(db, uid, kulhon=kul, xp=xp, lvl=lvl)
            await db.execute("UPDATE players SET hp=? WHERE user=?", (hp, uid))
            await db.commit()
            embed.description = result
            embed.clear_fields()
            embed.add_field(name="Kulhony", value=f"{kul}", inline=True)
            embed.add_field(name="XP", value=f"{xp:.1f}", inline=True)
            embed.add_field(name="Level", value=f"{lvl}", inline=True)
            if xp_gain:
                embed.add_field(name="🏅 Bonus za rank", value=f"+{int(xp_rank_bonus*100)}%", inline=True)
            if leveled_up:
                embed.add_field(name="⬆️ LEVEL UP!", value=f"+10 HP, +500 Kulhonů, +2 DMG", inline=False)
            await interaction.edit_original_response(embed=embed)

    @app_commands.command(description="🎲 Dice Duel – souboj kostek s botem")
    @app_commands.describe(amount="Sázka v Kulhonech", guess="Tipni si číslo (1-6)")
    async def diceduel(self, interaction: discord.Interaction, amount: float, guess: int):
        if not await self.check_cooldown(interaction, "diceduel", DICEDUEL_COOLDOWN):
            return
        if guess not in range(1, 7):
            await interaction.response.send_message("Zadej číslo od 1 do 6!", ephemeral=True)
            return
        gid, uid = interaction.guild_id, interaction.user.id
        await ensure_guild_db(gid)
        embed = discord.Embed(title="🎲 Dice Duel", color=discord.Color.blue())
        embed.set_footer(text=f"{interaction.user.display_name} | Dice Duel", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(0.7)
        # Animace házení kostek
        for anim in [
            "🎲 **Házíš kostkou...**",
            "🎲 **Kostka se kutálí...**",
            "🎲 **Padne číslo...**"
        ]:
            embed.description = anim
            await interaction.edit_original_response(embed=embed)
            await asyncio.sleep(0.7)
        async with aiosqlite.connect(get_db_path(gid)) as db:
            kul, xp, lvl, _, _ = await get_player(db, uid)
            row = await db.execute("SELECT hp FROM players WHERE user=?", (uid,))
            hp_row = await row.fetchone()
            hp = hp_row[0] if hp_row else 100
            if amount <= 0 or amount > kul:
                embed = discord.Embed(
                    description=f"❌ Neplatná sázka. Máš {kul} Kulhonů.", color=discord.Color.red())
                await interaction.edit_original_response(embed=embed)
                return
            player_roll = random.randint(1, 6)
            bot_roll = random.randint(1, 6)
            if player_roll == guess:
                kul += amount
                xp_rank_bonus = get_xp_bonus_percent(lvl)
                xp_gain = 12 * (1 + xp_rank_bonus)
                xp += xp_gain
                result = f"🎲 Tipoval jsi **{guess}** a padlo **{player_roll}**!\nVyhráváš {amount} Kulhonů a {xp_gain:.1f} XP!\nBot hodil {bot_roll}."
            elif player_roll > bot_roll:
                kul += amount
                xp_rank_bonus = get_xp_bonus_percent(lvl)
                xp_gain = 8 * (1 + xp_rank_bonus)
                xp += xp_gain
                result = f"🎲 Hodil jsi {player_roll}, bot {bot_roll}.\nVyhráváš {amount} Kulhonů a {xp_gain:.1f} XP!"
            elif player_roll < bot_roll:
                kul -= amount
                xp_gain = 0
                result = f"😢 Hodil jsi {player_roll}, bot {bot_roll}.\nProhráváš {amount} Kulhonů."
            else:
                xp_gain = 0
                result = f"🤝 Remíza! Oba {player_roll}. Sázka se vrací."
            xp, lvl, hp, leveled_up = await process_level_up(db, uid, xp, lvl, hp)
            if leveled_up:
                kul += LEVEL_UP_KULHON_BONUS
            await update_player(db, uid, kulhon=kul, xp=xp, lvl=lvl)
            await db.execute("UPDATE players SET hp=? WHERE user=?", (hp, uid))
            await db.commit()
            embed.description = result
            embed.clear_fields()
            embed.add_field(name="Kulhony", value=f"{kul}", inline=True)
            embed.add_field(name="XP", value=f"{xp:.1f}", inline=True)
            embed.add_field(name="Level", value=f"{lvl}", inline=True)
            if xp_gain:
                embed.add_field(name="🏅 Bonus za rank", value=f"+{int(xp_rank_bonus*100)}%", inline=True)
            if leveled_up:
                embed.add_field(name="⬆️ LEVEL UP!", value=f"+10 HP, +500 Kulhonů, +2 DMG", inline=False)
            await interaction.edit_original_response(embed=embed)

async def setup(bot):
    await bot.add_cog(Coinflip(bot))