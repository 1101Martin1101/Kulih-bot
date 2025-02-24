import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import json
from discord.ui import Modal, TextInput, Select, View
from config import BASIC_COLORS  # Importujeme BASIC_COLORS z config.py
from discord.ext.commands import Context
from io import BytesIO
import io
from PIL import Image


# Povolení práce v přímých zprávách
async def dm_or_guild_check(interaction: discord.Interaction):
    if not interaction.guild:
        print(f"Command used in DM by {interaction.user}.")
    return True

class JSONInputModal(Modal):
    def __init__(self, user: discord.User, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    # Define the input field for the JSON
    json_input = TextInput(
        label="Zadejte JSON pro embed", 
        style=discord.TextStyle.long, 
        placeholder="Například: {\"title\": \"Test Title\", \"description\": \"Test Description\", \"color\": 16711680}",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        json_data = self.json_input.value
        try:
            data = json.loads(json_data)
            embed_data = data.get("embeds", [{}])[0]
            embed = discord.Embed(
                title=embed_data.get("title"),
                description=embed_data.get("description"),
                url=embed_data.get("url"),
                color=embed_data.get("color", discord.Color.default())  # Default color if not specified
            )

            author = embed_data.get("author")
            if author:
                embed.set_author(name=author.get("name"), url=author.get("url"), icon_url=author.get("icon_url"))

            footer = embed_data.get("footer")
            if footer:
                embed.set_footer(text=footer.get("text"), icon_url=footer.get("icon_url"))

            timestamp = embed_data.get("timestamp")
            if timestamp:
                embed.timestamp = discord.utils.parse_time(timestamp)

            image = embed_data.get("image")
            if image:
                embed.set_image(url=image.get("url"))
            
            thumbnail = embed_data.get("thumbnail")
            if thumbnail:
                embed.set_thumbnail(url=thumbnail.get("url"))

            fields = embed_data.get("fields", [])
            for field in fields:
                embed.add_field(name=field.get("name"), value=field.get("value"), inline=False)

            # Poslání zprávy před embedem
            await interaction.channel.send("📢 **Zpráva před Embedem:** Tento embed byl vytvořen z JSONu.")  # Přidání zprávy
            await interaction.channel.send(embed=embed)
            await interaction.response.send_message("✅ Embed vytvořen z JSONu!", ephemeral=True)
        except json.JSONDecodeError:
            await interaction.response.send_message("❌ **Chyba:** Neplatný JSON formát. Ujistěte se, že formát je správný.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ **Chyba:** {str(e)}", ephemeral=True)

# Command for /embed with JSON toggle
@app_commands.command(name="embed", description="Vytvoří přizpůsobený embed na základě zadaných hodnot nebo JSON.")
@app_commands.check(dm_or_guild_check)
async def embed_command(
    interaction: discord.Interaction,
    json: Optional[bool] = False,  # JSON toggle
    author: Optional[str] = None,
    author_url: Optional[str] = None,
    author_icon_url: Optional[str] = None,
    title: Optional[str] = None,
    title_url: Optional[str] = None,  # Přidán nový parametr title_url
    description: Optional[str] = None,
    description_url: Optional[str] = None,
    color: Optional[str] = None,  # Barva
    field_name_1: Optional[str] = None, field_value_1: Optional[str] = None,
    field_name_2: Optional[str] = None, field_value_2: Optional[str] = None,
    image_url_1: Optional[str] = None,
    image_url_2: Optional[str] = None,
    image_url_3: Optional[str] = None,
    image_url_4: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    footer: Optional[str] = None,
    footer_icon_url: Optional[str] = None,
    timestamp: Optional[bool] = False,
    message: Optional[str] = None  # Parametr pro zprávu před embedem
):
    if json:
        # Trigger the modal for JSON input
        modal = JSONInputModal(
            user=interaction.user,
            title="Zadejte JSON pro Embed",
            custom_id="embed_json_modal"
        )
        await interaction.response.send_modal(modal)
        return

    # Pokud je message parametr vyplněn, pošleme zprávu před embedem
    if message and not title:
        # Pokud je zadána jen zpráva (a ne title), pošleme pouze text
        # Povolit zmínky pro @everyone
        await interaction.response.send_message(message, allowed_mentions=discord.AllowedMentions(everyone=True))
        return

    # Pokud není vyplněno title, vytvoříme embed bez něj
    embed_color = discord.Color.default()  # Výchozí barva

    if color:
        if color.capitalize() in BASIC_COLORS:
            embed_color = discord.Color(int(BASIC_COLORS[color.capitalize()].strip("#"), 16))
        else:
            try:
                embed_color = discord.Color(int(color.strip("#"), 16))
            except ValueError:
                await interaction.followup.send("\u26a0\ufe0f **Chyba:** Neplatný HEX kód barvy.", ephemeral=True)
                return

    # Pokud není vyplněno title, můžeme použít výchozí hodnoty
    embed = discord.Embed(
        title=title if title else "Embed bez title",  # Pokud není title, nastavíme výchozí text
        description=f"[{description}]({description_url})" if description and description_url else description,
        color=embed_color
    )

    # Pokud je title_url, nastavíme title jako klikací odkaz
    if title_url:
        embed.title = f"[{title}]({title_url})" if title else "Embed bez title"

    # Nastavení autora
    if author:
        embed.set_author(name=author, url=author_url, icon_url=author_icon_url)

    # Přidání fields
    if field_name_1 and field_value_1:
        embed.add_field(name=field_name_1, value=field_value_1, inline=False)
    if field_name_2 and field_value_2:
        embed.add_field(name=field_name_2, value=field_value_2, inline=False)

    # Nastavení thumbnail
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    # Nastavení obrázků
    if image_url_1:
        embed.set_image(url=image_url_1)
    elif image_url_2:
        embed.set_image(url=image_url_2)
    elif image_url_3:
        embed.set_image(url=image_url_3)
    elif image_url_4:
        embed.set_image(url=image_url_4)

    # Nastavení patičky (footer)
    if footer:
        embed.set_footer(text=footer, icon_url=footer_icon_url)

    # Přidání časového razítka
    if timestamp:
        embed.timestamp = discord.utils.utcnow()

    # Odeslání zprávy a embedu v jedné zprávě (pokud je message a title)
    if message:
        await interaction.response.send_message(content=message, embed=embed, allowed_mentions=discord.AllowedMentions(everyone=True))
    else:
        # Pokud není message, jen embed
        await interaction.response.send_message(embed=embed)


@discord.app_commands.command(name="clear", description="Clear messages from a user or total messages.")
@app_commands.describe(count="Number of messages to clear", user="User to clear messages from (optional)")
async def clear_command(interaction: discord.Interaction, count: int, user: Optional[discord.User] = None):
    # Ensure the count is within valid range (maximum 100 messages)
    if count < 1 or count > 100:
        await interaction.response.send_message("Please specify a count between 1 and 100.", ephemeral=True)
        return

    try:
        # Check if the bot is in the guild and has the necessary permission to delete messages
        if interaction.guild is None or interaction.guild.me is None:
            await interaction.response.send_message("I am not in this server or cannot find my user details.", ephemeral=True)
            return

        if not interaction.guild.me.guild_permissions.manage_messages:
            await interaction.response.send_message("I don't have permission to manage messages in this channel.", ephemeral=True)
            return

        # Check if the user has the necessary permission to use the command
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You don't have permission to clear messages.", ephemeral=True)
            return

        # Acknowledge the interaction to avoid timeout
        await interaction.response.defer()

        # Get the channel where the command was invoked
        channel = interaction.channel

        # If a user is specified, delete their messages
        if user:
            # Fetch the last 'count' messages
            messages = [msg async for msg in channel.history(limit=200)]
            user_messages = [msg for msg in messages if msg.author == user]

            # Delete the specified number of messages from the user
            for msg in user_messages[:count]:
                await msg.delete()

            await interaction.followup.send(f"Deleted {len(user_messages[:count])} messages from {user.mention}.", ephemeral=True)

        # If no user is specified, delete the total number of messages
        else:
            # Delete the last 'count' messages
            deleted_messages = await channel.purge(limit=count)
            await interaction.followup.send(f"Deleted {len(deleted_messages)} messages.", ephemeral=True)

    except discord.errors.NotFound:
        # Handle the case where the message context is lost
        await interaction.followup.send("The message context was lost. Please try again.", ephemeral=True)

    except Exception as e:
        # Catch any other errors and display them
        await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)



# Funkce pro nastavení příkazů
def setup_mod_commands(bot):
    bot.tree.add_command(embed_command)
    bot.tree.add_command(clear_command)