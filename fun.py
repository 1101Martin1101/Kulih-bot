import discord
import aiohttp
from discord import app_commands
from discord.ext import commands
import random
import string
from io import BytesIO
from PIL import Image, ImageFilter
from config import LANGUAGES
from typing import Optional, Union
from petpetgif import petpet as petpetgif
from dotenv import load_dotenv
import os
from discord.ui import View, Button
from datetime import datetime, timedelta
from PIL import Image
import tempfile

# Povolení práce v přímých zprávách
async def dm_or_guild_check(interaction: discord.Interaction):
    if not interaction.guild:
        print(f"Command used in DM by {interaction.user}.")
    return True

# Funkce pro generování náhodného řetězce
def generate_random_string(length=16):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

RICKROLL_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rickroll odkaz
NITRO_IMAGE_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRTOoRgLXFM4YkvLRwkjMIzzBoPV-wSzw6p-0K1uDs&s"  # Obrázek nahoře v rohu

# Třída pro tlačítko s Nitro
class NitroButton(View):
    def __init__(self, bot_owner_id: int):
        super().__init__(timeout=120)  # Timeout na 120 sekund
        self.bot_owner_id = bot_owner_id

    @discord.ui.button(label="ㅤㅤㅤㅤㅤㅤㅤACCEPTㅤㅤㅤㅤㅤㅤㅤ", style=discord.ButtonStyle.success, custom_id="nitro_accept", row=0)
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        # VYPSÁNÍ DO KONZOLE
        print(f"[NitroButton] Uživatelské jméno: {interaction.user} | ID: {interaction.user.id}")
        # Změna tlačítka po kliknutí
        button.label = "ㅤㅤㅤㅤㅤㅤㅤClaimedㅤㅤㅤㅤㅤㅤㅤ"
        button.style = discord.ButtonStyle.secondary
        button.disabled = True
        await interaction.response.edit_message(view=self)

        # Poslat rickroll odkaz do DM uživateli
        try:
            await interaction.user.send(f"🎉 **You got pranked!** Here's your gift: {RICKROLL_URL}")
        except discord.Forbidden:
            await interaction.followup.send("I couldn't DM you, but you got pranked anyway! 🎉", ephemeral=True)

        # Poslat zprávu majiteli bota
        owner = interaction.client.get_user(self.bot_owner_id)
        if owner:
            await owner.send(f"🎁 User {interaction.user} clicked the nitro button and got pranked!")

        # Odpověď pouze pro uživatele, který kliknul na tlačítko
        await interaction.followup.send("Nitro successfully active! Check your DMs!", ephemeral=True)

# Slash příkaz /nitro
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="nitro", description="A wild Nitro gift appears!")
async def nitro_command(interaction: discord.Interaction):
    # Vypočítat čas expirace za 47 hodin
    expire_time = datetime.now() + timedelta(hours=47)
    timestamp = int(expire_time.timestamp())  # Unix timestamp pro Discord timestamp

    # Embed zpráva
    embed = discord.Embed(
        title="A WILD GIFT APPEARS!",
        description=f"**Nitro**\nExpires <t:{timestamp}:R>",  # Discord timestamp
        color=discord.Color.from_str("#2f3136")  # Vlastní barva embedu
    )
    embed.set_thumbnail(url=NITRO_IMAGE_URL)  # Obrázek v pravém horním rohu

    # Generování náhodného odkazu
    random_string = generate_random_string()  # Generuje náhodný řetězec
    random_url = f"https://discord.gitt/{random_string}"  # Sestavení odkazu

    # Přidání tlačítka (vizuálně "větší" tlačítko)
    view = NitroButton(bot_owner_id=interaction.client.application.owner.id)

    # Odeslat zprávu s embedem a tlačítkem
    await interaction.response.send_message(
        content=random_url,  # Text v rámci jedné zprávy
        embed=embed,
        view=view
    )

