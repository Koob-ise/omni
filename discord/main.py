#main.py
import disnake
from disnake.ext import commands
import toml
import os
import json
from read_first import check_read_first_channel, setup_language_roles
from information import check_information_channel
from rules import check_rules_channel
from updates import check_updates_channel
from gaming_news import check_gaming_news_channel

# Загрузка конфигов
config_path = os.path.join(os.path.dirname(__file__), "../configs/config.toml")
channels_path = os.path.join(os.path.dirname(__file__), "../configs/channels_config.json")

config = toml.load(config_path)
with open(channels_path, "r", encoding="utf-8") as f:
    channels_config = json.load(f)

bot = commands.Bot(
    command_prefix=config["bot"]["prefix"],
    activity=disnake.Game(config["bot"]["activity"]),
    intents=disnake.Intents.all()
)


@bot.event
async def on_ready():
    print(f"Бот {bot.user} запущен!")
    
    # Настраиваем обработчик выбора языка
    #await setup_language_roles(bot)

    bot.load_extension("cogs.news")

    # Проверяем/создаем приветственное сообщение
    channels = channels_config["channels"]    

    # ❗│read-first
    #await check_read_first_channel(bot, channels["❗│read-first"]["id"], channels["❗│read-first"]["webhook"])

    # 📌│информация
    #await check_information_channel(bot, channels["📌│информация"]["id"], channels["📌│информация"]["webhook"])

    # 📜│правила
    #await check_rules_channel(bot, channels["📜│правила"]["id"], channels["📜│правила"]["webhook"])

    # 🔄│обновления
    #await check_updates_channel(bot, channels["🔄│обновления"]["id"], channels["🔄│обновления"]["webhook"])

    # 🎮│игровые-новости
    #await check_gaming_news_channel(bot, channels["🎮│игровые-новости"]["id"], channels["🎮│игровые-новости"]["webhook"])

if __name__ == "__main__":
    bot.run(config["bot"]["DISCORD_BOT_TOKEN"])