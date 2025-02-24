import discord
from discord.ui import View, Button
from discord.ext import commands

async def help_command(interaction: discord.Interaction):
    # Seznam příkazů
    commands_list = [
        ("🏓 /info", "Zobrazí latenci bota a systémové informace."),
        ("👊 /pesti_dostanes", "Uživatel dostane pěsti."),
        ("🔞 /startgen", "Začne generovat obrázky na základě zadaného typu a intervalu."),
        ("⏹️ /stopgen", "Zastaví generování obrázků."),
        ("👤 /userinfo", "Zobrazí informace o členovy."),
        ("🏰 /serverinfo", "Zobrazí informace o serveru."),
        ("🐶 /pet", "Petpet gif pro uživatele na základě jejich avataru."),
        ("🎴 /welcome_card", "Vytvoří uvítací kartu pro uživatele."),
        ("🌦️ /weather", "Zobrazí aktuální počasí."),
        ("🎬 /meme", "Zobrazí náhodný meme obrázek."),
        ("🚨 /alert", "Vytvoří upozornění s textem."),
        ("🎱 /8ball", "Položte otázku a dostanete odpověď od magické koule."),
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
        ("🧹 /clear", "Smaže zprávy, pokud máš oprávnění."),
        ("📊 /embed", "Generuje embed zprávu."),
    ]

    # Funkce pro vytvoření embed stránky
    def create_embed(page_number, commands):
        embed = discord.Embed(
            title="📚 **Help**",
            description=f"**🔧 /help**\nDostupné příkazy pro bota - Stránka {page_number}",
            color=discord.Color.from_rgb(227, 159, 215)
        )
        for name, value in commands:
            embed.add_field(name=name, value=value, inline=False)

        embed.set_thumbnail(url=interaction.client.user.avatar.url)
        embed.add_field(
            name="❓ Pokud máte nějaké otázky, kontaktujte správce.",
            value="[martin1101](https://discord.com/users/771295264153141250)",
            inline=False
        )
        return embed

    # Počet příkazů na stránce
    commands_per_page = 5
    total_pages = (len(commands_list) + commands_per_page - 1) // commands_per_page

    # Funkce pro vytvoření tlačítek pro stránkování
    class PaginationButtons(View):
        def __init__(self, total_pages):
            super().__init__(timeout=60)
            self.current_page = 1
            self.total_pages = total_pages

            # Přiřadit správné počáteční stavy tlačítek
            self.update_buttons()

        def update_buttons(self):
            self.children[0].disabled = self.current_page == 1  # Deaktivovat "Předchozí" na první stránce
            self.children[1].disabled = self.current_page == self.total_pages  # Deaktivovat "Další" na poslední stránce

        @discord.ui.button(label="Předchozí", style=discord.ButtonStyle.red, disabled=True)
        async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page > 1:
                self.current_page -= 1
                commands_to_show = commands_list[
                    (self.current_page - 1) * commands_per_page:self.current_page * commands_per_page
                ]
                embed = create_embed(self.current_page, commands_to_show)
                self.update_buttons()
                await interaction.response.edit_message(embed=embed, view=self)

        @discord.ui.button(label="Další", style=discord.ButtonStyle.green)
        async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page < self.total_pages:
                self.current_page += 1
                commands_to_show = commands_list[
                    (self.current_page - 1) * commands_per_page:self.current_page * commands_per_page
                ]
                embed = create_embed(self.current_page, commands_to_show)
                self.update_buttons()
                await interaction.response.edit_message(embed=embed, view=self)

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True

    # Odeslání zprávy
    commands_to_show = commands_list[:commands_per_page]
    embed = create_embed(1, commands_to_show)
    view = PaginationButtons(total_pages)
    await interaction.response.send_message(embed=embed, view=view)

# Funkce pro registraci příkazu /help
def setup_help_command(bot):
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @bot.tree.command(name="help", description="Zobrazí dostupné příkazy a jejich popis.")
    async def help_command_register(interaction: discord.Interaction):
        await help_command(interaction)
