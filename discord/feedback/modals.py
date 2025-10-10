import disnake
from disnake import ui, Embed
import io
import logging
from configs.feedback_config import config, TEXTS, TICKET_COLORS
from database.db import create_ticket

log = logging.getLogger(__name__)


async def get_webhook(channel, webhook_name):
    """Находит вебхук по имени в канале."""
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
        transcript = await self._generate_transcript()
        embed = self._create_embed(closed_by)

        message_link = await self._send_log_and_get_link(interaction, embed, transcript)

        if message_link:
            try:
                create_ticket(str(self.opener.id), message_link)
            except Exception as e:
                await interaction.followup.send(self.texts["db_error"], ephemeral=True)
                return

        try:
            await self.channel.delete(reason=f"Ticket closed by {closed_by.display_name}")
        except disnake.NotFound:
            pass
        except Exception as e:
            log.error(f"Could not delete ticket channel {self.channel.id}: {e}")
            await interaction.followup.send(self.texts["delete_error"], ephemeral=True)
            return

        await interaction.followup.send(self.texts["success"], ephemeral=True)
        self.stop()

    @ui.button(label="Cancel", style=disnake.ButtonStyle.secondary, custom_id="cancel_close")
    async def cancel_button(self, button: ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.edit_message(content=self.texts.get("cancelled", "Ticket closing cancelled"),
                                                view=None)
        self.stop()

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

    async def _send_log_and_get_link(self, interaction, embed, transcript_text):
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

            if not webhook:
                log.warning(f"Webhook for closed tickets not found, sending as bot.")
                message = await closed_channel.send(embed=embed)
                return message.jump_url

            transcript_file = disnake.File(
                io.BytesIO(transcript_text.encode('utf-8-sig')),
                filename=f"transcript_{self.channel.name}.txt"
            )

            message = await webhook.send(
                embed=embed,
                file=transcript_file,
                wait=True
            )
            return message.jump_url
        except Exception as e:
            log.error(f"Log sending error: {e}")
            return None