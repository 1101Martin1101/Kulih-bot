import discord
import asyncio
import requests
from discord import app_commands
from config import ImageTypes  # Předpokládáme, že máš nastavené různé typy obrázků

# NSFW klient pro správu obrázků
class NSFWClient:
    def __init__(self):
        self.image_type = None  # Typ obrázku
        self.channel = None  # Kanál pro posílání obrázků
        self.send_interval = 5  # Výchozí interval pro posílání obrázků (sekundy)
        self.task = None  # Asynchronní úkol pro posílání obrázků
        self.max_images = 50  # Maximální počet obrázků (omezeno na 50)

    def parse_time(self, time_str):
        """Převede časový řetězec ('5s', '1m', '1h') na sekundy."""
        num = int(time_str[:-1])
        unit = time_str[-1]
        return num * {'s': 1, 'm': 60, 'h': 3600}.get(unit, 5)

    async def send_image(self):
        """Odešle obrázek dle zvoleného typu."""
        if self.channel and self.image_type:
            try:
                response = requests.get(f"https://nekobot.xyz/api/image?type={self.image_type}")
                if response.status_code == 200:
                    image_url = response.json().get("message")
                    
                    # Vylepšený Embed pro zobrazení obrázku
                    embed = discord.Embed(
                        title=f"NSFW Image: {self.image_type}",
                        description=f"Type: {self.image_type}",
                        color=discord.Color.from_rgb(227, 159, 215)
                    )
                    embed.set_image(url=image_url)
                    await self.channel.send(embed=embed)
                else:
                    print("Error fetching image.")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("Channel or image type not set.")

    async def send_images_periodically(self):
        """Posílání obrázků po intervalech.""" 
        for i in range(self.max_images):
            await self.send_image()
            await asyncio.sleep(self.send_interval)
        self.task = None

    async def stop_sending_images(self):
        """Zastaví odesílání obrázků.""" 
        if self.task:
            self.task.cancel()
            self.task = None

# Vytvoření instance klienta pro NSFW
nsfw_client = NSFWClient()

# Příkaz /startgen
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="startgen", description="Start generating images.")
async def startgen(interaction: discord.Interaction, type: str, interval: str, count: int):
    # Zkontrolujeme, zda je interakce ve veřejném kanálu (serveru)
    if interaction.guild:  # Je to serverová zpráva
        nsfw_role = discord.utils.get(interaction.guild.roles, name="nsfw")
        
        # Kontrola role na serveru
        if not nsfw_role or nsfw_role not in interaction.user.roles:
            await interaction.response.send_message(
                "Nemáš práva pro použití tohoto příkazu. Potřebuješ roli **nsfw**.",
                ephemeral=True
            )
            return
    
    # Kontrola platného typu obrázku
    if type in ImageTypes.values():
        nsfw_client.image_type = type
        nsfw_client.channel = interaction.channel
        nsfw_client.send_interval = nsfw_client.parse_time(interval)
        
        # Omezíme maximální počet obrázků na 50
        nsfw_client.max_images = min(count, 50)

        # Informativní embed o začátku generování obrázků
        embed = discord.Embed(
            title="Začíná generování obrázků",
            description=f"**Kategorie**: {type}\n**Interval**: {interval}\n**Počet obrázků**: {nsfw_client.max_images}",
            color=discord.Color.from_rgb(227, 159, 215)
        )
        
        # Přidání profilové fotky bota vpravo
        embed.set_footer(text="Generováno botem", icon_url=interaction.client.user.avatar.url)

        await interaction.response.send_message(embed=embed)

        if nsfw_client.task:
            nsfw_client.task.cancel()  # Zastavíme stávající úlohu, pokud existuje

        nsfw_client.task = asyncio.create_task(nsfw_client.send_images_periodically())
    else:
        await interaction.response.send_message(
            f"Neplatný typ obrázku. K dispozici jsou tyto typy: {', '.join(ImageTypes.keys())}"
        )

# Příkaz /stopgen
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="stopgen", description="Stop generating images.")
async def stopgen(interaction: discord.Interaction):
    # Zkontrolujeme, zda je interakce ve veřejném kanálu (serveru)
    if interaction.guild:  # Je to serverová zpráva
        nsfw_role = discord.utils.get(interaction.guild.roles, name="nsfw")
        
        # Kontrola role na serveru
        if not nsfw_role or nsfw_role not in interaction.user.roles:
            await interaction.response.send_message(
                "Nemáš práva pro použití tohoto příkazu. Potřebuješ roli **nsfw**.",
                ephemeral=True
            )
            return

    # Zastavení generování obrázků
    await nsfw_client.stop_sending_images()
    
    # Informativní embed pro zastavení generování obrázků
    embed = discord.Embed(
        title="Generování obrázků bylo zastaveno",
        description="Generování obrázků bylo úspěšně zastaveno.",
        color=discord.Color.from_rgb(227, 159, 215)
    )
    
    # Přidání profilové fotky bota vpravo
    embed.set_footer(text="Generováno botem", icon_url=interaction.client.user.avatar.url)

    await interaction.response.send_message(embed=embed)

# Autocomplete pro typy obrázků
@startgen.autocomplete("type")
async def image_type_autocomplete(interaction: discord.Interaction, current: str):
    return [
        discord.app_commands.Choice(name=type, value=type)
        for type in ImageTypes.keys()
        if current.lower() in type.lower()
    ]

# Funkce pro nastavení příkazů v hlavním botovi
def setup_nsfw_commands(bot):
    bot.tree.add_command(startgen)
    bot.tree.add_command(stopgen)