# Vlastní třída pro tlačítko a View
class MemeButtonView(discord.ui.View):
    def __init__(self, timeout: Optional[int] = 120):
        super().__init__(timeout=timeout)  # Nastavení timeoutu tlačítka

    @discord.ui.button(label="Next 🥏", style=discord.ButtonStyle.success)
    async def next_meme_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Generování nového meme po stisknutí tlačítka
        await interaction.response.defer()  # Odpověď, aby uživatel nemusel čekat na potvrzení
        async with aiohttp.ClientSession() as session:
            async with session.get("https://meme-api.com/gimme") as response:
                if response.status == 200:
                    data = await response.json()
                    meme_url = data["url"]

                    # Vytvoření embed zprávy s novým meme
                    embed = discord.Embed(
                        title=data["title"],
                        description=f"Subreddit: {data['subreddit']}",
                        color=discord.Color.from_rgb(227, 159, 215)
                    )
                    embed.set_image(url=meme_url)

                    # Poslání nové zprávy s tlačítkem
                    await interaction.followup.send(embed=embed, view=MemeButtonView(timeout=120))
                else:
                    embed = discord.Embed(
                        title="Error",
                        description="There was an error fetching the meme.",
                        color=discord.Color.from_rgb(227, 159, 215)
                    )
                    await interaction.followup.send(embed=embed)

# Příkaz pro /meme
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="meme", description="Get a random meme")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def meme_command(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://meme-api.com/gimme") as response:
            if response.status == 200:
                data = await response.json()
                meme_url = data["url"]

                # Embed s prvním meme
                embed = discord.Embed(
                    title=data["title"],
                    description=f"Subreddit: {data['subreddit']}",
                    color=discord.Color.from_rgb(227, 159, 215)
                )
                embed.set_image(url=meme_url)

                # Poslání zprávy s tlačítkem
                await interaction.response.send_message(embed=embed, view=MemeButtonView(timeout=120))
            else:
                embed = discord.Embed(
                    title="Error",
                    description="There was an error fetching the meme.",
                    color=discord.Color.from_rgb(227, 159, 215)
                )
                await interaction.response.send_message(embed=embed)

# Příkaz pro /8ball
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="8ball", description="Zeptej se kouzelné 8ball koule na otázku!")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def eightball_command(interaction: discord.Interaction, question: str):
    """Odpovědět na otázku pomocí magické koule."""
    responses = [
        "Ano.",
        "Ne.",
        "Možná.",
        "Určitě.",
        "Nejsem si jistý.",
        "Počkej chvíli a zeptej se znovu.",
        "To je velmi nejasné.",
        "Není to v tuto chvíli jasné.",
    ]

    # Vyber náhodnou odpověď
    response = random.choice(responses)

    # Vytvoříme embed s odpovědí
    embed = discord.Embed(
        title="🎱 Kouzelná 8ball 🎱",
        description=f"**Otázka:** {question}\n**Odpověď:** {response}",
        color=discord.Color.from_rgb(227, 159, 215)
    )
    embed.set_thumbnail(url=interaction.client.user.avatar.url)  # Nahoře vpravo se objeví avatar bota
    embed.set_footer(text="Zeptej se na další otázku, pokud chceš!")  # Footer pro další interakce

    # Odeslání zprávy s embedem
    await interaction.response.send_message(embed=embed)

# Příkaz pro /welcome_card
@discord.app_commands.command(name="welcome_card", description="Generate a welcome card for a user")
@app_commands.check(dm_or_guild_check)  # Pokud chceš zachovat vlastní kontrolu, může zůstat
async def welcome_card_command(interaction: discord.Interaction, user: discord.User):
    avatar_url = user.display_avatar.url
    welcome_url = (
        f"https://api.popcat.xyz/welcomecard"
        f"?background=https://cdn.popcat.xyz/welcome-bg.png"
        f"&text1={user.name}&text2=Welcome&text3=Member&avatar={avatar_url}"
    )

    await interaction.response.send_message(welcome_url)


