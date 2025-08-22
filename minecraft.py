import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import random
import requests
from config import ITEM_IDS
import urllib.parse
from bs4 import BeautifulSoup

# Funkce pro získání UUID hráče z API Mojangu
def get_uuid(username):
    try:
        response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{urllib.parse.quote(username)}")
        if response.status_code == 200:
            return response.json().get("id")
        return None
    except Exception as e:
        print(f"Chyba při získávání UUID: {e}")
        return None

# Příkaz /mchead
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="mchead", description="Get Minecraft player's head and information.")
async def mchead(interaction: discord.Interaction, username: str):
    uuid = get_uuid(username)
    if uuid:
        namemc_url = f"https://namemc.com/profile/{uuid}"
        give_command = f"/give @s player_head{{SkullOwner:{username}}}"
        head_url = f"https://mc-heads.net/avatar/{uuid}/128"  # URL pro hlavu hráče
        large_head_url = f"https://mc-heads.net/head/{uuid}/256"  # URL pro velkou hlavu hráče
        
        # Embed zpráva
        embed = discord.Embed(
            color=discord.Color.from_rgb(227, 159, 215)
        )
        
        # Nastavení autora
        embed.set_author(
            name=f"{username}",
            url=namemc_url,
            icon_url=head_url
        )
        
        # Nastavení velkého obrázku hlavy hráče
        embed.set_image(url=large_head_url)
        
        # Přidání textu pod hlavu
        embed.add_field(name=f"`{username}`'s head:", value=f"`{give_command}`", inline=False)
        
        # Přidání profilového obrázku bota
        embed.set_thumbnail(url=interaction.client.user.avatar.url)
        
        # Odeslání zprávy s embedem
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(
            f"Uživatel s nickem `{username}` nebyl nalezen. Zkontroluj, zda je správně napsaný.",
            ephemeral=True
        )


# server info
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="mcserver", description="Získej informace o Minecraft serveru.")
async def mcserver(interaction: discord.Interaction, ip: str):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.mcstatus.io/v2/status/java/{ip}") as response:
            if response.status == 200:
                data = await response.json()
                if data.get("online", False):
                    embed = discord.Embed(
                        title=f"🌍 Info o Minecraft serveru",
                        description=f"`{ip}` je **online** 🎉",
                        color=discord.Color.from_rgb(227, 159, 215)
                    )

                    # MOTD
                    motd_raw = data.get("motd", {}).get("clean", [])
                    if isinstance(motd_raw, list):
                        motd_clean = " ".join(motd_raw).strip()
                    else:
                        motd_clean = str(motd_raw).strip()
                    if not motd_clean:
                        motd_clean = "*Žádný popis*"

                    # Hráči
                    players = data.get("players", {})
                    online = players.get("online", 0)
                    max_players = players.get("max", 0)

                    # Verze
                    version_data = data.get("version", {})
                    version_name = version_data.get("name_clean", "Neznámá")
                    version_protocol = version_data.get("protocol", "N/A")

                    # IP a port
                    ip_address = data.get("ip_address", "Neznámá")
                    port = data.get("port", "Neznámý")

                    embed.add_field(
                        name="📝 MOTD (popis serveru)",
                        value=f"> {motd_clean}",
                        inline=False
                    )
                    embed.add_field(
                        name="👥 Hráči online",
                        value=f"> **{online}** / {max_players}",
                        inline=True
                    )
                    embed.add_field(
                        name="📦 Verze serveru",
                        value=f"> {version_name}\n> *(Protokol: {version_protocol})*",
                        inline=True
                    )
                    embed.add_field(
                        name="🌐 IP adresa & port",
                        value=f"> `{ip_address}:{port}`",
                        inline=False
                    )

                    embed.set_thumbnail(url=f"https://api.mcstatus.io/v2/icon/{ip}")

                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(f"❌ Server `{ip}` je offline.", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Server `{ip}` nebyl nalezen (HTTP {response.status}).", ephemeral=True)


#player info
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="mcplayerinfo", description="Získej informace o Minecraft hráči.")
async def mcplayerinfo(interaction: discord.Interaction, username: str):
    await interaction.response.defer()  # Indikuje, že bot zpracovává požadavek
    async with aiohttp.ClientSession() as session:
        # Získání UUID hráče
        async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{username}") as response:
            if response.status == 200:
                profile = await response.json()
                uuid = profile['id']

                # Vytvoření odkazu ke stažení skinu
                skin_url = f"https://api.mineatar.io/skin/{uuid}"
                
                # Embed zpráva
                embed = discord.Embed(
                    title=f"Minecraft profil pro {username}",
                    color=discord.Color.from_rgb(227, 159, 215)
                )
                embed.add_field(name="UUID", value=uuid, inline=False)
                embed.add_field(
                    name="Textury",
                    value=f"[Stáhnout Skin]({skin_url})",
                    inline=False
                )
                # Nastavení obrázku hráče do pravého rohu
                embed.set_thumbnail(url=f"https://api.mineatar.io/body/full/{uuid}?scale=16")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"Hráč `{username}` nebyl nalezen.", ephemeral=True)
                
