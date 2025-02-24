import discord
import time
from discord.ext import commands
from nsfw import setup_nsfw_commands
from help import setup_help_command
from info import setup_info_command
from stats import setup
from fun import setup_fun_commands
from mod import setup_mod_commands
from minecraft import setup_minecraft_commands
import asyncio

# ---------------------------
# NASTAVENÍ INTENTS (KRITICKÉ PRO DM)
# ---------------------------
intents = discord.Intents.default()
intents.presences = True        # Pro sledování aktivit
intents.members = True          # Pro práci s členy
intents.messages = True         # Pro příjem zpráv v DM
intents.message_content = True  # Pro čtení obsahu zpráv (NUTNÉ!)

# ---------------------------
# KONFIGURACE BOTA
# ---------------------------
bot = commands.Bot(
    command_prefix="+-",
    intents=intents,
    help_command=None,  # Vypnutí vestavěného helpu
    allowed_mentions=discord.AllowedMentions(
        everyone=True,  # Zabránit zneužití @everyone
        roles=True,
        users=True
    )
)

# ---------------------------
# EVENT: PŘIPRAVENOST BOTA
# ---------------------------
@bot.event
async def on_ready():
    # Inicializace časovače
    bot.start_time = time.time()
    
    # Výpis základních informací
    print(f"🟢 Bot připojen jako: {bot.user}")
    print(f"🌐 Počet serverů: {len(bot.guilds)}")
    print(f"👥 Celkem uživatelů: {sum(g.member_count for g in bot.guilds)}")

    try:
        # Globální synchronizace příkazů
        await bot.tree.sync()
        print("✅ Všechny příkazy synchronizovány!")
        print(f"📝 Dostupné příkazy: {[cmd.name for cmd in bot.tree.get_commands()]}")
    except Exception as e:
        print(f"❌ Chyba při synchronizaci: {e}")

    # Nastavení statusu
    await bot.change_presence(
        activity=discord.Streaming(
            name="Napiš /help",
            url="https://twitch.tv/example"
        )
    )

# ---------------------------
# REGISTRACE PŘÍKAZŮ
# ---------------------------
def setup_bot_commands():
    # Registrace všech modulů
    setup_help_command(bot)
    setup_info_command(bot)
    setup_nsfw_commands(bot)
    setup(bot)  # Příkazy ze stats.py
    setup_fun_commands(bot)
    setup_mod_commands(bot)
    setup_minecraft_commands(bot)

# ---------------------------
# SPUŠTĚNÍ BOTA
# ---------------------------
if __name__ == "__main__":
    setup_bot_commands()
    bot.run("TOKEN")  # TVŮJ_TOKEN