# Příkaz pro /pet
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="pet", description="Pet a member to generate a petpet gif from their profile picture")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def pet_command(interaction: discord.Interaction, user: discord.User):
    try:
        # Acknowledge the interaction immediately
        await interaction.response.defer()

        # Retrieve the mentioned user's avatar using {user.avatar.url}
        avatar_url = user.avatar.url  # Get the avatar URL (default PNG format)
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as response:
                if response.status == 200:
                    image_data = await response.read()  # Retrieve the avatar image as bytes

                    # Convert the image to a petpet gif
                    source = BytesIO(image_data)  # File-like container to hold the image in memory
                    dest = BytesIO()  # Container to store the petpet gif in memory
                    petpetgif.make(source, dest)  # Create the petpet gif
                    dest.seek(0)  # Set the file pointer back to the beginning to prevent a blank file

                    # Prepare the embed
                    embed = discord.Embed(
                        title=f"{user.name} got petpet'd!",
                        color=discord.Color.from_rgb(227, 159, 215)
                    )

                    # Attach the petpet gif to the embed
                    embed.set_image(url="attachment://petpet.gif")

                    # Send the embed with the petpet gif attached
                    await interaction.followup.send(
                        embed=embed,
                        file=discord.File(dest, filename="petpet.gif")
                    )
                else:
                    await interaction.followup.send("Error: Couldn't fetch the avatar image.", ephemeral=True)
    except Exception as e:
        # Error handling
        await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)


# Příkaz pro /blur
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="blur", description="Apply blur effect to a user's avatar")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def blur_command(interaction: discord.Interaction, user: discord.User):
    blur_url = f"https://api.popcat.xyz/blur?image={user.avatar.url}"

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.set_image(url=blur_url)

    await interaction.response.send_message(embed=embed)


# Příkaz pro /invert
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="invert", description="Invert the colors of a user's avatar")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def invert_command(interaction: discord.Interaction, user: discord.User):
    invert_url = f"https://api.popcat.xyz/invert?image={user.avatar.url}"

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.set_image(url=invert_url)

    await interaction.response.send_message(embed=embed)


# Příkaz pro /greyscale
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="greyscale", description="Convert a user's avatar to greyscale")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def greyscale_command(interaction: discord.Interaction, user: discord.User):
    greyscale_url = f"https://api.popcat.xyz/greyscale?image={user.avatar.url}"

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.set_image(url=greyscale_url)

    await interaction.response.send_message(embed=embed)


# Příkaz pro /clown
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="clown", description="Apply clown effect to a user's avatar")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def clown_command(interaction: discord.Interaction, user: discord.User):
    clown_url = f"https://api.popcat.xyz/clown?image={user.avatar.url}"

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.set_image(url=clown_url)

    await interaction.response.send_message(embed=embed)


# Příkaz pro /jail
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="jail", description="Apply jail effect to a user's avatar")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def jail_command(interaction: discord.Interaction, user: discord.User):
    jail_url = f"https://api.popcat.xyz/jail?image={user.avatar.url}"

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.set_image(url=jail_url)

    await interaction.response.send_message(embed=embed)


# Příkaz pro /wanted
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="wanted", description="Create a wanted poster effect for a user's avatar")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def wanted_command(interaction: discord.Interaction, user: discord.User):
    wanted_url = f"https://api.popcat.xyz/wanted?image={user.avatar.url}"

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.set_image(url=wanted_url)

    await interaction.response.send_message(embed=embed)


# Příkaz pro /colorify
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="colorify", description="Colorify a user's avatar with a specific color")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def colorify_command(interaction: discord.Interaction, user: discord.User, color: str):
    colorify_url = f"https://api.popcat.xyz/colorify?image={user.avatar.url}&color={color}"

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.set_image(url=colorify_url)

    await interaction.response.send_message(embed=embed)

# Příkaz pro /nokia
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="nokia", description="Apply the Nokia effect to a user's avatar")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def nokia_command(interaction: discord.Interaction, user: discord.User):
    nokia_url = f"https://api.popcat.xyz/nokia?image={user.avatar.url}"

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.set_image(url=nokia_url)

    await interaction.response.send_message(embed=embed)

# Příkaz pro /communism
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="communism", description="Apply a communism effect to a user's avatar")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def communism_command(interaction: discord.Interaction, user: discord.User):
    communism_url = f"https://api.popcat.xyz/communism?image={user.avatar.url}"

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.set_image(url=communism_url)

    await interaction.response.send_message(embed=embed)

