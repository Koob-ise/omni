#main.py
import disnake
from disnake.ext import commands
import toml
import os
import json
from read_first import check_read_first_channel, setup_language_roles

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
    await setup_language_roles(bot)

    # Проверяем/создаем приветственное сообщение
    channel_config = channels_config["channels"]["❗│read-first"]
    await check_read_first_channel(bot, channel_config["id"], channel_config.get("webhook", {}))


if __name__ == "__main__":
    bot.run(config["bot"]["DISCORD_BOT_TOKEN"])