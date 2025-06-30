import disnake
import asyncio
import time
import logging
from .config import user_states, last_cleanup
from .views import FeedbackView

log = logging.getLogger(__name__)


async def setup_feedback_channel(bot, channels_config, roles_config, guild_id):
    @bot.listen("on_button_click")
    async def handle_close_button(interaction: disnake.MessageInteraction):
        if interaction.component.custom_id != "persistent_close_ticket":
            return

        channel = interaction.channel
        try:
            message = await channel.fetch_message(interaction.message.id)
        except disnake.NotFound:
            await interaction.response.send_message("❌ Ticket message not found", ephemeral=True)
            return

        if not message.embeds:
            await interaction.response.send_message("❌ Ticket information not found", ephemeral=True)
            return

        embed = message.embeds[0]
        footer_text = embed.footer.text if embed.footer else ""

        if not footer_text:
            await interaction.response.send_message("❌ Metadata not found in ticket", ephemeral=True)
            return

        metadata = {}
        for part in footer_text.split(";"):
            if ":" in part:
                key, value = part.split(":", 1)
                metadata[key.strip()] = value.strip()

        required_fields = ["ticket_type", "lang", "opener"]
        if not all(field in metadata for field in required_fields):
            await interaction.response.send_message("❌ Invalid ticket metadata", ephemeral=True)
            return

        ticket_type = metadata["ticket_type"]
        lang = metadata["lang"]

        try:
            opener_id = int(metadata["opener"])
        except ValueError:
            await interaction.response.send_message("❌ Invalid opener ID format", ephemeral=True)
            return

        opener = interaction.guild.get_member(opener_id)
        if not opener:
            try:
                opener = await interaction.guild.fetch_member(opener_id)
            except disnake.NotFound:
                await interaction.response.send_message("❌ Ticket opener not found", ephemeral=True)
                return

        platform_field_name = "Платформа" if lang == "ru" else "Platform"
        platform_field = next((field for field in embed.fields if field.name == platform_field_name), None)

        if not platform_field:
            await interaction.response.send_message("❌ Platform information not found", ephemeral=True)
            return

        platform = platform_field.value

        form_data = {}
        for field in embed.fields:
            if field.name != platform_field_name:
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
            channels_config=channels_config,
            lang=lang
        )
        await interaction.response.send_modal(modal)

    guild = bot.get_guild(guild_id)
    if not guild:
        log.error(f"Server with ID {guild_id} not found")
        return

    ru_key = "⚖│обратная-связь"
    en_key = "⚖│feedback"

    if ru_ch_cfg := channels_config.get("channels", {}).get(ru_key):
        if ru_channel := guild.get_channel(ru_ch_cfg["id"]):
            try:
                await ru_channel.purge(limit=100)
                ru_webhook = await ru_channel.create_webhook(
                    name=ru_ch_cfg["webhook"]["name"],
                    avatar=await bot.user.display_avatar.read(),
                )
                ru_embed = disnake.Embed(
                    title="Обратная связь",
                    description=(
                        "**1.** Выберите тип обращения: `Жалоба`, `Апелляция` или `Заявка на стафф`\n"
                        "**2.** Выберите платформу: `Mindustry` или `Discord`\n"
                        "**3.** Нажмите кнопку `Заполнить форму`\n\n"
                        "После заполнения формы будет создан приватный канал, доступный только вам и администрации."
                    ),
                    color=disnake.Color.orange(),
                )
                ru_view = FeedbackView(bot, channels_config, roles_config, lang="ru", is_russian=True)
                await ru_webhook.send(
                    embed=ru_embed,
                    view=ru_view,
                    username=ru_ch_cfg["webhook"]["name"]
                )
                await ru_webhook.delete()
            except Exception as e:
                log.error(f"Russian channel setup error: {e}")
        else:
            log.error(f"Russian channel not found: ID {ru_ch_cfg['id']}")
    else:
        log.error("Russian channel config not found")

    if en_ch_cfg := channels_config.get("channels", {}).get(en_key):
        if en_channel := guild.get_channel(en_ch_cfg["id"]):
            try:
                await en_channel.purge(limit=100)
                en_webhook = await en_channel.create_webhook(
                    name=en_ch_cfg["webhook"]["name"],
                    avatar=await bot.user.display_avatar.read(),
                )
                en_embed = disnake.Embed(
                    title="Feedback System",
                    description=(
                        "**1.** Select request type: `Complaint`, `Appeal` or `Staff Application`\n"
                        "**2.** Select platform: `Mindustry` or `Discord`\n"
                        "**3.** Click `Fill Form` button\n\n"
                        "After submitting the form, a private channel will be created accessible only to you and staff."
                    ),
                    color=disnake.Color.orange(),
                )
                en_view = FeedbackView(bot, channels_config, roles_config, lang="en", is_russian=False)
                await en_webhook.send(
                    embed=en_embed,
                    view=en_view,
                    username=en_ch_cfg["webhook"]["name"]
                )
                await en_webhook.delete()
            except Exception as e:
                log.error(f"English feedback setup error: {e}")
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