# Příkaz pro /caution
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="caution", description="Add a caution effect to the given text")
@app_commands.check(dm_or_guild_check)
async def caution_command(interaction: discord.Interaction, text: str):
    caution_url = f"https://api.popcat.xyz/caution?text={text}"

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.set_image(url=caution_url)

    await interaction.response.send_message(embed=embed)
    
# Příkaz pro /encode 
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="encode", description="Encode the given text")
@app_commands.check(dm_or_guild_check)
async def encode_command(interaction: discord.Interaction, text: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.popcat.xyz/encode?text={text}") as response:
            data = await response.json()

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.add_field(name="Encoded Text", value=data["binary"], inline=False)
    embed.set_thumbnail(url=interaction.client.user.avatar.url)

    await interaction.response.send_message(embed=embed)

# Příkaz pro /decode
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="decode", description="Decode the given binary string")
@app_commands.check(dm_or_guild_check)
async def decode_command(interaction: discord.Interaction, binary: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.popcat.xyz/decode?binary={binary}") as response:
            data = await response.json()

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.add_field(name="Decoded Text", value=data["text"], inline=False)
    embed.set_thumbnail(url=interaction.client.user.avatar.url)

    await interaction.response.send_message(embed=embed)

# Příkaz pro /texttomorse
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="texttomorse", description="Convert text to morse code")
@app_commands.check(dm_or_guild_check)
async def text_to_morse_command(interaction: discord.Interaction, text: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.popcat.xyz/texttomorse?text={text}") as response:
            data = await response.json()

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.add_field(name="Morse Code", value=data["morse"], inline=False)
    embed.set_thumbnail(url=interaction.client.user.avatar.url)

    await interaction.response.send_message(embed=embed)

# Příkaz pro /reverse
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="reverse", description="Reverse the given text")
@app_commands.check(dm_or_guild_check)
async def reverse_command(interaction: discord.Interaction, text: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.popcat.xyz/reverse?text={text}") as response:
            data = await response.json()

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.add_field(name="Reversed Text", value=data["text"], inline=False)
    embed.set_thumbnail(url=interaction.client.user.avatar.url)

    await interaction.response.send_message(embed=embed)

# Příkaz pro /doublestruck
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="doublestruck", description="Convert text to doublestruck")
@app_commands.check(dm_or_guild_check)
async def doublestruck_command(interaction: discord.Interaction, text: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.popcat.xyz/doublestruck?text={text}") as response:
            data = await response.json()

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.add_field(name="Doublestruck Text", value=data["text"], inline=False)
    embed.set_thumbnail(url=interaction.client.user.avatar.url)

    await interaction.response.send_message(embed=embed)

# Příkaz pro /translate
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="translate", description="Translate text to the specified language")
@app_commands.check(dm_or_guild_check)
async def translate_command(interaction: discord.Interaction, text: str, language: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.popcat.xyz/translate?to={language}&text={text}") as response:
            data = await response.json()

    embed = discord.Embed(color=discord.Color.from_rgb(227, 159, 215))
    embed.add_field(name="Translated Text", value=data["translated"], inline=False)
    embed.set_thumbnail(url=interaction.client.user.avatar.url)

    await interaction.response.send_message(embed=embed)

# Autocomplete pro jazyk
@translate_command.autocomplete("language")
async def language_autocomplete(interaction: discord.Interaction, current: str):
    current = current.lower()
    matches = [discord.app_commands.Choice(name=lang[0], value=lang[1]) for lang in LANGUAGES if current in lang[0].lower()]
    return matches[:25]  # Discord omezuje autocomplete na max 25 možností


# Příkaz pro /weather
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="weather", description="Get the current weather for a city")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def weather_command(interaction: discord.Interaction, city: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.popcat.xyz/weather?q={city}") as response:
            if response.status == 200:
                data = await response.json()

                # Parse current weather data
                current_weather = data[0]["current"]
                forecast = data[0]["forecast"]

                # Prepare weather icons based on conditions
                weather_icons = {
                    "Cloudy": "☁️",
                    "Mostly cloudy": "🌥️",
                    "Clear": "☀️",
                    "Light rain and snow": "🌧️❄️",
                    "Light snow": "❄️",
                    "Rain": "🌧️🌧️",
                    "Thunderstorm": "🌩️",
                    "Windy": "💨",
                    "Fog": "🌫️",
                    "Hail": "❄️💥",
                    "Stormy": "⛈️",
                    "Drizzle": "🌦️"
                }

                # Get the current weather icon based on description
                current_weather_icon = weather_icons.get(current_weather["skytext"], "🌈")

                # Select weather image based on current condition
                weather_image = "https://images.pexels.com/photos/1118873/pexels-photo-1118873.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1"

                if "rain" in current_weather["skytext"].lower():
                    weather_image = "https://images.pexels.com/photos/459451/pexels-photo-459451.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1"
                elif "snow" in current_weather["skytext"].lower():
                    weather_image = "https://images.pexels.com/photos/3334585/pexels-photo-3334585.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1"
                elif "clear" in current_weather["skytext"].lower():
                    weather_image = "https://images.pexels.com/photos/301599/pexels-photo-301599.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1"
                elif "cloud" in current_weather["skytext"].lower():
                    weather_image = "https://images.pexels.com/photos/1154510/pexels-photo-1154510.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1"

                # Create embed with weather information
                embed = discord.Embed(
                    title=f"🌦️ Weather in {city} 🌦️",
                    description=f"{current_weather_icon} **Temperature:** {current_weather['temperature']}°C\n"
                                f"**Feels like:** {current_weather['feelslike']}°C\n"
                                f"**Sky:** {current_weather['skytext']} {current_weather_icon}\n"
                                f"**Wind:** {current_weather['windspeed']} 🌬️\n"
                                f"**Humidity:** {current_weather['humidity']}% 💧",
                    color=discord.Color.from_rgb(227, 159, 215)
                )

                # Add the weather image for current weather at the bottom
                embed.set_image(url=weather_image)

                # Add the bot's profile picture in the top-right corner
                embed.set_thumbnail(url=interaction.client.user.avatar.url)  # Používá se URL profilového obrázku bota

                # Add forecast for next days with emojis
                forecast_text = ""
                for entry in forecast:
                    forecast_text += f"**{entry['day']}**: {entry['skytextday']} {weather_icons.get(entry['skytextday'], '🌈')} | High: {entry['high']}°C, Low: {entry['low']}°C, Precip: {entry['precip']}mm\n"

                embed.add_field(name="Next days forecast 🌦️", value=forecast_text, inline=False)

                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="There was an error fetching the weather data. Please check the city name.",
                    color=discord.Color.from_rgb(227, 159, 215)
                )
                await interaction.response.send_message(embed=embed)

