async def setup_kulhon_commands(bot):
    await bot.load_extension("kulhon.job")
    await bot.load_extension("kulhon.raid")
    await bot.load_extension("kulhon.shop")
    await bot.load_extension("kulhon.coinflip")
    await bot.load_extension("kulhon.game_info")
    await bot.load_extension("kulhon.admin")