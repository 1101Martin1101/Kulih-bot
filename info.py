import discord
import psutil
import time
import os
import platform
import socket
import json

COUNT_FILE = "message_count.json"

def load_command_counts():
    if not os.path.exists(COUNT_FILE):
        return {"total": 0, "session": 0}
    with open(COUNT_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return {
                "total": data.get("total", 0),
                "session": data.get("session", 0)
            }
        except Exception:
            return {"total": 0, "session": 0}

def save_command_counts(total, session):
    with open(COUNT_FILE, "w", encoding="utf-8") as f:
        json.dump({"total": total, "session": session}, f)

def reset_session_count():
    counts = load_command_counts()
    save_command_counts(counts["total"], 0)

def increment_command_counts():
    counts = load_command_counts()
    counts["total"] += 1
    counts["session"] += 1
    save_command_counts(counts["total"], counts["session"])

def get_total_command_count():
    return load_command_counts()["total"]

def get_session_command_count():
    return load_command_counts()["session"]

# Funkce pro příkaz /info
async def info_command(interaction: discord.Interaction):
    this_file = os.path.abspath(__file__)  # ← Přidej tuto řádky
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
    total_message_count = get_total_command_count()
    session_message_count = get_session_command_count()
    embed.add_field(
        name="💬 Příkazů",
        value=f"\n(celkem / od spuštění)\n{total_message_count} / {session_message_count}",
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
        value="[INVITE](https://discord.com/oauth2/authorize?client_id=1314134553727733770&permissions=8&integration_type=0&scope=bot)", 
        inline=False
    )
    await interaction.response.send_message(embed=embed)

# Funkce pro registraci příkazu /info
def setup_info_command(bot):
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @bot.tree.command(name="ping", description="Zobrazí informace o botovi.")
    async def info_command_register(interaction: discord.Interaction):
        await info_command(interaction)