@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="alert", description="Generate an alert message")
@app_commands.check(dm_or_guild_check)  # Apply the check here
async def alert_command(interaction: discord.Interaction, message: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.popcat.xyz/alert?text={message}") as response:
            if response.status == 200:
                data = await response.read()
                image_url = "attachment://alert.png"  # Předpokládáme, že obrázek je ve formátu PNG

                embed = discord.Embed(
                    title="Alert",
                    description=message,
                    color=discord.Color.from_rgb(227, 159, 215)
                )
                embed.set_image(url=image_url)

                await interaction.response.send_message(  # Používáme send_message pro odpověď na interakci
                    embed=embed,
                    file=discord.File(BytesIO(data), filename="alert.png")
                )
            else:
                embed = discord.Embed(
                    title="Error",
                    description="There was an error generating the alert.",
                    color=discord.Color.from_rgb(227, 159, 215)
                )
                await interaction.response.send_message(embed=embed)

# ID role, na kterou se nesmí použít příkaz
PROTECTED_ROLE_ID = 1137727775462150144

# ID role, na kterou se nesmí běžně použít příkaz
PROTECTED_ROLE_ID = 1137727775462150144

# Command function definition for /pesti_dostanes
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="pesti_dostanes", description="Dostaneš pěsti od uživatele!")
@app_commands.check(dm_or_guild_check)
async def pesti_dostanes(interaction: discord.Interaction, user: discord.Member):
    author = interaction.user

    if not isinstance(author, discord.Member):
        await interaction.response.send_message("Tento příkaz lze použít pouze na serveru.", ephemeral=True)
        return

    user_has_protected_role = any(role.id == PROTECTED_ROLE_ID for role in user.roles)
    author_has_protected_role = any(role.id == PROTECTED_ROLE_ID for role in author.roles)

    if user_has_protected_role and not author_has_protected_role:
        await interaction.response.send_message(
            "Na tohoto uživatele nelze použít tento příkaz, protože má speciální roli.", ephemeral=True
        )
        return

    responses = [
        f"💥 {user.mention} dostal pěsti od {author.mention} jak v akčním filmu!",
        f"🥊 {author.mention} právě ukázal {user.mention}, jak chutná levá hákovka!",
        f"💢 {user.mention} právě schytal kombo od {author.mention}!",
        f"🤜 {author.mention} trefil {user.mention} tak, že to slyšela i druhá vesnice!",
        f"🌀 {user.mention} se točí jak větrník – {author.mention} ho zasáhl jak Naruto.",
        f"⚡ {author.mention} uštědřil {user.mention} takovou ránu, že se to třáslo až v Netheru!",
        f"🔥 {user.mention} byl napěchován pěstma od {author.mention}!",
        f"🧨 {author.mention} odpálil {user.mention} jak TNT bez pojistky.",
        f"🎯 Přesný zásah! {user.mention} dostal pěstí od {author.mention} rovnou mezi oči!",
        f"👊 {author.mention} seslal kombo jak v Mortal Kombatu na {user.mention}!",
        f"🛠️ {user.mention} byl doslova přeštípnut klíčem od {author.mention}.",
        f"🧱 {user.mention} si spletl boxerský ring s realitou. {author.mention} to napravil.",
        f"💨 {author.mention} proletěl na {user.mention} jak bouře a zanechal jen chaos!",
        f"📦 {user.mention} byl zabalen a odeslán expressní pěstí od {author.mention}!",
        f"🧊 {author.mention} schladil {user.mention} pěstí tak studenou, že zamrzl chat!",
        f"🚪 {user.mention} byl vykopnut z místnosti pěstí od {author.mention} – doslova!",
        f"🔨 {author.mention} použil... pěstové kladivo na {user.mention}.",
        f"🥴 {user.mention} neví, co se stalo. Jen ví, že {author.mention} má silný úder.",
        f"🪐 {user.mention} letí na oběžnou dráhu – díky pěstnímu boostu od {author.mention}!",
    ]

    response = random.choice(responses)
    await interaction.response.send_message(response)

