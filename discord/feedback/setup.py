import disnake
from disnake import Embed
import asyncio
import time
import logging
from configs.feedback_config import config
from .views import FeedbackView

log = logging.getLogger(__name__)

user_states = {}
last_cleanup = time.time()

async def get_webhook(channel, webhook_name):
    webhooks = await channel.webhooks()
    for webhook in webhooks:
        if webhook.name == webhook_name:
            return webhook
    return None

async def setup_feedback_channel(bot, channels_config, roles_config, guild_id):
    config.init(channels_config, roles_config)

    @bot.listen("on_button_click")
    async def handle_close_button(interaction: disnake.MessageInteraction):
        if interaction.component.custom_id != "persistent_close_ticket":
            return

        channel = interaction.channel
        message = await channel.fetch_message(interaction.message.id)

        if not message.embeds:
            await interaction.response.send_message("❌ Ticket information not found", ephemeral=True)
            return

        embed = message.embeds[0]
        footer_text = embed.footer.text

        if not footer_text:
            await interaction.response.send_message("❌ Metadata not found in ticket", ephemeral=True)
            return

        metadata = {}
        for part in footer_text.split(";"):
            if ":" in part:
                key, value = part.split(":", 1)
                metadata[key] = value

        if "ticket_type" not in metadata or "lang" not in metadata or "opener" not in metadata:
            await interaction.response.send_message("❌ Invalid ticket metadata", ephemeral=True)
            return

        ticket_type = metadata["ticket_type"]
        lang = metadata["lang"]
        opener_id = int(metadata["opener"])

        opener = interaction.guild.get_member(opener_id)
        if not opener:
            try:
                opener = await interaction.guild.fetch_member(opener_id)
            except disnake.NotFound:
                await interaction.response.send_message("❌ Ticket opener not found", ephemeral=True)
                return

        platform_field = next((field for field in embed.fields if field.name in ["Platform", "Платформа"]), None)
        if not platform_field:
            await interaction.response.send_message("❌ Platform information not found", ephemeral=True)
            return
        platform = platform_field.value

        form_data = {}
        for field in embed.fields:
            if field.name not in ["Platform", "Платформа"]:
                form_data[field.name] = field.value

        from .modals import ConfirmCloseModal
        modal = ConfirmCloseModal(
            channel=channel,
            opener=opener,
            ticket_data={
                'title': embed.title,
                'type': ticket_type,
                'platform': platform,
                'content': form_data
            },
            lang=lang
        )
        await interaction.response.send_modal(modal)

    guild = bot.get_guild(guild_id)
    if not guild:
        log.error(f"Сервер с ID {guild_id} не найден")
        return

    ru_key = "⚖│обратная-связь"
    ru_ch_cfg = channels_config["channels"].get(ru_key)
    if ru_ch_cfg:
        ru_channel = guild.get_channel(ru_ch_cfg["id"])
        if ru_channel:
            try:
                await ru_channel.purge(limit=100)
                webhook_name = ru_ch_cfg["webhook"]["name"]
                ru_webhook = await get_webhook(ru_channel, webhook_name)
                ru_embed = Embed(
                    title="Обратная связь",
                    description=(
                        "**1.** Выберите тип обращения: `Жалоба`, `Апелляция` или `Заявка на стафф`\n"
                        "**2.** Выберите платформу: `Mindustry` или `Discord`\n"
                        "**3.** Нажмите кнопку `Заполнить форму`\n\n"
                        "После заполнения формы будет создан приватный канал, доступный только вам и администрации."
                    ),
                    color=disnake.Color.orange(),
                )
                ru_view = FeedbackView(
                    lang="ru",
                    is_russian=True,
                    user_states=user_states,
                    webhook_name=webhook_name,
                    channel_id=ru_channel.id
                )

                if "banner" in channels_config["channels"].get(ru_key).get("webhook", {}) and channels_config["channels"].get(ru_key).get("webhook", {})["banner"]:
                    ru_embed.set_image(url=channels_config["channels"].get(ru_key).get("webhook", {})["banner"])

                ru_message = await ru_webhook.send(embed=ru_embed, view=ru_view, wait=True)
                ru_view.message = ru_message
            except Exception as e:
                log.error(f"Ошибка настройки русского канала: {e}")
        else:
            log.error(f"Русский канал не найден: ID {ru_ch_cfg['id']}")
    else:
        log.error("Конфиг для русского канала не найден")

    en_key = "⚖│feedback"
    en_ch_cfg = channels_config["channels"].get(en_key)
    if en_ch_cfg:
        en_channel = guild.get_channel(en_ch_cfg["id"])
        if en_channel:
            try:
                await en_channel.purge(limit=100)
                webhook_name = en_ch_cfg["webhook"]["name"]
                en_webhook = await get_webhook(en_channel, webhook_name)
                en_embed = Embed(
                    title="Feedback System",
                    description=(
                        "**1.** Select request type: `Complaint`, `Appeal` or `Staff Application`\n"
                        "**2.** Select platform: `Mindustry` or `Discord`\n"
                        "**3.** Click `Fill Form` button\n\n"
                        "After submitting the form, a private channel will be created accessible only to you and staff."
                    ),
                    color=disnake.Color.orange(),
                )
                en_view = FeedbackView(
                    lang="en",
                    is_russian=False,
                    user_states=user_states,
                    webhook_name=webhook_name,
                    channel_id=en_channel.id
                )

                if "banner" in channels_config["channels"].get(en_key).get("webhook", {}) and channels_config["channels"].get(en_key).get("webhook", {})["banner"]:
                    en_embed.set_image(url=channels_config["channels"].get(en_key).get("webhook", {})["banner"])

                en_message = await en_webhook.send(embed=en_embed, view=en_view, wait=True)
                en_view.message = en_message
            except Exception as e:
                log.error(f"Error setting up English feedback: {e}")
        else:
            log.error(f"English feedback channel not found: ID {en_ch_cfg['id']}")
    else:
        log.error("English feedback config not found")

    async def cleanup_task():
        while True:
            await asyncio.sleep(1800)
            current_time = time.time()
            global last_cleanup
            if current_time - last_cleanup > 1800:
                for key in list(user_states.keys()):
                    if current_time - user_states[key].get("timestamp", 0) > 1800:
                        del user_states[key]
                last_cleanup = current_time

    bot.loop.create_task(cleanup_task())