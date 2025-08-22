import discord, aiosqlite
from discord import app_commands
from discord.ext import commands
from .db import get_db_path, ensure_guild_db, get_player, update_player

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_admin(self, interaction):
        return interaction.user.guild_permissions.administrator

    @app_commands.command(name="admin", description="🛠️ Univerzální admin příkaz")
    @app_commands.describe(
        type="Typ akce",
        user="Uživatel",
        value="Hodnota (číslo restart = 0)"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="Přidat Kulhony", value="add_money"),
        app_commands.Choice(name="Odebrat Kulhony", value="remove_money"),
        app_commands.Choice(name="Nastavit level", value="set_level"),
        app_commands.Choice(name="Nastavit XP", value="set_xp"),
        app_commands.Choice(name="Nastavit killů", value="set_kills"),
        app_commands.Choice(name="Nastavit smrtí", value="set_deaths"),
        app_commands.Choice(name="Přidat HP", value="add_hp"),
        app_commands.Choice(name="Odebrat HP", value="remove_hp"),
        app_commands.Choice(name="Přidat DMG", value="add_dmg"),
        app_commands.Choice(name="Odebrat DMG", value="remove_dmg"),
        app_commands.Choice(name="Přidat obranu", value="add_armor"),
        app_commands.Choice(name="Odebrat obranu", value="remove_armor"),
        app_commands.Choice(name="Restart hráče", value="restart"),
        app_commands.Choice(name="Zrušit cooldown na job", value="reset_job_cd"),      # <-- přidáno
        app_commands.Choice(name="Zrušit cooldown na raid", value="reset_raid_cd"),    # <-- přidáno
    ])
    async def admin(self, interaction: discord.Interaction, type: app_commands.Choice[str], user: discord.Member, value: float):
        if not await self.is_admin(interaction):
            return await interaction.response.send_message("Pouze admin může upravovat účty.", ephemeral=True)
        gid = interaction.guild_id
        await ensure_guild_db(gid)
        async with aiosqlite.connect(get_db_path(gid)) as db:
            if type.value == "add_money":
                kulhon, *_ = await get_player(db, user.id)
                kulhon += value
                await update_player(db, user.id, kulhon=kulhon)
                await db.commit()
                msg = f"{user.display_name} má nyní {kulhon:.2f} Kulhonů."
            elif type.value == "remove_money":
                kulhon, *_ = await get_player(db, user.id)
                kulhon = max(0, kulhon - value)
                await update_player(db, user.id, kulhon=kulhon)
                await db.commit()
                msg = f"{user.display_name} má nyní {kulhon:.2f} Kulhonů."
            elif type.value == "set_level":
                await update_player(db, user.id, lvl=int(value))
                await db.commit()
                msg = f"{user.display_name} má nyní level {int(value)}."
            elif type.value == "set_xp":
                await update_player(db, user.id, xp=value)
                await db.commit()
                msg = f"{user.display_name} má nyní {value} XP."
            elif type.value == "set_kills":
                await db.execute("UPDATE players SET kills=? WHERE user=?", (int(value), user.id))
                await db.commit()
                msg = f"{user.display_name} má nyní {int(value)} killů."
            elif type.value == "set_deaths":
                await db.execute("UPDATE players SET deaths=? WHERE user=?", (int(value), user.id))
                await db.commit()
                msg = f"{user.display_name} má nyní {int(value)} smrtí."
            elif type.value == "add_hp":
                row = await db.execute("SELECT hp FROM players WHERE user=?", (user.id,))
                hp = (await row.fetchone())[0] or 0
                hp += int(value)
                await db.execute("UPDATE players SET hp=? WHERE user=?", (hp, user.id))
                await db.commit()
                msg = f"{user.display_name} má nyní {hp} životů."
            elif type.value == "remove_hp":
                row = await db.execute("SELECT hp FROM players WHERE user=?", (user.id,))
                hp = (await row.fetchone())[0] or 0
                hp = max(0, hp - int(value))
                await db.execute("UPDATE players SET hp=? WHERE user=?", (hp, user.id))
                await db.commit()
                msg = f"{user.display_name} má nyní {hp} životů."
            elif type.value == "add_dmg":
                row = await db.execute("SELECT dmg FROM players WHERE user=?", (user.id,))
                dmg = (await row.fetchone())[0] or 0
                dmg += int(value)
                await db.execute("UPDATE players SET dmg=? WHERE user=?", (dmg, user.id))
                await db.commit()
                msg = f"{user.display_name} má nyní {dmg} damage."
            elif type.value == "remove_dmg":
                row = await db.execute("SELECT dmg FROM players WHERE user=?", (user.id,))
                dmg = (await row.fetchone())[0] or 0
                dmg = max(0, dmg - int(value))
                await db.execute("UPDATE players SET dmg=? WHERE user=?", (dmg, user.id))
                await db.commit()
                msg = f"{user.display_name} má nyní {dmg} damage."
            elif type.value == "add_armor":
                row = await db.execute("SELECT armor FROM players WHERE user=?", (user.id,))
                armor = (await row.fetchone())[0] or 0
                armor += int(value)
                await db.execute("UPDATE players SET armor=? WHERE user=?", (armor, user.id))
                await db.commit()
                msg = f"{user.display_name} má nyní {armor} obrany."
            elif type.value == "remove_armor":
                row = await db.execute("SELECT armor FROM players WHERE user=?", (user.id,))
                armor = (await row.fetchone())[0] or 0
                armor = max(0, armor - int(value))
                await db.execute("UPDATE players SET armor=? WHERE user=?", (armor, user.id))
                await db.commit()
                msg = f"{user.display_name} má nyní {armor} obrany."
            elif type.value == "reset_job_cd":
                await db.execute("UPDATE players SET job_cd=? WHERE user=?", (0, user.id))
                await db.commit()
                msg = f"Cooldown na job byl hráči {user.display_name} zrušen."
            elif type.value == "reset_raid_cd":
                await db.execute("UPDATE players SET raid_cd=? WHERE user=?", (0, user.id))
                await db.commit()
                msg = f"Cooldown na raid byl hráči {user.display_name} zrušen."
            elif type.value == "restart":
                await db.execute("DELETE FROM players WHERE user=?", (user.id,))
                await db.execute("DELETE FROM owned_items WHERE user=?", (user.id,))
                await db.execute("DELETE FROM active_boosts WHERE user=?", (user.id,))
                await db.commit()
                msg = f"Účet hráče {user.display_name} byl kompletně restartován."
            else:
                msg = "Neznámý typ akce."
        await interaction.response.send_message(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))