# Command function definition for /gayrate
# Define the special users as a list of user IDs for 100% and 0%
SPECIAL_USER_0 = [267774664372256768]  # Replace with the actual special user IDs for 100%
SPECIAL_USER_1 = [771295264153141250, 927209637768495105, 730013121124630528]   # Replace with the actual special user IDs for 0%

# Command function definition for /gayrate
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="gayrate", description="Check your gay rate!")
@app_commands.check(dm_or_guild_check)  # Optional check for DM or guild
async def gayrate(interaction: discord.Interaction, user: discord.User):
    # Check if the user is in the list for 100% gay rate
    if user.id in SPECIAL_USER_0:
        percentage = 100  # Set special user's gay rate to 100%
    # Check if the user is in the list for 0% gay rate
    elif user.id in SPECIAL_USER_1:
        percentage = 0  # Set special user's gay rate to 0%
    else:
        # Generate a random percentage from 0 to 100
        percentage = random.randint(0, 100)

    # Determine the color based on the percentage
    if percentage <= 15:
        color = discord.Color.from_rgb(144, 238, 144)  # Light Green
    elif percentage <= 30:
        color = discord.Color.from_rgb(102, 205, 170)  # Medium Green
    elif percentage <= 45:
        color = discord.Color.from_rgb(0, 128, 0)  # Dark Green
    elif percentage <= 60:
        color = discord.Color.from_rgb(255, 255, 0)  # Yellow
    elif percentage <= 80:
        color = discord.Color.from_rgb(255, 165, 0)  # Orange
    else:
        color = discord.Color.from_rgb(255, 0, 0)  # Red

    # Create an embed message
    embed = discord.Embed(
        title="Gay Rate!",
        description=f"**{user.mention}** is **{percentage}% Gay**!",
        color=color
    )
    
    # Send the embed as a response
    await interaction.response.send_message(embed=embed)



