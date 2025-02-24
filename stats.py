import discord
from discord import app_commands
from discord.utils import get

# Příkaz pro uživatele (userinfo) - funguje v PM
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.command(name="userinfo", description="Zobrazí informace o uživateli.")
@app_commands.describe(user="Uživatel, o kterém chcete získat informace (volitelné)")
async def userinfo(interaction: discord.Interaction, user: discord.Member = None):
    # Pokud není uživatel zadaný, použije se interagující uživatel
    user = user or interaction.user

    # Pokud uživatel není členem serveru, pokusíme se najít člena podle jména nebo ID
    if isinstance(user, str):
        user = get(interaction.guild.members, name=user)
    
    # Pokud stále nenajdeme uživatele podle jména, použijeme ID pro vyhledání
    if isinstance(user, str):
        user = get(interaction.guild.members, id=int(user.strip('<>@!')))

    # Pokud stále nenajdeme uživatele, použijeme interagujícího uživatele
    if not user:
        user = interaction.user

    # Aktivita uživatele
    activity = "Žádná aktivita"
    if user.activity:
        if isinstance(user.activity, discord.Streaming):
            activity = f"🎥 Streamuje: [{user.activity.name}]({user.activity.url})"
        else:
            activity = f"{user.activity.type.name.capitalize()}: {user.activity.name}"

    # Načtení detailních informací o uživatelském banneru
    detailed_user = await interaction.client.fetch_user(user.id)
    banner_url = detailed_user.banner.url if detailed_user.banner else None

    # Vytvoření embedu
    embed = discord.Embed(
        title=f"👤 Informace o uživateli {user.name}",
        description=f"Detaily o uživateli **{user.mention}**",
        color=discord.Color.from_rgb(227, 159, 215)
    )
    embed.set_thumbnail(url=user.avatar.url)  # Profilový obrázek

    # Přidání polí do embedu
    embed.add_field(name="📝 Uživatelské jméno", value=user.name, inline=True)
    embed.add_field(name="💬 ID uživatele", value=user.id, inline=True)
    embed.add_field(name="🤖 Bot?", value="Ano" if user.bot else "Ne", inline=True)
    embed.add_field(name="📅 Vytvořeno na Discordu", value=f"<t:{int(user.created_at.timestamp())}:F>", inline=False)
    
    # Pokud je příkaz na serveru, přidáme datum připojení
    if interaction.guild and hasattr(user, 'joined_at') and user.joined_at:
        embed.add_field(name="📅 Připojeno na server", value=f"<t:{int(user.joined_at.timestamp())}:F>", inline=False)

    # Přidání banneru nebo výchozího obrázku
    if banner_url:
        embed.set_image(url=banner_url)
    else:
        embed.set_image(url="https://via.placeholder.com/s.png?")  # Výchozí banner

    embed.set_footer(text=f"Požádal {interaction.user.name}")
    await interaction.response.send_message(embed=embed)

# Příkaz pro server (serverinfo) - pouze na serveru
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.command(name="serverinfo", description="Zobrazí informace o serveru.")
async def serverinfo(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("Tento příkaz může být použit pouze na serveru.", ephemeral=True)
        return

    guild = interaction.guild
    icon_url = guild.icon.url if guild.icon else "https://example.com/default_icon.png"

    embed = discord.Embed(
        title=f"🏰 Informace o serveru {guild.name}",
        description=f"Detaily o serveru **{guild.name}**",
        color=discord.Color.from_rgb(227, 159, 215)
    )
    embed.set_thumbnail(url=icon_url)
    
    embed.add_field(name="📝 Název serveru", value=guild.name, inline=True)
    embed.add_field(name="💬 ID serveru", value=guild.id, inline=True)
    embed.add_field(name="👥 Počet členů", value=guild.member_count, inline=True)
    embed.add_field(name="👑 Majitel", value=str(guild.owner), inline=True)
    embed.add_field(name="📅 Server vytvořen", value=f"<t:{int(guild.created_at.timestamp())}:F>", inline=True)
    embed.add_field(name="💎 Počet Boostů", value=guild.premium_subscription_count, inline=True)
    embed.add_field(name="⚙️ Role", value=f"{len(guild.roles)} role", inline=True)
    embed.add_field(name="🔒 Úroveň ověření", value=guild.verification_level.name, inline=True)

    embed.set_footer(text=f"Požádal {interaction.user.name}")
    await interaction.response.send_message(embed=embed)

# Funkce pro nastavení příkazů
def setup(bot):
    bot.tree.add_command(userinfo)  # Registrace příkazu /userinfo
    bot.tree.add_command(serverinfo)  # Registrace příkazu /serverinfo
