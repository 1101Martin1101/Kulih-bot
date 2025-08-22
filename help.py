import discord
from discord.ui import View, Button, Select
from discord.ext import commands

MAX_FIELDS = 24

async def help_command(interaction: discord.Interaction):
    categories = [
        ("ℹ️ Základní info a utility", [
            ("🏓 /info", "Zobrazí latenci bota a systémové informace."),
            ("👤 /userinfo", "Zobrazí informace o uživateli."),
            ("🏰 /serverinfo", "Zobrazí informace o serveru."),
            ("📚 /help", "Zobrazí tuto nápovědu."),
        ]),
        ("🛡️ Moderace", [
            ("🧹 /clear", "Smaže zprávy v kanálu (dle oprávnění)."),
            ("🧹 /vymaz", "Smaže více kanálů s názvem closed-<číslo> (dle oprávnění)."),
            ("🔇 /mute", "Ztlumí uživatele (permanentně, prodlužováno po 7 dnech)."),
            ("⏳ /tempmute", "Dočasně ztlumí uživatele na zadaný čas (max 7 dní)."),
            ("🔊 /unmute", "Odebere ztlumení uživateli."),
            ("🚫 /ban", "Zabanuje uživatele na serveru."),
            ("⏳ /tempban", "Dočasně zabanovat uživatele na zadaný čas."),
            ("♻️ /unban", "Odbanuje uživatele podle ID."),
            ("👢 /kick", "Vykopne uživatele ze serveru."),
            ("⚠️ /warn", "Upozorní uživatele (uloží varování do DB)."),
            ("🗑️ /unwarn", "Smaže poslední varování uživatele."),
            ("📋 /warnlist", "Zobrazí všechny warny uživatele."),
        ]),
        ("🌟 Reputace", [
            ("🌟 /rep", "Dej reputaci uživateli (1-10 hvězd)."),
            ("📋 /replist", "Zobrazí detailní seznam reputací pro člena."),
            ("🏆 /reptop", "Zobrazí top členy podle reputace."),
            ("🗑️ /repdel", "Smaže reputaci podle ID (autor nebo admin)."),
            ("ℹ️ /rephelp", "Nápověda k rep systému."),
        ]),
        ("💰 Ekonomika a minihry", [
            ("🛒 /shop", "Obchod s boosty, upgrady a lektvary."),
            ("💼 /job", "Vykonej job pro Kulhony a XP."),
            ("⚔️ /raid", "Zaútoč na hráče a získej odměny."),
            ("🏆 /leaderboard", "Zobrazí žebříček nejlepších hráčů."),
            ("📊 /player-info", "Zobrazí statistiku hráče."),
            ("ℹ️ /game-info", "Nápověda a užitečné příkazy ke hře."),
            ("🪙 /coinflip", "Sázej na hod mincí."),
            ("🎲 /shellgame", "Skořápky – hádej pod kterou je výhra."),
            ("🎰 /slotmachine", "Zatoč automatem o Kulhony."),
            ("🎲 /diceduel", "Souboj kostek s botem."),
        ]),
        ("⛏️ Minecraft", [
            ("🧑‍🎤 /mcplayerinfo", "Získej informace o Minecraft hráči."),
            ("🌍 /mcserver", "Získej informace o Minecraft serveru."),
            ("🪖 /mchead", "Zobraz hlavu Minecraft hráče."),
            ("🏅 /achievement", "Vytvoř Minecraft achievement obrázek."),
            ("📦 /item", "Zobraz obrázek Minecraft itemu/bloku."),
            ("🪙 /mctotem", "Minecraft totem pro hráče."),
            ("🦸 /mcbust", "Minecraft bust obrázek hráče."),
            ("⛑️ /mchelm", "Minecraft helm obrázek hráče."),
        ]),
        ("🎉 Zábava a obrázky", [
            ("🐶 /pet", "Petpet gif pro uživatele na základě jejich avataru."),
            ("🎴 /welcome_card", "Vytvoří uvítací kartu pro uživatele."),
            ("🎬 /meme", "Zobrazí náhodný meme obrázek."),
            ("🎱 /8ball", "Položte otázku a dostanete odpověď od magické koule."),
            ("🌦️ /weather", "Zobrazí aktuální počasí."),
            ("🚨 /alert", "Vytvoří upozornění s textem."),
            ("🔲 /blur", "Aplikuje blur efekt na avatar uživatele."),
            ("🔲 /invert", "Aplikuje inverzní barvy na avatar uživatele."),
            ("⚫ /greyscale", "Aplikuje šedotónový efekt na avatar uživatele."),
            ("🤡 /clown", "Aplikuje clown efekt na avatar uživatele."),
            ("🚔 /jail", "Aplikuje jail efekt na avatar uživatele."),
            ("🏞️ /wanted", "Vytvoří wanted poster s avatarem uživatele."),
            ("🎨 /colorify", "Přidá specifikovanou barvu na avatar uživatele."),
            ("📱 /nokia", "Přidá efekt Nokia na avatar uživatele."),
            ("☭ /communism", "Přidá efekt komunismu na avatar uživatele."),
            ("⚠️ /caution", "Přidá efekt opatrnosti k textu."),
            ("🔤 /encode", "Zakóduje zadaný text."),
            ("🖥️ /decode", "Dekóduje zadaný binární řetězec."),
            ("📡 /texttomorse", "Převádí text na morseovku."),
            ("🔁 /reverse", "Otočí zadaný text."),
            ("🎮 /doublestruck", "Převádí text na písmo typu doublestruck."),
            ("🌐 /translate", "Přeloží zadaný text do specifikovaného jazyka."),
            ("💎 /nitro", "Generuje fake Nitro kód."),
            ("🌈 /gayrate", "Provádí gay test a generuje procento."),
            ("👑 /simprate", "Provádí simp test a generuje procento."),
            ("🧠 /iq", "Generuje IQ test a ukáže náhodně vygenerované IQ."),
            ("💯 /sigmarate", "Generuje sigma procento."),
            ("🎤 /skibidirate", "Generuje skibidi procento."),
            ("👊 /pesti_dostanes", "Uživatel dostane pěsti."),
        ]),
        #("🔞 NSFW", [
        #    ("🔞 /startgen", "Začne generovat NSFW obrázky (jen s rolí nsfw)."),
        #    ("⏹️ /stopgen", "Zastaví generování NSFW obrázků."),
        #]),
        #("🛠️ Admin a speciální", [
        #    ("🛠️ /admin", "Univerzální admin příkaz pro správu hráčů."),
        #    ("👑 /kulihadmin", "Vytvoří admin roli a přidělí ji (pouze Kulih)."),
        #]),
    ]

    # Rozdělení kategorií na více embedů pokud mají víc než 25 příkazů
    embed_pages = []
    category_names = []
    for cat_name, cmds in categories:
        category_names.append(cat_name)
        for i in range(0, len(cmds), MAX_FIELDS):
            embed = discord.Embed(
                title=f"📚 Help – {cat_name}",
                color=discord.Color.from_rgb(227, 159, 215)
            )
            for name, desc in cmds[i:i+MAX_FIELDS]:
                embed.add_field(name=name, value=desc, inline=False)
            embed.set_thumbnail(url=interaction.client.user.avatar.url)
            embed.add_field(
                name="❓ Pokud máte nějaké otázky, kontaktujte správce.",
                value="[martin1101](https://discord.com/users/771295264153141250)",
                inline=False
            )
            embed_pages.append((cat_name, embed))

    # Mapování: kategorie -> indexy v embed_pages
    cat_to_indexes = {}
    idx = 0
    for cat_name, cmds in categories:
        count = (len(cmds) + MAX_FIELDS - 1) // MAX_FIELDS
        cat_to_indexes[cat_name] = list(range(idx, idx+count))
        idx += count

    class CategoryView(View):
        def __init__(self, embed_pages, cat_to_indexes, category_names, current_cat=0, current_page=0):
            super().__init__(timeout=120)
            self.embed_pages = embed_pages
            self.cat_to_indexes = cat_to_indexes
            self.category_names = category_names
            self.current_cat = current_cat
            self.current_page = current_page
            self.update_buttons()

        def update_buttons(self):
            cat = self.category_names[self.current_cat]
            indexes = self.cat_to_indexes[cat]
            self.previous_page.disabled = False
            self.next_page.disabled = False

        def get_current_embed(self):
            cat = self.category_names[self.current_cat]
            indexes = self.cat_to_indexes[cat]
            return self.embed_pages[indexes[self.current_page]][1]

        @discord.ui.button(label="⬅️ Předchozí stránka", style=discord.ButtonStyle.red, row=0)
        async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            cat = self.category_names[self.current_cat]
            indexes = self.cat_to_indexes[cat]
            if self.current_page > 0:
                new_view = CategoryView(
                    self.embed_pages, self.cat_to_indexes, self.category_names,
                    current_cat=self.current_cat, current_page=self.current_page - 1
                )
            elif self.current_cat > 0:
                prev_cat = self.current_cat - 1
                prev_indexes = self.cat_to_indexes[self.category_names[prev_cat]]
                new_view = CategoryView(
                    self.embed_pages, self.cat_to_indexes, self.category_names,
                    current_cat=prev_cat, current_page=len(prev_indexes) - 1
                )
            else:
                # Jsme na úplně první stránce první kategorie, zůstaň zde
                new_view = self
            await interaction.response.edit_message(embed=new_view.get_current_embed(), view=new_view)

        @discord.ui.button(label="Další stránka ➡️", style=discord.ButtonStyle.green, row=0)
        async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            cat = self.category_names[self.current_cat]
            indexes = self.cat_to_indexes[cat]
            if self.current_page < len(indexes) - 1:
                new_view = CategoryView(
                    self.embed_pages, self.cat_to_indexes, self.category_names,
                    current_cat=self.current_cat, current_page=self.current_page + 1
                )
            elif self.current_cat < len(self.category_names) - 1:
                next_cat = self.current_cat + 1
                new_view = CategoryView(
                    self.embed_pages, self.cat_to_indexes, self.category_names,
                    current_cat=next_cat, current_page=0
                )
            else:
                # Jsme na úplně poslední stránce poslední kategorie, zůstaň zde
                new_view = self
            await interaction.response.edit_message(embed=new_view.get_current_embed(), view=new_view)

        @discord.ui.select(
            placeholder="Vyber kategorii",
            options=[
                discord.SelectOption(label=cat, value=str(i))
                for i, cat in enumerate([
                    cat for cat, _ in categories
                ])
            ],
            row=1
        )
        async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
            selected = int(select.values[0])
            new_view = CategoryView(
                self.embed_pages, self.cat_to_indexes, self.category_names,
                current_cat=selected, current_page=0
            )
            await interaction.response.edit_message(embed=new_view.get_current_embed(), view=new_view)

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True

    view = CategoryView(embed_pages, cat_to_indexes, category_names)
    await interaction.response.send_message(embed=view.get_current_embed(), view=view)

# Funkce pro registraci příkazu /help
def setup_help_command(bot):
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @bot.tree.command(name="help", description="Zobrazí dostupné příkazy a jejich popis.")
    async def help_command_register(interaction: discord.Interaction):
        await help_command(interaction)