# Command function definition for /simprate
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="simprate", description="Check your simp rate!")
@app_commands.check(dm_or_guild_check)  # Optional check for DM or guild
async def simprate(interaction: discord.Interaction, user: discord.User):
    # Check if the user is in the list for 100% simp rate
    if user.id in SPECIAL_USER_0:
        percentage = 100  # Set special user's simp rate to 100%
    # Check if the user is in the list for 0% simp rate
    elif user.id in SPECIAL_USER_1:
        percentage = 0  # Set special user's simp rate to 0%
    else:
        # Generate a random percentage from 0 to 100
        percentage = random.randint(0, 100)

    # Determine the color based on the percentage
    if percentage <= 15:
        color = discord.Color.from_rgb(255, 0, 0)  # Red (Low percentage)
    elif percentage <= 30:
        color = discord.Color.from_rgb(255, 165, 0)  # Orange
    elif percentage <= 45:
        color = discord.Color.from_rgb(255, 255, 0)  # Yellow
    elif percentage <= 60:
        color = discord.Color.from_rgb(0, 128, 0)  # Dark Green
    elif percentage <= 80:
        color = discord.Color.from_rgb(102, 205, 170)  # Medium Green
    else:
        color = discord.Color.from_rgb(144, 238, 144)  # Light Green (High percentage)

    # Create an embed message
    embed = discord.Embed(
        title="Simp Rate!",
        description=f"**{user.mention}** is **{percentage}% Simp**!",
        color=color
    )

    # Send the embed as a response
    await interaction.response.send_message(embed=embed)


# Command for /iq (IQ Test)
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="iq", description="Generates a random IQ score!")
@app_commands.check(dm_or_guild_check)  # Optional check for DM or guild
async def iq(interaction: discord.Interaction, user: discord.User):
    # Check if the user is in the list for a fixed IQ score of 100
    if user.id in SPECIAL_USER_1:
        iq_score = 300  # Set special user's IQ score to 100
    # Check if the user is in the list for a fixed IQ score of 0
    elif user.id in SPECIAL_USER_0:
        iq_score = 0  # Set special user's IQ score to 0
    else:
        # Generate a random IQ between 0 and 300
        iq_score = random.randint(0, 300)

    # Determine the color based on the IQ score (reversed logic)
    if iq_score <= 50:
        color = discord.Color.from_rgb(139, 0, 0)  # Dark Red (Very Low IQ)
    elif iq_score <= 100:
        color = discord.Color.from_rgb(255, 0, 0)  # Red (Low IQ)
    elif iq_score <= 150:
        color = discord.Color.from_rgb(255, 165, 0)  # Orange (Average IQ)
    elif iq_score <= 200:
        color = discord.Color.from_rgb(255, 255, 0)  # Yellow (Above Average IQ)
    elif iq_score <= 250:
        color = discord.Color.from_rgb(0, 128, 0)  # Dark Green (Genius IQ)
    else:
        color = discord.Color.from_rgb(144, 238, 144)  # Light Green (High IQ)

    # Create an embed with the IQ score
    embed = discord.Embed(
        title="IQ Test!",
        description=f"**{user.mention}**'s IQ is **{iq_score}**!",
        color=color
    )
    
    # Send the embed as a response
    await interaction.response.send_message(embed=embed)

