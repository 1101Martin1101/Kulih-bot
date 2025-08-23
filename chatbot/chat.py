import discord
from discord.ext import commands
import json
import os
import asyncio
from deep_translator import GoogleTranslator

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
                spoiler_pings = " ".join(f"|{m}" for m in mentions)
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

        content = message.content.lower().strip()
        if content.startswith("kulbot on"):
            self.set_enabled(message.guild.id, True)
            try:
                await message.delete()
            except Exception:
                pass
            try:
                await self.send_status_embed(message.author, message.guild, True)
            except Exception:
                pass
            return
        if content.startswith("kulbot off"):
            self.set_enabled(message.guild.id, False)
            try:
                await message.delete()
            except Exception:
                pass
            try:
                await self.send_status_embed(message.author, message.guild, False)
            except Exception:
                pass
            return

        if not self.is_enabled(message.guild.id):
            return

        # Smaž zprávu a pošli ji do kanálu místo tebe (nejdřív smaž, pak pošli)
        try:
            await message.delete()
        except Exception:
            pass
        files = await safe_attachments_to_files(message.attachments) if message.attachments else None

        if message.reference and message.reference.message_id:
            try:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                if message.content or files:
                    await message.channel.send(
                        message.content if message.content else None,
                        files=files,
                        reference=ref_msg
                    )
            except Exception:
                if message.content or files:
                    await message.channel.send(
                        message.content if message.content else None,
                        files=files
                    )
        else:
            if message.content or files:
                await message.channel.send(
                    message.content if message.content else None,
                    files=files
                )

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