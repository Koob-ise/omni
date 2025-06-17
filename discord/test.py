import disnake
def test(bot):
    @bot.slash_command(name="test")
    async def test(inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message('нормально все')