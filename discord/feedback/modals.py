import disnake
from disnake import ui, Embed
import io
import logging
from configs.feedback_config import config, TEXTS, TICKET_COLORS
from database.db import create_ticket

log = logging.getLogger(__name__)


async def get_webhook(channel, webhook_name):
    webhooks = await channel.webhooks()
    for webhook in webhooks:
        if webhook.name == webhook_name:
            return webhook
    return None


class ConfirmCloseModal(ui.Modal):
    def __init__(self, channel, opener, ticket_data, lang="en"):
        texts = TEXTS[lang]["modals"]["confirm_close"]

        self.lang = lang
        self.texts = texts
        super().__init__(
            title=self.texts["title"],
            custom_id="confirm_close",
            components=[
                ui.TextInput(
                    label=self.texts["label"],
                    placeholder=self.texts["placeholder"],
                    custom_id="confirm",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=3
                )
            ]
        )
        self.channel = channel
        self.opener = opener
        self.ticket_data = ticket_data

    async def callback(self, modal_interaction):
        try:
            await modal_interaction.response.defer(ephemeral=True)
            user_input = modal_interaction.text_values["confirm"].lower()
            if not (user_input == "yes" or (self.lang == "ru" and user_input == "да")):
                await modal_interaction.followup.send(self.texts["error"], ephemeral=True)
                return

            closed_by = modal_interaction.user
            transcript = await self._generate_transcript()
            embed = self._create_embed(closed_by)

            message_link = await self._send_log_and_get_link(modal_interaction, embed, transcript)

            if message_link:
                try:
                    create_ticket(str(self.opener.id), message_link)
                    log.info(f"Ticket saved for {self.opener.id}: {message_link}")
                except Exception as e:
                    log.error(f"Error saving ticket to DB: {e}")
                    await modal_interaction.followup.send(
                        self.texts["db_error"],
                        ephemeral=True
                    )
            else:
                log.warning("Failed to get message link for ticket")

            await modal_interaction.followup.send(self.texts["success"], ephemeral=True)

            try:
                await self.channel.delete()
            except disnake.NotFound:
                pass
            except Exception as e:
                log.error(f"Channel deletion error: {e}")
                await modal_interaction.followup.send(
                    self.texts["delete_error"],
                    ephemeral=True
                )

        except Exception as e:
            log.error(f"Critical error in modal window: {e}")
            await modal_interaction.followup.send(
                self.texts["critical_error"],
                ephemeral=True
            )

    async def _generate_transcript(self):
        transcript = []
        async for message in self.channel.history(limit=200, oldest_first=True):
            content = ""
            if message.content:
                content = message.clean_content.replace('\n', ' ')
            elif message.embeds:
                content = "[Embed]"
            elif message.attachments:
                content = f"[File: {message.attachments[0].filename}]"

            transcript.append(
                f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"{message.author.display_name}: {content}"
            )
        return "\n".join(transcript)

    def _create_embed(self, closed_by):
        texts = TEXTS[self.lang]["modals"]["embed_titles"]
        ticket_type = self.ticket_data['type']

        embed = Embed(
            title=texts["closed_ticket"].format(title=self.ticket_data['title']),
            color=getattr(disnake.Color, TICKET_COLORS[ticket_type])(),
            timestamp=disnake.utils.utcnow()
        )
        embed.add_field(name=texts["type"], value=ticket_type, inline=True)
        embed.add_field(name=texts["platform"], value=self.ticket_data['platform'], inline=True)
        embed.add_field(name=texts["opened_by"], value=self.opener.mention, inline=True)
        embed.add_field(name=texts["closed_by"], value=closed_by.mention, inline=True)

        for field_name, field_value in self.ticket_data['content'].items():
            embed.add_field(
                name=field_name,
                value=field_value[:1000] + "..." if len(field_value) > 1000 else field_value,
                inline=False
            )
        return embed

    async def _send_log_and_get_link(self, interaction, embed, transcript_text):
        try:
            channels_config = config.channels
            closed_channel_config = channels_config["channels"].get("📌│closed-tickets", {})
            closed_channel_id = closed_channel_config.get("id")
            if not closed_channel_config:
                log.warning("Closed tickets channel not configured")
                return None

            closed_channel = interaction.guild.get_channel(closed_channel_id)
            if not closed_channel:
                log.error(f"Closed tickets channel not found: {closed_channel_id}")
                return None

            webhook_config = closed_channel_config.get("webhook", {})
            webhook_name = webhook_config.get("name", "Omnicorp Bot")
            webhook = await get_webhook(closed_channel, webhook_name)

            transcript_file = disnake.File(
                io.BytesIO(transcript_text.encode('utf-8-sig')),
                filename=f"transcript_{self.channel.name}.txt"
            )

            message = await webhook.send(
                embed=embed,
                file=transcript_file,
                wait=True
            )
            return message.id
        except Exception as e:
            log.error(f"Log sending error: {e}")
            return None