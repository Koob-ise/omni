import disnake
from disnake import ui, Embed
import io
import logging
from .config import global_channels_config
from .utils import generate_transcript

log = logging.getLogger(__name__)

class ConfirmCloseModal(ui.Modal):
    def __init__(self, channel, opener, ticket_data, channels_config, lang="en"):
        texts = {
            "en": {
                "title": "Confirm Closure",
                "label": "Confirmation",
                "placeholder": "Type 'yes' to confirm",
                "success": "✅ Ticket closed successfully",
                "error": "❌ Invalid confirmation"
            },
            "ru": {
                "title": "Подтверждение закрытия",
                "label": "Подтверждение",
                "placeholder": "Введите 'да' для подтверждения",
                "success": "✅ Тикет успешно закрыт",
                "error": "❌ Неверное подтверждение"
            }
        }

        self.lang = lang
        self.texts = texts.get(lang, texts["en"])
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
        self.channels_config = channels_config

    async def callback(self, modal_interaction):
        try:
            await modal_interaction.response.defer(ephemeral=True)
            user_input = modal_interaction.text_values["confirm"].lower()
            if not (user_input == "yes" or (self.lang == "ru" and user_input == "да")):
                await modal_interaction.followup.send(self.texts["error"], ephemeral=True)
                return

            closed_by = modal_interaction.user
            transcript = await generate_transcript(self.channel)
            embed = self._create_embed(closed_by)

            await self._send_log(modal_interaction, embed, transcript)
            await modal_interaction.followup.send(self.texts["success"], ephemeral=True)

            try:
                await self.channel.delete()
            except disnake.NotFound:
                pass
            except Exception as e:
                log.error(f"Channel deletion error: {e}")
                await modal_interaction.followup.send(
                    f"❌ {'Ошибка удаления канала' if self.lang == 'ru' else 'Channel deletion error'}",
                    ephemeral=True
                )

        except Exception as e:
            log.error(f"Critical error in modal window: {e}")
            await modal_interaction.followup.send(
                f"❌ {'Критическая ошибка' if self.lang == 'ru' else 'Critical error'}",
                ephemeral=True
            )

    def _create_embed(self, closed_by):
        embed = Embed(
            title=f"Closed ticket: {self.ticket_data['title']}",
            color=disnake.Color.red(),
            timestamp=disnake.utils.utcnow()
        )
        embed.add_field(name="Type", value=self.ticket_data['type'], inline=True)
        embed.add_field(name="Platform", value=self.ticket_data['platform'], inline=True)
        embed.add_field(name="Opened by", value=self.opener.mention, inline=True)
        embed.add_field(name="Closed by", value=closed_by.mention, inline=True)

        for field_name, field_value in self.ticket_data['content'].items():
            embed.add_field(
                name=field_name,
                value=field_value[:1000] + "..." if len(field_value) > 1000 else field_value,
                inline=False
            )
        return embed

    async def _send_log(self, interaction, embed, transcript_text):
        closed_channels = self.channels_config.get("channels", {})
        closed_channel_info = closed_channels.get("📌│closed-tickets", {})

        if not closed_channel_info:
            return

        closed_channel_id = closed_channel_info.get("id")
        if not closed_channel_id:
            return

        try:
            closed_channel = interaction.guild.get_channel(closed_channel_id)
            if closed_channel:
                transcript_file = disnake.File(
                    io.BytesIO(transcript_text.encode('utf-8-sig')),
                    filename=f"transcript_{self.channel.name}.txt"
                )
                await closed_channel.send(embed=embed, file=transcript_file)
        except Exception as e:
            log.error(f"Log sending error: {e}")