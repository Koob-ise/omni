import database
import disnake
from disnake.ext import commands
import configparser

bot = commands.Bot(intents=disnake.Intents.all())


# config = configparser.ConfigParser()
# config.read('config.cfg')
# roles_str = config.get('DEFAULT', 'STAFF_ROLES')
# roles_list = [role.strip() for role in roles_str.split(",")]


@bot.event
async def on_ready():
    print(f"Бот {bot.user} готов к работе!")


'''
@bot.slash_command(
    name="ban",
    description="Добавить бан в базу данных",
    options=[
        disnake.Option(
            name="list_name",
            description="Тип бана: Discord или Mindustry",
            type=disnake.OptionType.string,
            required=True,
            choices=["Discord", "Mindustry"]
        ),
        disnake.Option(
            name="main_user",
            description="Пользователь, которого нужно забанить",
            type=disnake.OptionType.user,
            required=True
        ),
        disnake.Option(
            name="ban_days",
            description="Время бана в днях",
            type=disnake.OptionType.integer,
            required=True
        ),
        disnake.Option(

            name="reason",
            description="Причина бана",
            type=disnake.OptionType.string,
            required=True
        )
    ]
)
async def ban(
    inter: disnake.ApplicationCommandInteraction,
    list_name: str,
    main_user: disnake.User,
    ban_days: int,
    reason: str = 'None'
):
    banned_by = inter.author
    database.add_ban(list_name, str(main_user), str(banned_by), reason, ban_days)
'''
bot.run("MTIzNDUzNzU5NTkzMzgxODg4MQ.GoXSdS.mRgZ6jlMleZOjEhh90s8L6hPZ0mjwLGqKj4y0s")
