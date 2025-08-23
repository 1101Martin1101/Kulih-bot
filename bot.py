import discord
import time
from discord.ext import commands
import os
import pkg_resources
import sys
from kulhon.db import ensure_guild_db
from help import setup_help_command
from info import (
    setup_info_command,
    increment_command_counts,
    reset_session_count
)
from stats import setup
from fun import setup_fun_commands
#from nsfw import setup_nsfw_commands
from mod import setup_mod_commands
from minecraft import setup_minecraft_commands
from kulhon import setup_kulhon_commands
import asyncio
from cogs.reputace import setup_rep_command
import logging
import datetime

# Vytvoření složky log, pokud neexistuje
if not os.path.exists("logs"):
    os.makedirs("logs")

# Název log souboru podle dne (každý den jen jeden log)
log_filename = datetime.datetime.now().strftime("logs/bot_%Y-%m-%d.log")

# Nastavení loggeru
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s[%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def print_banner():
    logging.info("===================================")
    logging.info("         K U L I H   B O T         ")
    logging.info("===================================")
    logging.info(f"Startuji Kulih bota...  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("Autor: kulih | GitHub Copilot | https://github.com/1101Martin1101")
    logging.info("──────────────────────────────")

print_banner()

# Přesměrování stdout a stderr do loggeru
class StreamToLogger:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def flush(self):
        pass

sys.stdout = StreamToLogger(logging.getLogger(), logging.INFO)
sys.stderr = StreamToLogger(logging.getLogger(), logging.ERROR)

# Intents (lepší nastavení z prvního skriptu)
intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="+-",
    intents=intents,
    help_command=None,
    allowed_mentions=discord.AllowedMentions(everyone=True, roles=True, users=True)
)

@bot.event
async def on_ready():
    bot.start_time = time.time()
    print("────────────────────────────────────────────────────────────────────")
    logging.info(f"🟢 Bot připojen jako: {bot.user}")
    logging.info(f"🌐 Počet serverů: {len(bot.guilds)}")
    logging.info(f"👥 Celkem uživatelů: {sum(g.member_count for g in bot.guilds)}")
    logging.info(f"📦 Verze discord.py: {discord.__version__}")
    logging.info(f"📝 Počet slash commandů: {len(bot.tree.get_commands())}")
    logging.info("📦 Verze nainstalovaných pip balíčků:")

    # Výpis balíčků do 3 sloupců
    pkgs = sorted(pkg_resources.working_set, key=lambda d: d.project_name.lower())
    lines = []
    for i in range(0, len(pkgs), 3):
        cols = []
        for j in range(3):
            if i + j < len(pkgs):
                dist = pkgs[i + j]
                cols.append(f"{dist.project_name}=={dist.version}".ljust(35))
        lines.append("  ".join(cols))
    for line in lines:
        logging.info(line)

    logging.info("────────────────────────────────────────────────────────────────────")

    try:
        await bot.tree.sync()
        print("✅ Všechny příkazy synchronizovány!")
        print(f"📝 Dostupné příkazy: {[cmd.name for cmd in bot.tree.get_commands()]}")
    except Exception as e:
        print(f"❌ Chyba při synchronizaci: {e}")

    await bot.change_presence(
        activity=discord.Streaming(
            name="Napiš /help",
            url="https://twitch.tv/example"
        )
    )

@bot.event
async def on_guild_join(guild):
    await ensure_guild_db(guild.id)

@bot.event
async def on_guild_remove(guild):
    path = f"db/kulhon/economy_{guild.id}.db"
    if os.path.exists(path):
        os.remove(path)

def setup_bot_commands():
    setup_help_command(bot)
    setup_info_command(bot)
    setup(bot)  # ze stats.py
    setup_fun_commands(bot)
#    setup_nsfw_commands(bot)
    setup_mod_commands(bot)
    setup_minecraft_commands(bot)
    asyncio.run(setup_kulhon_commands(bot))
    asyncio.run(setup_rep_command(bot))
    # Přidej tento řádek pro načtení chatu:
    from chatbot.chat import setup as setup_chat
    asyncio.run(setup_chat(bot))

# Logování příkazů (slash i prefix)
@bot.event
async def on_command(ctx):
    increment_command_counts()
    user = ctx.author
    logging.info(f"{user} issued prefix command: {ctx.message.content}")

@bot.event
async def on_app_command_completion(interaction, command):
    increment_command_counts()
    user = interaction.user
    params = ""
    if interaction.data.get("options"):
        params = " ".join(
            f"{opt['name']}={opt.get('value', '')}" for opt in interaction.data["options"]
        )
    logging.info(f"{user} issued slash command: /{command.name} {params}")

# Logování chyb
@bot.event  
async def on_command_error(ctx, error):
    logging.warning(f"Error for {ctx.author}: {error}")

@bot.tree.error
async def on_app_command_error(interaction, error):
    user = interaction.user
    logging.warning(f"Slash command error for {user}: {error}")

@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return
    increment_command_counts()
    await bot.process_commands(message)

if __name__ == "__main__":
    reset_session_count()  # ← přidej tento řádek
    setup_bot_commands()
    bot.run("TOKEN")  # TVŮJ_TOKEN


