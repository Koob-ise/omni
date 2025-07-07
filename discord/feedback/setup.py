import disnake
from disnake import Embed
import asyncio
import time
import logging
from configs.feedback_config import config, TEXTS
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
            texts = TEXTS.get("ru", TEXTS["en"])["setup"]["errors"]
            await interaction.response.send_message(texts["ticket_info"], ephemeral=True)
            return

        embed = message.embeds[0]
        footer_text = embed.footer.text

        if not footer_text:
            texts = TEXTS.get("ru", TEXTS["en"])["setup"]["errors"]
            await interaction.response.send_message(texts["metadata"], ephemeral=True)
            return

        metadata = {}
        for part in footer_text.split(";"):
            if ":" in part:
                key, value = part.split(":", 1)
                metadata[key] = value

        if "ticket_type" not in metadata or "lang" not in metadata or "opener" not in metadata:
            texts = TEXTS.get("ru", TEXTS["en"])["setup"]["errors"]
            await interaction.response.send_message(texts["invalid_metadata"], ephemeral=True)
            return

        ticket_type = metadata["ticket_type"]
        lang = metadata["lang"]
        opener_id = int(metadata["opener"])

        opener = interaction.guild.get_member(opener_id)
        if not opener:
            try:
                opener = await interaction.guild.fetch_member(opener_id)
            except disnake.NotFound:
                texts = TEXTS.get("ru", TEXTS["en"])["setup"]["errors"]
                await interaction.response.send_message(texts["opener"], ephemeral=True)
                return

        platform_field = next((field for field in embed.fields if field.name in ["Platform", "Платформа"]), None)
        if not platform_field:
            texts = TEXTS.get("ru", TEXTS["en"])["setup"]["errors"]
            await interaction.response.send_message(texts["platform"], ephemeral=True)
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

    async def setup_channel(ch_key, lang, is_russian):
        ch_cfg = channels_config["channels"].get(ch_key)
        if not ch_cfg:
            log.error(f"Конфиг для канала {ch_key} не найден")
            return

        channel = guild.get_channel(ch_cfg["id"])
        if not channel:
            log.error(f"Канал не найден: ID {ch_cfg['id']}")
            return

        webhook_name = ch_cfg["webhook"]["name"]
        webhook = await get_webhook(channel, webhook_name)
        if not webhook:
            try:
                webhook = await channel.create_webhook(name=webhook_name)
                log.info(f"Создан новый вебхук: {webhook_name}")
            except Exception as e:
                log.error(f"Ошибка создания вебхука: {e}")
                return

        existing_message = None
        async for message in channel.history(limit=100):
            if message.author.id == webhook.id and message.embeds:
                existing_message = message
                break

        texts = TEXTS[lang]["setup"]["feedback"]
        embed = Embed(
            title=texts["title"],
            description=texts["description"],
            color=disnake.Color.orange(),
        )

        if "banner" in ch_cfg.get("webhook", {}) and ch_cfg["webhook"]["banner"]:
            embed.set_image(url=ch_cfg["webhook"]["banner"])

        view = FeedbackView(
            lang=lang,
            is_russian=is_russian,
            user_states=user_states,
            webhook_name=webhook_name,
            channel_id=channel.id
        )

        if existing_message:
            try:
                await webhook.edit_message(
                    existing_message.id,
                    embed=embed,
                    view=view
                )
                log.info(f"Сообщение в канале {channel.name} обновлено")
                view.message = existing_message
            except Exception as e:
                log.error(f"Ошибка обновления сообщения: {e}")
        else:
            try:
                message = await webhook.send(
                    embed=embed,
                    view=view,
                    wait=True
                )
                view.message = message
                log.info(f"Отправлено новое сообщение в канал {channel.name}")
            except Exception as e:
                log.error(f"Ошибка отправки сообщения: {e}")

        if view.message:
            bot.add_view(view, message_id=view.message.id)

    await setup_channel("⚖│обратная-связь", "ru", True)
    await setup_channel("⚖│feedback", "en", False)

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