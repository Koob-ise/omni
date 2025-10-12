import disnake
from disnake import ui, Embed
import io
import logging
import aiohttp
from configs.feedback_config import config, TEXTS, TICKET_COLORS
from database.tickets import log_ticket_close

log = logging.getLogger(__name__)


async def get_webhook(channel, webhook_name):
    if not webhook_name: return None
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


class ConfirmCloseModal(ui.View):
    def __init__(self, channel, opener, ticket_data, lang="en"):
        super().__init__(timeout=60)
        self.channel = channel
        self.opener = opener
        self.ticket_data = ticket_data
        self.lang = lang
        self.texts = TEXTS[lang]["modals"]["confirm_close"]
        self.confirmation_text = self.texts.get(
            "confirmation_message",
            "Are you sure you want to close the ticket?" if lang == "en" else "Вы уверены, что хотите закрыть тикет?"
        )

    @ui.button(label="Close", style=disnake.ButtonStyle.danger, custom_id="close_ticket")
    async def close_button(self, button: ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.defer(ephemeral=True)

        closed_by = interaction.user

        transcript, attachments = await self._collect_media_and_generate_transcript()
        embed = self._create_embed(closed_by)

        message_link = await self._send_log_and_get_link(interaction, embed, transcript, attachments)

        if message_link:
            try:
                log_ticket_close(self.channel.id, message_link)
            except Exception as e:
                log.error(f"DB Error on ticket close: {e}")

        await interaction.followup.send(self.texts["success"], ephemeral=True)

        try:
            await self.channel.delete(reason=f"Ticket closed by {closed_by.display_name}")
        except disnake.NotFound:
            pass
        except Exception as e:
            log.error(f"Could not delete ticket channel {self.channel.id}: {e}")
            return

        self.stop()

    @ui.button(label="Cancel", style=disnake.ButtonStyle.secondary, custom_id="cancel_close")
    async def cancel_button(self, button: ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.edit_message(content=self.texts.get("cancelled", "Ticket closing cancelled"),
                                                view=None)
        self.stop()

    async def _collect_media_and_generate_transcript(self):
        transcript_lines = []
        attachments_to_upload = []

        async for message in self.channel.history(limit=None, oldest_first=True):
            content_part = ""
            if message.content:
                content_part = message.clean_content.replace('\n', ' ')
            elif message.embeds:
                embed_title = message.embeds[0].title if message.embeds[0].title else "Embed"
                content_part = f"[{embed_title}]"

            attachment_part = ""
            if message.attachments:
                attachment_descriptions = [f"[Файл: {att.filename} | URL: {att.url}]" for att in message.attachments]
                attachment_part = " ".join(attachment_descriptions)

                for att in message.attachments:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(att.url) as resp:
                                if resp.status == 200:
                                    file_bytes = await resp.read()
                                    attachments_to_upload.append(
                                        disnake.File(io.BytesIO(file_bytes), filename=att.filename)
                                    )
                                else:
                                    log.warning(f"Failed to download attachment {att.url}, status: {resp.status}")
                    except Exception as e:
                        log.error(f"Error processing attachment {att.url}: {e}")

            full_line = f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {message.author.display_name}: {content_part} {attachment_part}".strip()
            transcript_lines.append(full_line)

        return "\n".join(transcript_lines), attachments_to_upload

    def _create_embed(self, closed_by):
        texts = TEXTS[self.lang]["modals"]["embed_titles"]
        ticket_type = self.ticket_data['type']

        embed = Embed(
            title=texts["closed_ticket"].format(title=self.ticket_data['title']),
            color=getattr(disnake.Color, TICKET_COLORS.get(ticket_type, "default"))(),
            timestamp=disnake.utils.utcnow()
        )
        embed.add_field(name=texts["type"], value=ticket_type, inline=True)
        embed.add_field(name=texts["platform"], value=self.ticket_data['platform'], inline=True)
        embed.add_field(name=texts["opened_by"], value=self.opener.mention, inline=True)
        embed.add_field(name=texts["closed_by"], value=closed_by.mention, inline=True)

        for field_name, field_value in self.ticket_data['content'].items():
            if field_name in ["game_nick", "username", "offender_game"]:
                continue
            display_value = field_value if len(field_value) <= 1000 else field_value[:1000] + "..."
            embed.add_field(name=field_name, value=display_value, inline=False)
        return embed

    async def _send_log_and_get_link(self, interaction, embed, transcript_text, attachments):
        try:
            channels_config = config.channels
            closed_channel_config = channels_config["channels"].get("📌│closed-tickets", {})
            closed_channel_id = closed_channel_config.get("id")
            if not closed_channel_id:
                log.warning("Closed tickets channel not configured")
                return None

            closed_channel = interaction.guild.get_channel(closed_channel_id)
            if not closed_channel:
                log.error(f"Closed tickets channel not found: {closed_channel_id}")
                return None

            webhook_config = closed_channel_config.get("webhook", {})
            webhook_name = webhook_config.get("name")
            webhook = await get_webhook(closed_channel, webhook_name)

            transcript_file = disnake.File(
                io.BytesIO(transcript_text.encode('utf-8-sig')),
                filename=f"transcript_{self.channel.name}.txt"
            )

            async def send_message(content=None, embed=None, file=None):
                if webhook:
                    return await webhook.send(content=content, embed=embed, file=file, wait=True)
                else:
                    log.warning(f"Webhook for closed tickets not found, sending as bot.")
                    return await closed_channel.send(content=content, embed=embed, file=file)

            message = await send_message(embed=embed, file=transcript_file)
            if not message:
                log.error("Failed to send the initial log message.")
                return None

            if attachments:
                thread = None
                try:
                    thread_name = f"Медиа-файлы из тикета {self.channel.name}"
                    if len(thread_name) > 100:
                        thread_name = thread_name[:97] + "..."
                    thread = await message.create_thread(name=thread_name)
                except Exception as e:
                    log.error(f"Failed to create thread for attachments on message {message.id}: {e}")

                if thread:
                    log.info(f"Created thread '{thread.name}' for {len(attachments)} attachments.")
                    for attachment_file in attachments:
                        try:
                            attachment_file.fp.seek(0)
                            await thread.send(file=attachment_file)
                        except disnake.HTTPException as e:
                            if e.status == 413:
                                log.error(
                                    f"Failed to send attachment {attachment_file.filename} to thread {thread.id}: File is too large (over 25MB).")
                            else:
                                log.error(
                                    f"Failed to send attachment {attachment_file.filename} to thread {thread.id}: {e}")
                        except Exception as e:
                            log.error(
                                f"An unexpected error occurred while sending attachment {attachment_file.filename} to thread {thread.id}: {e}")

            return message.jump_url
        except Exception as e:
            log.error(f"Log sending error: {e}")
            return None