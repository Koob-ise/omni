import disnake
from disnake.ext import commands
import toml
import os
import json
from read_first import setup_read_first
from push import setup_slash_commands
from test import test

config_path = os.path.join(os.path.dirname(__file__), "../configs/config.toml")
channels_path = os.path.join(os.path.dirname(__file__), "../configs/channels_config.json")
roles_path = os.path.join(os.path.dirname(__file__), "../configs/roles_config.json")

config = toml.load(config_path)
with open(channels_path, "r", encoding="utf-8") as f:
    channels_config = json.load(f)
with open(roles_path, "r", encoding="utf-8") as f:
    roles_config = json.load(f)

bot = commands.Bot(
    command_prefix=config["bot"]["prefix"],
    activity=disnake.Game(config["bot"]["activity"]),
    intents=disnake.Intents.all(),
    test_guilds=[config["server"]["id"]]
)

setup_slash_commands(bot,channels_config)
test(bot)

@bot.event
async def on_ready():
    channel_data = channels_config["channels"]["❗│read-first"]
    await setup_read_first(
        bot=bot,
        guild_id=config["server"]["id"],
        channel_id=channel_data["id"],
        webhook_config=channel_data.get("webhook", {}),
        roles_config=roles_config
    )

if __name__ == "__main__":
    bot.run(config["bot"]["DISCORD_BOT_TOKEN"])