import discord
import psutil
import time
import os
import platform
import socket

# Globální proměnná pro počítání zpráv
message_count = 0
total_message_count = 0

def load_total_message_count():
    global total_message_count
    try:
        with open("messages_count.txt", "r") as f:
            total_message_count = int(f.read())
    except Exception:
        total_message_count = 0

def save_total_message_count():
    with open("messages_count.txt", "w") as f:
        f.write(str(total_message_count))

# Načti při startu
load_total_message_count()

# Funkce pro příkaz /info
async def info_command(interaction: discord.Interaction):
    global message_count, total_message_count
    message_count += 1  # Přičte i slash command
    total_message_count += 1
    save_total_message_count()
    this_file = os.path.abspath(__file__)  # ← Přidej tuto řádku
    """info command with system info and bot status."""
    # Získání informací o systému
    ram_usage = psutil.virtual_memory().percent  # RAM využití v %
    ram_used = psutil.virtual_memory().used / (1024 ** 3)  # Použitá RAM v GB
    ram_total = psutil.virtual_memory().total / (1024 ** 3)  # Celková RAM v GB
    cpu_usage = psutil.cpu_percent(interval=0.5)  # Využití CPU v %
    bot_uptime = time.time() - interaction.client.start_time  # Doba online bota
    server_count = len(interaction.client.guilds)  # Počet serverů, na kterých je bot
    total_members = sum(guild.member_count for guild in interaction.client.guilds)  # Počet členů na všech serverech
    latency = round(interaction.client.latency * 1000, 2)  # Latence v ms
    app_users = len(interaction.client.users)  # Počet uživatelů, kteří mají připojenou aplikaci (bot je sleduje)
    command_count = len(interaction.client.tree.get_commands())  # Počet zaregistrovaných příkazů

    # Spočítání řádků a znaků ve všech .py souborech včetně tohoto
    total_lines = 0
    total_chars = 0
    for root, dirs, files in os.walk(os.path.dirname(this_file)):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, encoding='utf-8', errors='replace') as f:
                        content = f.read()
                        total_lines += len(content.splitlines())
                        total_chars += len(content)
                except Exception:
                    pass

    # Získání informací o systému (pro Raspberry Pi 5 i jiné)
    sysinfo = {
        "OS": platform.system() + " " + platform.release(),
        "Architektura": platform.machine(),
        "Procesor": platform.processor(),
        "Hostname": socket.gethostname(),
    }
    try:
        with open("/proc/device-tree/model") as f:
            sysinfo["Model"] = f.read().strip('\x00\n')
    except Exception:
        pass

    # Získání informací o procesu bota
    proc = psutil.Process(os.getpid())
    ram_used_bot = proc.memory_info().rss / (1024 ** 2)  # RAM v MB
    cpu_usage_bot = proc.cpu_percent(interval=0.5)  # CPU v %

    # Použití Discord Timestamp pro dobu online
    bot_start_timestamp = int(interaction.client.start_time)  # Unix čas (v sekundách)
    
    # Vytvoření embed zprávy
    embed = discord.Embed(
        title="🤖 Bot Status", 
        description="Informace o botovi", 
        color=discord.Color.from_rgb(227, 159, 215)
    )
    # Základní statistiky
    embed.add_field(name="🌐 Latence", value=f"{latency} ms", inline=True)
    embed.add_field(name="🖥 Servery", value=f"{server_count}", inline=True)
    embed.add_field(name="👥 Členů", value=f"{total_members}", inline=True)

    # RAM a CPU
    embed.add_field(
        name="🧠 RAM bota",
        value=f"{ram_used_bot:.2f} MB\nz {ram_total*1024:.0f} MB ({ram_total:.2f} GB)",
        inline=True
    )
    embed.add_field(
        name="💾 CPU bota",
        value=f"{cpu_usage_bot} %",
        inline=True
    )
    embed.add_field(
        name="⏳ Uptime",
        value=f"<t:{bot_start_timestamp}:R>",
        inline=True
    )

    # Kód a příkazy
    embed.add_field(
        name="📄 Kód bota",
        value=f"{total_lines} řádků\n{total_chars} znaků",
        inline=True
    )
    embed.add_field(
        name="📦 Příkazů",
        value=f"{command_count}",
        inline=True
    )
    embed.add_field(
        name="💬 Zpráv (běh / celkem)",
        value=f"{message_count} / {total_message_count}",
        inline=True
    )

    # Systémové info
    sysinfo_text = "\n".join(f"**{k}:** {v}" for k, v in sysinfo.items())
    embed.add_field(
        name="🖥️ Systém",
        value=sysinfo_text,
        inline=False
    )

    embed.set_thumbnail(url=interaction.client.user.avatar.url)
    embed.add_field(
        name="🔗 Pozvi bota", 
        value="[INVITE](https://discord.com/oauth2/authorize?client_id=1314134553727733770&permissions=8&integration_type=0&scope=bot )", 
        inline=False
    )
    await interaction.response.send_message(embed=embed)

# Funkce pro registraci příkazu /info
def setup_info_command(bot):
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @bot.tree.command(name="info", description="Zobrazí informace o botovi.")
    async def info_command_register(interaction: discord.Interaction):
        await info_command(interaction)

# Přidej do hlavního souboru bota (např. bot.py) tuto funkci do on_message:
# async def on_message(message):
#     global message_count, total_message_count
#     message_count += 1
#     total_message_count += 1
#     save_total_message_count()
#     await bot.process_commands(message)
