import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import timedelta, datetime, timezone
import os
import json
import re
from discord.ui import Modal, TextInput, Select, View
from config import BASIC_COLORS

ALLOWED_MOD_ROLES = [
    994372956836864041,
    1391414756405018696,
    # ...další ID podle potřeby
]
PROTECTED_ROLES = [111111111111111111, 994372956836864041]

def has_mod_role():
    async def predicate(interaction: discord.Interaction):
        if not interaction.guild:
            print("Příkaz není na serveru.")
            return False
        try:
            member = interaction.guild.get_member(interaction.user.id)
            if not member:
                member = await interaction.guild.fetch_member(interaction.user.id)
            user_roles = [role.id for role in member.roles]
            print(f"Kontroluji role uživatele {interaction.user}: {user_roles}")
            print(f"Povolené role: {ALLOWED_MOD_ROLES}")
            return any(role_id in user_roles for role_id in ALLOWED_MOD_ROLES)
        except Exception as e:
            print(f"Chyba při kontrole rolí: {e}")
            return False
    return app_commands.check(predicate)

def is_protected(member: discord.Member):
    return any(role.id in PROTECTED_ROLES for role in member.roles)

def get_guild_db_path(guild_id):
    folder = "db/mod"
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{guild_id}.json")

def log_punishment(guild_id, user_id, action, moderator_id, reason, duration=None, until_iso=None):
    path = get_guild_db_path(guild_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"punishments": []}
    entry = {
        "user_id": user_id,
        "action": action,
        "moderator_id": moderator_id,
        "reason": reason,
        "duration": duration,
        "until": until_iso,
        "timestamp": datetime.utcnow().isoformat()
    }
    data["punishments"].append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_active_bans(guild_id):
    path = get_guild_db_path(guild_id)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    bans = []
    for entry in data.get("punishments", []):
        if entry["action"] == "Ban":
            bans.append(str(entry["user_id"]))
        elif entry["action"] == "TempBan" and entry.get("until"):
            until = datetime.fromisoformat(entry["until"])
            if datetime.utcnow() < until:
                bans.append(str(entry["user_id"]))
    return bans

def parse_time(timestr: str) -> timedelta:
    regex = r"(?:(\d+)M)?(?:(\d+)t)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    match = re.fullmatch(regex, timestr)
    if not match:
        raise ValueError("Neplatný formát času. Použij např. 1M2t1d3h55m10s nebo 5d nebo 1h30m.")
    months, weeks, days, hours, minutes, seconds = (int(x) if x else 0 for x in match.groups())
    total_days = months * 30 + weeks * 7 + days
    return timedelta(days=total_days, hours=hours, minutes=minutes, seconds=seconds)

# --- LOGOVACÍ EMBED ---
async def send_punish_embed(interaction, user, action, reason, duration=None):
    embed = discord.Embed(
        title="🚨 Moderátorský zásah",
        color=discord.Color.red() if action in ["Mute", "TempMute", "Ban", "TempBan"] else discord.Color.green()
    )
    embed.add_field(name="Uživatel", value=f"{user.mention} ({user.id})", inline=True)
    embed.add_field(name="Akce", value=action, inline=True)
    if duration:
        embed.add_field(name="Doba", value=duration, inline=True)
    embed.add_field(name="Moderátor", value=f"{interaction.user.mention}", inline=True)
    embed.add_field(name="Důvod", value=reason or "Neuveden", inline=False)
    embed.timestamp = discord.utils.utcnow()
    await interaction.channel.send(embed=embed)

async def send_pm(user, text):
    try:
        await user.send(text)
    except Exception:
        pass

# --- MODERACE ---
@discord.app_commands.command(name="mute", description="Ztlumí uživatele (permanentně, dokud nebude unmute).")
@has_mod_role()
@app_commands.describe(user="Uživatel k ztlumení", reason="Důvod (volitelné)")
async def mute_command(interaction: discord.Interaction, user: discord.Member, reason: Optional[str] = None):
    if is_protected(user):
        await interaction.response.send_message("❌ Tento uživatel má chráněnou roli a nelze ho ztlumit.", ephemeral=True)
        return
    try:
        # Nastav timeout na maximum (7 dní)
        until = datetime.now(timezone.utc) + timedelta(days=7)
        await user.timeout(until, reason=reason or f"Muted by {interaction.user}")
        await send_pm(user, f"Byl jsi ztlumen na serveru **{interaction.guild.name}** (permanentně, prodlužováno každých 7 dní).\nDůvod: {reason or 'Neuveden'}")
        await interaction.response.send_message(f"✅ {user.mention} byl ztlumen (timeout na 7 dní, bude prodlužováno).", ephemeral=True)
        await send_punish_embed(interaction, user, "Mute", reason)
        log_punishment(interaction.guild.id, user.id, "Mute", interaction.user.id, reason)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

