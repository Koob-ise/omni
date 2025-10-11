import disnake
from disnake import Embed
import asyncio
import time
import logging
import re
from configs.feedback_config import config, TEXTS, TICKET_COLORS
from .views import FeedbackView
from .modals import ConfirmCloseModal
from .moderation.helpers import find_offender_in_ticket

log = logging.getLogger(__name__)

user_states = {}
last_cleanup = time.time()


async def get_webhook(channel, webhook_name):
    try:
        webhooks = await channel.webhooks()
        for webhook in webhooks:
            if webhook.name == webhook_name:
                return webhook
    except disnake.Forbidden:
        log.error(f"No permissions to get webhooks in {channel.name}")
    except Exception as e:
        log.error(f"Error getting webhooks in {channel.name}: {e}")
    return None


def has_close_permission(member, permission_key, roles_config):
    for role in member.roles:
        role_id = role.id
        for role_data in roles_config.get("staff_roles", {}).values():
            if role_data.get("id") == role_id and role_data.get("permissions"):
                permissions = [p.strip() for p in role_data["permissions"].split(",")]
                if permission_key in permissions:
                    return True
    return False


async def setup_feedback_channel(bot, channels_config, roles_config, guild_id):
    config.init(channels_config, roles_config)

    @bot.listen("on_button_click")
    async def handle_close_button(interaction: disnake.MessageInteraction):
        if interaction.component.custom_id != "persistent_close_ticket":
            return

        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel

        offender_tag, metadata = await find_offender_in_ticket(channel)

        texts_en = TEXTS["en"]["setup"]["errors"]
        texts_ru = TEXTS["ru"]["setup"]["errors"]

        if not metadata:
            await interaction.followup.send(texts_ru.get("invalid_metadata", texts_en["invalid_metadata"]),
                                            ephemeral=True)
            return

        ticket_type = metadata.get("ticket_type")
        lang = metadata.get("lang")
        opener_id_str = metadata.get("opener")

        if not all([ticket_type, lang, opener_id_str]):
            await interaction.followup.send(texts_ru.get("invalid_metadata", texts_en["invalid_metadata"]),
                                            ephemeral=True)
            return

        opener_id = int(opener_id_str)
        texts = TEXTS.get(lang, TEXTS["en"])

        message = await channel.fetch_message(interaction.message.id)
        if not message.embeds:
            await interaction.followup.send(texts_ru.get("ticket_info", texts_en["ticket_info"]), ephemeral=True)
            return
        embed = message.embeds[0]

        platform_field = next((field for field in embed.fields if field.name in ["Platform", "Платформа"]), None)
        if not platform_field:
            await interaction.followup.send(texts["setup"]["errors"]["platform"], ephemeral=True)
            return
        platform = platform_field.value.lower()

        is_opener = interaction.author.id == opener_id
        permission_key = f"{platform.capitalize()}-{ticket_type}"
        has_perm = has_close_permission(interaction.author, permission_key, roles_config)

        if not is_opener and not has_perm:
            await interaction.followup.send(texts["setup"]["errors"]["close_permission"], ephemeral=True)
            return

        if ticket_type == "Complaint" and has_perm and offender_tag:
            clean_tag = re.sub(r'[<@!>]', '', offender_tag).strip()
            offender = None
            try:
                offender_id = int(clean_tag)
                offender = await interaction.guild.fetch_member(offender_id)
            except (ValueError, disnake.NotFound):
                offender = interaction.guild.get_member_named(clean_tag)

            if offender and offender.id == interaction.author.id:
                await interaction.followup.send(texts["setup"]["errors"]["offender_cannot_close"], ephemeral=True)
                return

        opener = interaction.guild.get_member(opener_id)
        if not opener:
            try:
                opener = await interaction.guild.fetch_member(opener_id)
            except disnake.NotFound:
                await interaction.followup.send(texts["setup"]["errors"]["opener"], ephemeral=True)
                return

        form_data = {}
        for field in embed.fields:
            if field.name not in ["Platform", "Платформа"]:
                form_data[field.name] = field.value

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
        await interaction.followup.send(content=modal.confirmation_text, view=modal, ephemeral=True)

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

        webhook_cfg = ch_cfg.get("webhook", {})
        webhook_name = webhook_cfg.get("name")
        webhook_avatar_path = webhook_cfg.get("avatar")

        if not webhook_name:
            log.error(f"Имя вебхука не указано для канала {ch_key}")
            return

        webhook = await get_webhook(channel, webhook_name)
        if not webhook:
            try:
                avatar_bytes = None
                if webhook_avatar_path:
                    try:
                        with open(webhook_avatar_path, "rb") as f:
                            avatar_bytes = f.read()
                    except FileNotFoundError:
                        log.warning(f"Файл аватара для вебхука {webhook_name} не найден: {webhook_avatar_path}")

                webhook = await channel.create_webhook(name=webhook_name, avatar=avatar_bytes)
                log.info(f"Создан новый вебхук: {webhook_name}")
            except Exception as e:
                log.error(f"Ошибка создания вебхука: {e}")
                return

        existing_message = None
        async for message in channel.history(limit=100):
            if message.author.id == webhook.id and message.embeds:
                existing_message = message
                break

        color_name = TICKET_COLORS.get("feedback", "orange")
        color = getattr(disnake.Color, color_name, disnake.Color.orange)()

        texts = TEXTS[lang]["setup"]["feedback"]
        embed = Embed(
            title=texts["title"],
            description=texts["description"],
            color=color,
        )

        banner_file = None
        banner_path = webhook_cfg.get("banner")
        if banner_path:
            try:
                banner_file = disnake.File(banner_path, filename=banner_path.split('/')[-1])
                embed.set_image(url=f"attachment://{banner_file.filename}")
            except FileNotFoundError:
                log.warning(f"Файл баннера не найден: {banner_path}")
                banner_file = None
                banner_path = None

        view = FeedbackView(
            lang=lang,
            is_russian=is_russian,
            user_states=user_states,
            webhook_name=webhook_name,
            channel_id=channel.id,
            banner_path = banner_path
        )

        files_to_send = [banner_file] if banner_file else []

        if existing_message:
            try:
                await webhook.edit_message(
                    existing_message.id,
                    embed=embed,
                    view=view,
                    files=files_to_send
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
                    files=files_to_send,
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