# Command function definition for /sigmarate
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="sigmarate", description="Check your sigma rate!")
@app_commands.check(dm_or_guild_check)  # Optional check for DM or guild
async def sigmarate(interaction: discord.Interaction, user: discord.User):
    # Check if the user is in the list for 100% sigma rate
    if user.id in SPECIAL_USER_1:
        percentage = 100  # Set special user's sigma rate to 100%
    # Check if the user is in the list for 0% sigma rate
    elif user.id in SPECIAL_USER_0:
        percentage = 0  # Set special user's sigma rate to 0%
    else:
        # Generate a random percentage from 0 to 100
        percentage = random.randint(0, 100)

    # Determine the color based on the percentage
    if percentage <= 15:
        color = discord.Color.from_rgb(255, 0, 0)  # Red (Low percentage)
    elif percentage <= 30:
        color = discord.Color.from_rgb(255, 165, 0)  # Orange
    elif percentage <= 45:
        color = discord.Color.from_rgb(255, 255, 0)  # Yellow
    elif percentage <= 60:
        color = discord.Color.from_rgb(0, 128, 0)  # Dark Green
    elif percentage <= 80:
        color = discord.Color.from_rgb(102, 205, 170)  # Medium Green
    else:
        color = discord.Color.from_rgb(144, 238, 144)  # Light Green (High percentage)

    # Create an embed message
    embed = discord.Embed(
        title="Sigma Rate!",
        description=f"**{user.mention}** is **{percentage}% Sigma**!",
        color=color
    )

    # Send the embed as a response
    await interaction.response.send_message(embed=embed)

# Command function definition for /skibidirate
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="skibidirate", description="Check your skibidi rate!")
@app_commands.check(dm_or_guild_check)  # Optional check for DM or guild
async def skibidirate(interaction: discord.Interaction, user: discord.User):
    # Check if the user is in the list for 100% skibidi rate
    if user.id in SPECIAL_USER_0:
        percentage = 100  # Set special user's skibidi rate to 100%
    # Check if the user is in the list for 0% skibidi rate
    elif user.id in SPECIAL_USER_1:
        percentage = 0  # Set special user's skibidi rate to 0%
    else:
        # Generate a random percentage from 0 to 100
        percentage = random.randint(0, 100)

    # Determine the color based on the percentage
    if percentage <= 15:
        color = discord.Color.from_rgb(144, 238, 144)  # Light Green
    elif percentage <= 30:
        color = discord.Color.from_rgb(102, 205, 170)  # Medium Green
    elif percentage <= 45:
        color = discord.Color.from_rgb(0, 128, 0)  # Dark Green
    elif percentage <= 60:
        color = discord.Color.from_rgb(255, 255, 0)  # Yellow
    elif percentage <= 80:
        color = discord.Color.from_rgb(255, 165, 0)  # Orange
    else:
        color = discord.Color.from_rgb(255, 0, 0)  # Red

    # Create an embed message
    embed = discord.Embed(
        title="Skibidi Rate!",
        description=f"**{user.mention}** is **{percentage}% Skibidi**!",
        color=color
    )

    # Send the embed as a response
    await interaction.response.send_message(embed=embed)



# Funkce pro nastavení příkazů
def setup_fun_commands(bot):
    # Register the existing commands with the bot's command tree
    bot.tree.add_command(meme_command)
    bot.tree.add_command(eightball_command)
    bot.tree.add_command(welcome_card_command)
    bot.tree.add_command(pet_command)
    bot.tree.add_command(weather_command)
    bot.tree.add_command(alert_command)
    bot.tree.add_command(blur_command)
    bot.tree.add_command(invert_command)
    bot.tree.add_command(greyscale_command)
    bot.tree.add_command(clown_command)
    bot.tree.add_command(jail_command)
    bot.tree.add_command(wanted_command)
    bot.tree.add_command(colorify_command)
    bot.tree.add_command(nokia_command)
    bot.tree.add_command(communism_command)
    bot.tree.add_command(encode_command)
    bot.tree.add_command(decode_command)
    bot.tree.add_command(text_to_morse_command)
    bot.tree.add_command(reverse_command)
    bot.tree.add_command(doublestruck_command)
    bot.tree.add_command(caution_command)
    bot.tree.add_command(translate_command)
    bot.tree.add_command(nitro_command)
    bot.tree.add_command(pesti_dostanes)
    bot.tree.add_command(gayrate)
    bot.tree.add_command(simprate)
    bot.tree.add_command(iq)
    bot.tree.add_command(sigmarate)
    bot.tree.add_command(skibidirate)