@discord.app_commands.command(name="unmute", description="Odebere ztlumení uživateli (timeout).")
@has_mod_role()
@app_commands.describe(user="Uživatel k odtlumení")
async def unmute_command(interaction: discord.Interaction, user: discord.Member):
    if is_protected(user):
        await interaction.response.send_message("❌ Tento uživatel má chráněnou roli a nelze ho odtlumit.", ephemeral=True)
        return
    try:
        await user.timeout(None, reason=f"Unmuted by {interaction.user}")
        remove_punishment(interaction.guild.id, user.id, "Mute")  # Smaže mute z DB
        await send_pm(user, f"Byl jsi odtlumen na serveru **{interaction.guild.name}**.")
        await interaction.response.send_message(f"✅ {user.mention} byl odtlumen (timeout zrušen).", ephemeral=True)
        await send_punish_embed(interaction, user, "Unmute", None)
        log_punishment(interaction.guild.id, user.id, "Unmute", interaction.user.id, None)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

@discord.app_commands.command(name="tempmute", description="Dočasně ztlumí uživatele na zadaný čas (timeout).")
@has_mod_role()
@app_commands.describe(user="Uživatel k ztlumení", time="Doba např. 1d2h, 5m, 1M2t1d3h55m10s", reason="Důvod (volitelné)")
async def tempmute_command(interaction: discord.Interaction, user: discord.Member, time: str, reason: Optional[str] = None):
    if is_protected(user):
        await interaction.response.send_message("❌ Tento uživatel má chráněnou roli a nelze ho ztlumit.", ephemeral=True)
        return
    try:
        delta = parse_time(time)
        until = datetime.now(timezone.utc) + delta
        until_iso = (datetime.utcnow() + delta).isoformat()
        await user.timeout(until, reason=reason or f"Tempmuted by {interaction.user}")
        await send_pm(user, f"Byl jsi dočasně ztlumen na serveru **{interaction.guild.name}** na {time}.\nDůvod: {reason or 'Neuveden'}")
        await interaction.response.send_message(f"✅ {user.mention} byl ztlumen na {time} (timeout).", ephemeral=True)
        await send_punish_embed(interaction, user, "TempMute", reason, duration=time)
        log_punishment(interaction.guild.id, user.id, "TempMute", interaction.user.id, reason, duration=time, until_iso=until_iso)
    except ValueError as ve:
        await interaction.response.send_message(f"❌ {ve}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

@discord.app_commands.command(name="ban", description="Zabanuje uživatele na serveru.")
@has_mod_role()
@app_commands.describe(user="Uživatel k zabanování", reason="Důvod (volitelné)")
async def ban_command(interaction: discord.Interaction, user: discord.Member, reason: Optional[str] = None):
    if is_protected(user):
        await interaction.response.send_message("❌ Tento uživatel má chráněnou roli a nelze ho zabanovat.", ephemeral=True)
        return
    try:
        await send_pm(user, f"Byl jsi zabanován na serveru **{interaction.guild.name}**.\nDůvod: {reason or 'Neuveden'}")
        await user.ban(reason=reason or f"Banned by {interaction.user}")
        await interaction.response.send_message(f"✅ {user.mention} byl zabanován.", ephemeral=True)
        await send_punish_embed(interaction, user, "Ban", reason)
        log_punishment(interaction.guild.id, user.id, "Ban", interaction.user.id, reason)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

@discord.app_commands.command(name="tempban", description="Dočasně zabanovat uživatele na zadaný čas.")
@has_mod_role()
@app_commands.describe(user="Uživatel k tempbanu", time="Doba např. 1d2h, 5m, 1M2t1d3h55m10s", reason="Důvod (volitelné)")
async def tempban_command(interaction: discord.Interaction, user: discord.Member, time: str, reason: Optional[str] = None):
    if is_protected(user):
        await interaction.response.send_message("❌ Tento uživatel má chráněnou roli a nelze ho zabanovat.", ephemeral=True)
        return
    try:
        delta = parse_time(time)
        until_iso = (datetime.utcnow() + delta).isoformat()
        await send_pm(user, f"Byl jsi dočasně zabanován na serveru **{interaction.guild.name}** na {time}.\nDůvod: {reason or 'Neuveden'}")
        await user.ban(reason=reason or f"Tempbanned by {interaction.user}")
        await interaction.response.send_message(f"✅ {user.mention} byl dočasně zabanován na {time}.", ephemeral=True)
        await send_punish_embed(interaction, user, "TempBan", reason, duration=time)
        log_punishment(interaction.guild.id, user.id, "TempBan", interaction.user.id, reason, duration=time, until_iso=until_iso)
    except ValueError as ve:
        await interaction.response.send_message(f"❌ {ve}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

@discord.app_commands.command(name="kick", description="Vykopne uživatele ze serveru.")
@has_mod_role()
@app_commands.describe(user="Uživatel k vykopnutí", reason="Důvod (volitelné)")
async def kick_command(interaction: discord.Interaction, user: discord.Member, reason: Optional[str] = None):
    if is_protected(user):
        await interaction.response.send_message("❌ Tento uživatel má chráněnou roli a nelze ho vykopnout.", ephemeral=True)
        return
    try:
        await send_pm(user, f"Byl jsi vykopnut ze serveru **{interaction.guild.name}**.\nDůvod: {reason or 'Neuveden'}")
        await user.kick(reason=reason or f"Kicked by {interaction.user}")
        await interaction.response.send_message(f"✅ {user.mention} byl vykopnut.", ephemeral=True)
        await send_punish_embed(interaction, user, "Kick", reason)
        log_punishment(interaction.guild.id, user.id, "Kick", interaction.user.id, reason)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

@discord.app_commands.command(name="unban", description="Odbanuje uživatele podle ID.")
@has_mod_role()
@app_commands.describe(user_id="ID uživatele k odbanování")
async def unban_command(interaction: discord.Interaction, user_id: str):
    try:
        user = await interaction.client.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        remove_punishment(interaction.guild.id, int(user_id), "TempBan")  # Odeber tempban z DB
        await send_pm(user, f"Byl jsi odbanován na serveru **{interaction.guild.name}**.")
        await interaction.response.send_message(f"✅ Uživatel s ID {user_id} byl odbanován.", ephemeral=True)
        await send_punish_embed(interaction, user, "Unban", None)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

# --- BAN ENFORCEMENT ---
async def on_member_join(member):
    bans = get_active_bans(member.guild.id)
    if str(member.id) in bans:
        try:
            await member.send(f"Stále máš aktivní ban na serveru **{member.guild.name}**.")
        except Exception:
            pass
        await member.ban(reason="Pokus o obejití banu (automaticky)")

# --- EMBED GENERÁTOR, CLEAR, VYMAZ (zachováno z tvého původního souboru) ---
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import timedelta, datetime
import os
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
@app_commands.command(name="embed", description="Vytvoří přizpůsobený embed...")
@app_commands.checks.has_permissions(manage_messages=True)
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


@discord.app_commands.command(name="clear", description="Smaže zprávy v kanálu (od uživatele nebo všechny).")
@app_commands.describe(count="Počet zpráv ke smazání (max 100)", user="Uživatel, jehož zprávy se mají smazat (volitelné)")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_command(interaction: discord.Interaction, count: int, user: Optional[discord.User] = None):
    if count < 1 or count > 100:
        await interaction.response.send_message("❌ Počet musí být mezi 1 a 100.", ephemeral=True)
        return

    if not interaction.guild or not interaction.channel:
        await interaction.response.send_message("❌ Tento příkaz lze použít pouze na serveru.", ephemeral=True)
        return

    if not interaction.guild.me.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ Nemám právo mazat zprávy.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    def check(msg):
        return (user is None or msg.author.id == user.id)

    fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
    to_delete = []
    async for msg in interaction.channel.history(limit=200):
        if check(msg) and msg.created_at > fourteen_days_ago:
            to_delete.append(msg)
        if len(to_delete) >= count:
            break

    if not to_delete:
        await interaction.followup.send("❌ Nebyly nalezeny žádné zprávy ke smazání (mladší 14 dní).", ephemeral=True)
        return

    try:
        deleted = await interaction.channel.delete_messages(to_delete)
        text = f"Smazáno {len(to_delete)} zpráv"
        if user:
            text += f" od uživatele {user.mention}"
        await interaction.followup.send(f"✅ {text}.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Chyba při mazání: {e}", ephemeral=True)


@discord.app_commands.command(name="vymaz", description="Smaže určitý počet kanálů s názvem 'closed-<číslo>'")
@app_commands.describe(pocet="Počet kanálů ke smazání (smaže prvních X kanálů s názvem 'closed-<číslo>')")
@app_commands.checks.has_permissions(manage_channels=True)
async def vymaz_command(interaction: discord.Interaction, pocet: int):
    # Kontrola oprávnění - buď Administrator nebo specifická role
    has_permission = False
    
    # ID rolí, které mohou používat tento příkaz
    allowed_role_ids = [1363539560616693912, 994372956836864041]
    
    if interaction.user.guild_permissions.administrator:
        has_permission = True
    else:
        # Kontrola, zda má uživatel některou z povolených rolí
        user_role_ids = [role.id for role in interaction.user.roles]
        if any(role_id in user_role_ids for role_id in allowed_role_ids):
            has_permission = True
    
    if not has_permission:
        await interaction.response.send_message(
            "❌ Nemáš oprávnění použít tento příkaz. Potřebuješ oprávnění **Administrator** nebo specifickou roli.",
            ephemeral=True
        )
        return
    
    # Kontrola, zda je počet v rozumném rozmezí
    if pocet < 1 or pocet > 50:
        await interaction.response.send_message("❌ Počet musí být mezi 1 a 50.", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    # Najdeme všechny kanály s názvem closed-<číslo>
    import re
    closed_pattern = re.compile(r'^closed-\d+$')
    all_closed_channels = []
    
    for channel in interaction.guild.channels:
        if closed_pattern.match(channel.name):
            all_closed_channels.append(channel)
    
    if not all_closed_channels:
        await interaction.followup.send("❌ Nebyly nalezeny žádné kanály s názvem 'closed-<číslo>'.", ephemeral=True)
        return
    
    # Seřadíme kanály podle názvu a vezmeme jen požadovaný počet
    all_closed_channels.sort(key=lambda x: x.name)
    channels_to_delete = all_closed_channels[:pocet]
    
    # Vytvoření potvrzovacího embedu
    embed = discord.Embed(
        title="⚠️ Potvrzení smazání kanálů",
        description=f"Nalezeno **{len(all_closed_channels)}** kanálů celkem.\nBude smazáno prvních **{len(channels_to_delete)}** kanálů:",
        color=discord.Color.orange()
    )
    
    channel_list = "\n".join([f"• {channel.name}" for channel in channels_to_delete[:10]])
    if len(channels_to_delete) > 10:
        channel_list += f"\n• ... a dalších {len(channels_to_delete) - 10} kanálů"
    
    embed.add_field(name="Kanály ke smazání:", value=channel_list, inline=False)
    embed.set_footer(text="Tato akce je nevratná! Máte 60 sekund na rozhodnutí.")
    
    # Vytvoření view s potvrzovacími tlačítky
    view = ConfirmVymazDeletionView(channels_to_delete, interaction.user)
    
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class ConfirmVymazDeletionView(View):
    def __init__(self, channels_to_delete, user):
        super().__init__(timeout=60)
        self.channels_to_delete = channels_to_delete
        self.user = user
    
    @discord.ui.button(label="✅ Potvrdit smazání", style=discord.ButtonStyle.danger)
    async def confirm_deletion(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Pouze osoba, která spustila příkaz, může potvrdit smazání.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        deleted_count = 0
        failed_channels = []
        
        for channel in self.channels_to_delete:
            try:
                await channel.delete(reason=f"Bulk cleanup by {interaction.user} using /vymaz command")
                deleted_count += 1
            except discord.errors.Forbidden:
                failed_channels.append(f"{channel.name} (chybí oprávnění)")
            except discord.errors.NotFound:
                # Kanál už byl smazán
                pass
            except Exception as e:
                failed_channels.append(f"{channel.name} ({str(e)})")
        
        # Vytvoření výsledného embedu
        result_embed = discord.Embed(
            title="🗑️ Výsledek mazání kanálů",
            color=discord.Color.green() if deleted_count > 0 else discord.Color.red()
        )
        
        result_embed.add_field(
            name="✅ Úspešně smazáno",
            value=f"**{deleted_count}** kanálů",
            inline=True
        )
        
        if failed_channels:
            result_embed.add_field(
                name="❌ Chyby při mazání",
                value=f"**{len(failed_channels)}** kanálů\n" + "\n".join(failed_channels[:5]),
                inline=True
            )
            result_embed.color = discord.Color.yellow()
        
        result_embed.set_footer(text=f"Provedeno uživatelem {interaction.user}")
        result_embed.timestamp = discord.utils.utcnow()
        
        # Deaktivace tlačítek
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(embed=result_embed, view=self)
    
    @discord.ui.button(label="❌ Zrušit", style=discord.ButtonStyle.secondary)
    async def cancel_deletion(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Pouze osoba, která spustila příkaz, může zrušit akci.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Akce zrušena",
            description="Žádné kanály nebyly smazány.",
            color=discord.Color.red()
        )
        
        # Deaktivace tlačítek
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        # Deaktivace tlačítek po vypršení času
        for item in self.children:
            item.disabled = True


@embed_command.error
async def embed_error_handler(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message(
            "❌ Nemáš oprávnění použít tento příkaz. Potřebuješ právo **Manage Messages**.",
            ephemeral=True
        )


def has_mod_role():
    async def predicate(interaction: discord.Interaction):
        if not interaction.guild:
            print("Příkaz není na serveru.")
            return False
        try:
            member = interaction.guild.get_member(interaction.user.id)
            if not member:
                member = await interaction.guild.fetch_member(interaction.user.id)
            user_roles = [role.id for role in member.roles]
            print(f"Kontroluji role uživatele {interaction.user}: {user_roles}")
            print(f"Povolené role: {ALLOWED_MOD_ROLES}")
            return any(role_id in user_roles for role_id in ALLOWED_MOD_ROLES)
        except Exception as e:
            print(f"Chyba při kontrole rolí: {e}")
            return False
    return app_commands.check(predicate)

# Cesta k DB pro daný server
def get_guild_db_path(guild_id):
    folder = "db/mod"
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{guild_id}.json")

# Uložení trestu do DB
def log_punishment(guild_id, user_id, action, moderator_id, reason, duration=None):
    path = get_guild_db_path(guild_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"punishments": []}
    entry = {
        "user_id": user_id,
        "action": action,
        "moderator_id": moderator_id,
        "reason": reason,
        "duration": duration,
        "timestamp": datetime.utcnow().isoformat()
    }
    data["punishments"].append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Získání aktivních banů
def get_active_bans(guild_id):
    path = get_guild_db_path(guild_id)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    bans = []
    for entry in data.get("punishments", []):
        if entry["action"] in ["Ban", "TempBan"]:
            # Pokud je tempban, zkontroluj expiraci
            if entry["action"] == "TempBan" and entry["duration"]:
                ban_until = datetime.fromisoformat(entry["duration"])
                if datetime.utcnow() < ban_until:
                    bans.append(entry["user_id"])
            else:
                bans.append(entry["user_id"])
    return bans

# Embed pro logování
async def send_punish_embed(interaction, user, action, reason, duration=None):
    embed = discord.Embed(
        title="🚨 Moderátorský zásah",
        color=discord.Color.red() if action in ["Mute", "TempMute", "Ban", "TempBan"] else discord.Color.green()
    )
    embed.add_field(name="Uživatel", value=f"{user.mention} ({user.id})", inline=True)
    embed.add_field(name="Akce", value=action, inline=True)
    if duration:
        embed.add_field(name="Doba", value=duration, inline=True)
    embed.add_field(name="Moderátor", value=f"{interaction.user.mention}", inline=True)
    embed.add_field(name="Důvod", value=reason or "Neuveden", inline=False)
    embed.timestamp = discord.utils.utcnow()
    await interaction.channel.send(embed=embed)

# PM zpráva uživateli
async def send_pm(user, text):
    try:
        await user.send(text)
    except Exception:
        pass  # uživatel má PM vypnuté

@discord.app_commands.command(name="mute", description="Ztlumí uživatele (permanentně, dokud nebude unmute).")
@has_mod_role()
@app_commands.describe(user="Uživatel k ztlumení", reason="Důvod (volitelné)")
async def mute_command(interaction: discord.Interaction, user: discord.Member, reason: Optional[str] = None):
    if is_protected(user):
        await interaction.response.send_message("❌ Tento uživatel má chráněnou roli a nelze ho ztlumit.", ephemeral=True)
        return
    try:
        # Nastav timeout na maximum (7 dní)
        until = datetime.now(timezone.utc) + timedelta(days=7)
        await user.timeout(until, reason=reason or f"Muted by {interaction.user}")
        await send_pm(user, f"Byl jsi ztlumen na serveru **{interaction.guild.name}** (permanentně, prodlužováno každých 7 dní).\nDůvod: {reason or 'Neuveden'}")
        await interaction.response.send_message(f"✅ {user.mention} byl ztlumen (timeout na 7 dní, bude prodlužováno).", ephemeral=True)
        await send_punish_embed(interaction, user, "Mute", reason)
        log_punishment(interaction.guild.id, user.id, "Mute", interaction.user.id, reason)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

@discord.app_commands.command(name="unmute", description="Odebere ztlumení uživateli (timeout).")
@has_mod_role()
@app_commands.describe(user="Uživatel k odtlumení")
async def unmute_command(interaction: discord.Interaction, user: discord.Member):
    if is_protected(user):
        await interaction.response.send_message("❌ Tento uživatel má chráněnou roli a nelze ho odtlumit.", ephemeral=True)
        return
    try:
        await user.timeout(None, reason=f"Unmuted by {interaction.user}")
        remove_punishment(interaction.guild.id, user.id, "Mute")  # Smaže mute z DB
        await send_pm(user, f"Byl jsi odtlumen na serveru **{interaction.guild.name}**.")
        await interaction.response.send_message(f"✅ {user.mention} byl odtlumen (timeout zrušen).", ephemeral=True)
        await send_punish_embed(interaction, user, "Unmute", None)
        log_punishment(interaction.guild.id, user.id, "Unmute", interaction.user.id, None)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

@discord.app_commands.command(name="tempmute", description="Dočasně ztlumí uživatele na zadaný čas (timeout).")
@has_mod_role()
@app_commands.describe(user="Uživatel k ztlumení", time="Doba např. 1d2h, 5m, 1M2t1d3h55m10s", reason="Důvod (volitelné)")
async def tempmute_command(interaction: discord.Interaction, user: discord.Member, time: str, reason: Optional[str] = None):
    if is_protected(user):
        await interaction.response.send_message("❌ Tento uživatel má chráněnou roli a nelze ho ztlumit.", ephemeral=True)
        return
    try:
        delta = parse_time(time)
        until = datetime.now(timezone.utc) + delta
        until_iso = (datetime.utcnow() + delta).isoformat()
        await user.timeout(until, reason=reason or f"Tempmuted by {interaction.user}")
        await send_pm(user, f"Byl jsi dočasně ztlumen na serveru **{interaction.guild.name}** na {time}.\nDůvod: {reason or 'Neuveden'}")
        await interaction.response.send_message(f"✅ {user.mention} byl ztlumen na {time} (timeout).", ephemeral=True)
        await send_punish_embed(interaction, user, "TempMute", reason, duration=time)
        log_punishment(interaction.guild.id, user.id, "TempMute", interaction.user.id, reason, duration=time, until_iso=until_iso)
    except ValueError as ve:
        await interaction.response.send_message(f"❌ {ve}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

@discord.app_commands.command(name="ban", description="Zabanuje uživatele na serveru.")
@has_mod_role()
@app_commands.describe(user="Uživatel k zabanování", reason="Důvod (volitelné)")
async def ban_command(interaction: discord.Interaction, user: discord.Member, reason: Optional[str] = None):
    if is_protected(user):
        await interaction.response.send_message("❌ Tento uživatel má chráněnou roli a nelze ho zabanovat.", ephemeral=True)
        return
    try:
        await send_pm(user, f"Byl jsi zabanován na serveru **{interaction.guild.name}**.\nDůvod: {reason or 'Neuveden'}")
        await user.ban(reason=reason or f"Banned by {interaction.user}")
        await interaction.response.send_message(f"✅ {user.mention} byl zabanován.", ephemeral=True)
        await send_punish_embed(interaction, user, "Ban", reason)
        log_punishment(interaction.guild.id, user.id, "Ban", interaction.user.id, reason)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

@discord.app_commands.command(name="tempban", description="Dočasně zabanovat uživatele na zadaný čas.")
@has_mod_role()
@app_commands.describe(user="Uživatel k tempbanu", time="Doba např. 1d2h, 5m, 1M2t1d3h55m10s", reason="Důvod (volitelné)")
async def tempban_command(interaction: discord.Interaction, user: discord.Member, time: str, reason: Optional[str] = None):
    if is_protected(user):
        await interaction.response.send_message("❌ Tento uživatel má chráněnou roli a nelze ho zabanovat.", ephemeral=True)
        return
    try:
        delta = parse_time(time)
        until_iso = (datetime.utcnow() + delta).isoformat()
        await send_pm(user, f"Byl jsi dočasně zabanován na serveru **{interaction.guild.name}** na {time}.\nDůvod: {reason or 'Neuveden'}")
        await user.ban(reason=reason or f"Tempbanned by {interaction.user}")
        await interaction.response.send_message(f"✅ {user.mention} byl dočasně zabanován na {time}.", ephemeral=True)
        await send_punish_embed(interaction, user, "TempBan", reason, duration=time)
        log_punishment(interaction.guild.id, user.id, "TempBan", interaction.user.id, reason, duration=time, until_iso=until_iso)
    except ValueError as ve:
        await interaction.response.send_message(f"❌ {ve}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

@discord.app_commands.command(name="kick", description="Vykopne uživatele ze serveru.")
@has_mod_role()
@app_commands.describe(user="Uživatel k vykopnutí", reason="Důvod (volitelné)")
async def kick_command(interaction: discord.Interaction, user: discord.Member, reason: Optional[str] = None):
    if is_protected(user):
        await interaction.response.send_message("❌ Tento uživatel má chráněnou roli a nelze ho vykopnout.", ephemeral=True)
        return
    try:
        await send_pm(user, f"Byl jsi vykopnut ze serveru **{interaction.guild.name}**.\nDůvod: {reason or 'Neuveden'}")
        await user.kick(reason=reason or f"Kicked by {interaction.user}")
        await interaction.response.send_message(f"✅ {user.mention} byl vykopnut.", ephemeral=True)
        await send_punish_embed(interaction, user, "Kick", reason)
        log_punishment(interaction.guild.id, user.id, "Kick", interaction.user.id, reason)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

@discord.app_commands.command(name="unban", description="Odbanuje uživatele podle ID.")
@has_mod_role()
@app_commands.describe(user_id="ID uživatele k odbanování")
async def unban_command(interaction: discord.Interaction, user_id: str):
    try:
        user = await interaction.client.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        remove_punishment(interaction.guild.id, int(user_id), "TempBan")  # Odeber tempban z DB
        await send_pm(user, f"Byl jsi odbanován na serveru **{interaction.guild.name}**.")
        await interaction.response.send_message(f"✅ Uživatel s ID {user_id} byl odbanován.", ephemeral=True)
        await send_punish_embed(interaction, user, "Unban", None)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)

# --- BAN ENFORCEMENT ---
async def on_member_join(member):
    bans = get_active_bans(member.guild.id)
    if str(member.id) in bans:
        try:
            await member.send(f"Stále máš aktivní ban na serveru **{member.guild.name}**.")
        except Exception:
            pass
        await member.ban(reason="Pokus o obejití banu (automaticky)")

@clear_command.error
async def clear_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message(
            "❌ Nemáš oprávnění použít tento příkaz. Potřebuješ právo **Manage Messages**.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ Nastala chyba: {error}",
            ephemeral=True
        )

@discord.app_commands.command(name="warn", description="Upozorní uživatele (uloží varování do DB).")
@has_mod_role()
@app_commands.describe(user="Uživatel k varování", reason="Důvod varování (volitelné)")
async def warn_command(interaction: discord.Interaction, user: discord.Member, reason: Optional[str] = None):
    if is_protected(user):
        await interaction.response.send_message("❌ Tento uživatel má chráněnou roli a nelze ho varovat.", ephemeral=True)
        return
    try:
        await send_pm(user, f"Obdržel jsi varování na serveru **{interaction.guild.name}**.\nDůvod: {reason or 'Neuveden'}")
        await interaction.response.send_message(f"⚠️ {user.mention} byl varován.", ephemeral=True)
        await send_punish_embed(interaction, user, "Warn", reason)
        log_punishment(interaction.guild.id, user.id, "Warn", interaction.user.id, reason)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {e}", ephemeral=True)


@discord.app_commands.command(name="unwarn", description="Smaže poslední varování uživatele.")
@has_mod_role()
@app_commands.describe(user="Uživatel, kterému chceš smazat poslední warn")
async def unwarn_command(interaction: discord.Interaction, user: discord.Member):
    path = get_guild_db_path(interaction.guild.id)
    if not os.path.exists(path):
        await interaction.response.send_message("Tento uživatel nemá žádné varování.", ephemeral=True)
        return
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    warns = [entry for entry in data.get("punishments", []) if entry["action"] == "Warn" and entry["user_id"] == user.id]
    if not warns:
        await interaction.response.send_message(f"{user.mention} nemá žádné varování.", ephemeral=True)
        return
    # Smaž poslední warn
    last_warn = warns[-1]
    data["punishments"].remove(last_warn)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    await interaction.response.send_message(f"✅ Poslední warn pro {user.mention} byl smazán.", ephemeral=True)

@discord.app_commands.command(name="warnlist", description="Zobrazí všechny warny uživatele.")
@has_mod_role()
@app_commands.describe(user="Uživatel, jehož warny chceš vidět")
async def warnlist_command(interaction: discord.Interaction, user: discord.Member):
    path = get_guild_db_path(interaction.guild.id)
    warns = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        warns = [entry for entry in data.get("punishments", []) if entry["action"] == "Warn" and entry["user_id"] == user.id]
    if not warns:
        await interaction.response.send_message(f"{user.mention} nemá žádné varování.", ephemeral=True)
        return
    text = f"{user.mention} má {len(warns)} varování:\n"
    for i, warn in enumerate(warns, 1):
        text += f"{i}. {warn['reason'] or 'Neuveden'} ({warn['timestamp'][:19].replace('T', ' ')})\n"
    await interaction.response.send_message(text, ephemeral=True)

def setup_mod_commands(bot):
    bot.tree.add_command(mute_command)
    bot.tree.add_command(unmute_command)
    bot.tree.add_command(tempmute_command)
    bot.tree.add_command(ban_command)
    bot.tree.add_command(tempban_command)
    bot.tree.add_command(kick_command)
    bot.tree.add_command(unban_command)
    bot.tree.add_command(warn_command)
    bot.tree.add_command(unwarn_command)
    bot.tree.add_command(warnlist_command)
    bot.tree.add_command(embed_command)
    bot.tree.add_command(clear_command)
    bot.tree.add_command(vymaz_command)
    bot.add_listener(on_member_join, "on_member_join")


async def tempban_checker(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        for guild in bot.guilds:
            path = get_guild_db_path(guild.id)
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            changed = False
            for entry in data.get("punishments", []):
                if entry["action"] == "TempBan" and entry.get("until"):
                    until = datetime.fromisoformat(entry["until"])
                    if datetime.utcnow() > until:
                        try:
                            user = await bot.fetch_user(entry["user_id"])
                            await guild.unban(user, reason="Vypršel tempban")
                            changed = True
                        except Exception:
                            pass
            # Odstraň tempban z DB (volitelné, nebo přidej flag "expired")
            if changed:
                data["punishments"] = [
                    e for e in data["punishments"]
                    if not (e["action"] == "TempBan" and e.get("until") and datetime.utcnow() > datetime.fromisoformat(e["until"]))
                ]
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        await asyncio.sleep(60)  # kontrola každou minutu

async def permamute_checker(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        for guild in bot.guilds:
            path = get_guild_db_path(guild.id)
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data.get("punishments", []):
                if entry["action"] == "Mute":
                    try:
                        member = guild.get_member(entry["user_id"])
                        if member and (not member.timed_out_until or member.timed_out_until < datetime.now(timezone.utc)):
                            until = datetime.now(timezone.utc) + timedelta(days=28)
                            await member.timeout(until, reason="Prodloužení permanentního mute")
                    except Exception:
                        pass
        await asyncio.sleep(3600)  # kontrola každou hodinu

def remove_punishment(guild_id, user_id, action):
    path = get_guild_db_path(guild_id)
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["punishments"] = [
        entry for entry in data.get("punishments", [])
        if not (entry["user_id"] == user_id and entry["action"] == action)
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)