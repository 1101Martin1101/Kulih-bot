import discord
import psutil
import time

# Funkce pro příkaz /info
async def info_command(interaction: discord.Interaction):
    """info command with system info and bot status."""
    # Získání informací o systému
    ram_usage = psutil.virtual_memory().percent  # RAM využití v %
    ram_used = psutil.virtual_memory().used / (1024 ** 3)  # Použitá RAM v GB
    ram_total = psutil.virtual_memory().total / (1024 ** 3)  # Celková RAM v GB
    bot_uptime = time.time() - interaction.client.start_time  # Doba online bota
    server_count = len(interaction.client.guilds)  # Počet serverů, na kterých je bot
    total_members = sum(guild.member_count for guild in interaction.client.guilds)  # Počet členů na všech serverech
    latency = round(interaction.client.latency * 1000, 2)  # Latence v ms
    app_users = len(interaction.client.users)  # Počet uživatelů, kteří mají připojenou aplikaci (bot je sleduje)

    # Použití Discord Timestamp pro dobu online
    bot_start_timestamp = int(interaction.client.start_time)  # Unix čas (v sekundách)
    
    # Vytvoření embed zprávy
    embed = discord.Embed(
        title="🤖 Bot Status", 
        description="Informace o botovi", 
        color=discord.Color.from_rgb(227, 159, 215)
    )
    embed.add_field(name="🌐 Latence", value=f"{latency} ms", inline=False)
    embed.add_field(name="🖥 Počet serverů", value=f"{server_count}", inline=False)
    embed.add_field(name="👥 Počet členů na všech serverech", value=f"{total_members}", inline=False)
    
    embed.add_field(name="🧠 Využití RAM", value=f"{ram_usage}% ({ram_used:.2f} GB z {ram_total:.2f} GB)", inline=False)
    
    # Použití Discord timestampu pro dobu online bota
    embed.add_field(
        name="⏳ Doba online", 
        value=f"<t:{bot_start_timestamp}:R>", 
        inline=False
    )  # <t:timestamp:R> zobrazuje relativní čas od startu
    
    embed.set_thumbnail(url=interaction.client.user.avatar.url)  # Používá se URL profilového obrázku bota

    # Přidání odkazu na pozvání bota
    embed.add_field(
        name="🔗 Pozvi bota", 
        value="[INVITE](https://discord.com/oauth2/authorize?client_id=1314134553727733770&permissions=8&integration_type=0&scope=bot )", 
        inline=False
    )

    # Odeslání embed zprávy
    await interaction.response.send_message(embed=embed)

# Funkce pro registraci příkazu /info
def setup_info_command(bot):
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @bot.tree.command(name="info", description="Zobrazí informace o botovi.")
    async def info_command_register(interaction: discord.Interaction):
        await info_command(interaction)