# Příkaz /achievement
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="achievement", description="Create a Minecraft achievement image.")
async def achievement(interaction: discord.Interaction, item: str, text1: str, text2: str):
    # Použijeme ITEM_IDS místo AchievementItems
    item_id = ITEM_IDS.get(item.title())  # Používáme item.title() pro správné formátování názvu
    if item_id:
        # Zakódujeme texty pro URL-safe formát
        text1_encoded = urllib.parse.quote(text1)
        text2_encoded = urllib.parse.quote(text2)
        
        achievement_url = f"https://skinmc.net/achievement/{item_id}/{text1_encoded}/{text2_encoded}"
        
        # Embed zpráva s obrázkem pod titulkem
        embed = discord.Embed(
            title="Minecraft Achievement",
            color=discord.Color.from_rgb(227, 159, 215)
        )
        
        # Nastavení obrázku achievement přímo pod titulek
        embed.set_image(url=achievement_url)
        
        # Přidání profilové fotky bota vpravo (horní roh)
        embed.set_thumbnail(url=interaction.client.user.avatar.url)

        # Odeslání zprávy s embedem
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(
            f"Neplatný item `{item}`. Zkontroluj, že je správně napsaný.",
            ephemeral=True
        )

# Autocomplete pro item
@achievement.autocomplete("item")
async def achievement_item_autocomplete(interaction: discord.Interaction, current: str):
    matching_items = [
        discord.app_commands.Choice(name=item, value=item)
        for item in ITEM_IDS.keys()
        if current.lower() in item.lower()
    ]
    
    # Zajištění maximálně 25 položek, které se zobrazí
    return matching_items[:25]

# Příkaz pro zobrazení obrázku Minecraft itemu
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="item", description="Get an image of a Minecraft item/block.")
async def item(interaction: discord.Interaction, name: str):
    try:
        # Vytvoření URL pro Minecraft item obrázek
        image_url = f"https://static.minecraftitemids.com/128/{name.lower()}.png"
        
        # Vytvoření embed zprávy
        embed = discord.Embed(
            title=f"Image of {name}",
            color=discord.Color.from_rgb(227, 159, 215)
        )
        embed.set_image(url=image_url)
        embed.set_thumbnail(url=interaction.client.user.avatar.url)

        # Odeslání zprávy s obrázkem
        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(
            content=f"An error occurred: {e}",
            ephemeral=True
        )
# Příkaz /mctotem
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="mctotem", description="Minecraft totem for the player.")
async def mctotem(interaction: discord.Interaction, username: str):
    totem_url = f"https://skinmc.net/api/v1/renders/skins/{username}/totem"
    
    embed = discord.Embed(
        title=f"{username}'s Minecraft Totem",
        description=f"Here is the totem for **{username}**.",
        color=discord.Color.from_rgb(227, 159, 215)
    )
    
    # Zvětšení obrázku totemu
    embed.set_image(url=totem_url + "?size=300")  # Parametr pro zvětšení obrázku (například pro velikost 3x)
    embed.set_thumbnail(url=interaction.client.user.avatar.url)
    # Odeslání embed zprávy
    await interaction.response.send_message(embed=embed)

# Příkaz /mcbust
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="mcbust", description="Get a Minecraft bust image of the player.")
async def mcbust(interaction: discord.Interaction, username: str):
    bust_url = f"https://minotar.net/armor/bust/{username}/500.png"
    
    # Embed zpráva pro zobrazení bustu
    embed = discord.Embed(
        title=f"{username}'s Bust",
        color=discord.Color.from_rgb(227, 159, 215)
    )
    embed.set_image(url=bust_url)
    embed.set_thumbnail(url=interaction.client.user.avatar.url)
    # Odeslání embed zprávy
    await interaction.response.send_message(embed=embed)

# Příkaz /mchelm
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.command(name="mchelm", description="Get a Minecraft helm image of the player.")
async def mchelm(interaction: discord.Interaction, username: str):
    helm_url = f"https://minotar.net/helm/{username}/600.png"
    
    # Embed zpráva pro zobrazení helmu
    embed = discord.Embed(
        title=f"{username}'s Helmet",
        color=discord.Color.from_rgb(227, 159, 215)
    )
    embed.set_image(url=helm_url)
    embed.set_thumbnail(url=interaction.client.user.avatar.url)
    # Odeslání embed zprávy
    await interaction.response.send_message(embed=embed)

# Funkce pro registraci příkazů
def setup_minecraft_commands(bot):
    bot.tree.add_command(mcplayerinfo)
    bot.tree.add_command(mcserver)
    bot.tree.add_command(achievement)
    bot.tree.add_command(mchead)
    bot.tree.add_command(item)
    bot.tree.add_command(mctotem)
    bot.tree.add_command(mcbust)
    bot.tree.add_command(mchelm)

