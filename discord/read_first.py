from database.core import create_user
import disnake
from disnake import Embed, ui
from disnake.ext import commands
import asyncio
from configs.read_first_config import messages
import logging

log = logging.getLogger(__name__)

async def get_webhook(channel, webhook_name):
    webhooks = await channel.webhooks()
    for webhook in webhooks:
        if webhook.name == webhook_name:
            return webhook
    return None

class LanguageSelect(ui.Select):
    def __init__(self, roles_config):
        self.roles_config = roles_config
        options = [
            disnake.SelectOption(
                label=opt["label"],
                description=opt["description"],
                emoji=opt["emoji"],
                value=opt["value"]
            ) for opt in messages["language_options"]
        ]
        super().__init__(
            custom_id="language_select",
            placeholder=messages["select_placeholder"],
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: disnake.MessageInteraction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        member = interaction.author

        ru_role = guild.get_role(self.roles_config["language_roles"]["russian"])
        en_role = guild.get_role(self.roles_config["language_roles"]["english"])
        both_role = guild.get_role(self.roles_config["language_roles"]["bilingual"])

        try:
            create_user(str(member.id))
            for role in [ru_role, en_role, both_role]:
                if role and role in member.roles:
                    await member.remove_roles(role)

            response_message = ""
            if self.values[0] == "russian" and ru_role:
                await member.add_roles(ru_role)
                response_message = messages["responses"]["russian"]
            elif self.values[0] == "english" and en_role:
                await member.add_roles(en_role)
                response_message = messages["responses"]["english"]
            elif self.values[0] == "bilingual" and both_role:
                await member.add_roles(both_role)
                response_message = messages["responses"]["bilingual"]

            await interaction.followup.send(response_message, ephemeral=True)

        except disnake.Forbidden:
            await interaction.followup.send(
                messages["responses"]["forbidden"],
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                messages["responses"]["error"].format(error=str(e)),
                ephemeral=True
            )

class LanguageView(ui.View):
    def __init__(self, roles_config):
        super().__init__(timeout=None)
        self.roles_config = roles_config
        self.add_item(LanguageSelect(roles_config))

async def setup_read_first(bot: commands.Bot, guild_id: int, channels_config: dict, roles_config: dict):
    guild = bot.get_guild(guild_id)
    if not guild:
        return

    view = LanguageView(roles_config)
    bot.add_view(view)

    channel_data = channels_config["channels"].get("❗│read-first")
    if not channel_data:
        return

    channel_id = channel_data["id"]
    webhook_config = channel_data.get("webhook", {})
    webhook_name = webhook_config.get("name")

    channel = guild.get_channel(channel_id)
    if not channel:
        return

    async for message in channel.history(limit=None):
        if not message.author.bot:
            try:
                await message.delete()
                await asyncio.sleep(0.3)
            except Exception:
                pass

    has_welcome_message = False
    async for message in channel.history(limit=100):
        is_bot_author = message.author == bot.user
        is_webhook_author = isinstance(message.author,
                                    disnake.User) and message.author.display_name == webhook_config.get("name",
                                                                                                    "Omnicorp Bot")

        if is_bot_author or is_webhook_author:
            if message.embeds:
                for embed in message.embeds:
                    if embed.title and ("Добро пожаловать" in embed.title or "Welcome" in embed.title):
                        has_welcome_message = True
                        break
        if has_welcome_message:
            break

    if has_welcome_message:
        return

    try:
        webhook = await get_webhook(channel, webhook_name)
        if not webhook:
            log.error(f"Webhook '{webhook_name}' not found in #{channel.name}")
            return

        embed = Embed(
            title=messages["welcome"]["title"],
            description=messages["welcome"]["description"],
            color=getattr(disnake.Color, messages["welcome"]["color"])()
        )

        if "banner" in webhook_config and webhook_config["banner"]:
            embed.set_image(url=webhook_config["banner"])

        embed.set_footer(text=messages["welcome"]["footer"])

        await webhook.send(embed=embed, view=LanguageView(roles_config))
    except Exception as e:
        log.error(f"Error sending welcome message: {e}")