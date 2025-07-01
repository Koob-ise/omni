import disnake
from disnake import ui, Embed
import io
import logging
from .config import config
from database.db import create_ticket

log = logging.getLogger(__name__)


class ConfirmCloseModal(ui.Modal):
    def __init__(self, channel, opener, ticket_data, lang="en"):
        texts = {
            "en": {
                "title": "Confirm Closure",
                "label": "Confirmation",
                "placeholder": "Type 'yes' to confirm",
                "hint": "❗ Please type 'yes' to confirm closure",
                "success": "✅ Ticket closed successfully",
                "error": "❌ Invalid confirmation"
            },
            "ru": {
                "title": "Подтверждение закрытия",
                "label": "Подтверждение",
                "placeholder": "Введите 'да' для подтверждения",
                "hint": "❗ Введите 'да' для подтверждения",
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

            # Отправляем лог и получаем ссылку на сообщение
            message_link = await self._send_log_and_get_link(modal_interaction, embed, transcript)

            if message_link:
                try:
                    # Сохраняем ссылку в БД как ID тикета
                    create_ticket(str(self.opener.id), message_link)
                    log.info(f"Ticket saved for {self.opener.id}: {message_link}")
                except Exception as e:
                    log.error(f"Error saving ticket to DB: {e}")
                    await modal_interaction.followup.send(
                        f"⚠️ {'Ошибка сохранения тикета' if self.lang == 'ru' else 'Ticket save error'}",
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
                    f"❌ {'Ошибка удаления канала' if self.lang == 'ru' else 'Channel deletion error'}",
                    ephemeral=True
                )

        except Exception as e:
            log.error(f"Critical error in modal window: {e}")
            await modal_interaction.followup.send(
                f"❌ {'Критическая ошибка' if self.lang == 'ru' else 'Critical error'}",
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

    async def _send_log_and_get_link(self, interaction, embed, transcript_text):
        """Отправляет лог и возвращает ссылку на сообщение"""
        try:
            channels_config = config.channels
            closed_channel_id = channels_config["channels"].get("📌│closed-tickets", {}).get("id")
            if not closed_channel_id:
                log.warning("Closed tickets channel not configured")
                return None

            closed_channel = interaction.guild.get_channel(closed_channel_id)
            if not closed_channel:
                log.error(f"Closed tickets channel not found: {closed_channel_id}")
                return None

            transcript_file = disnake.File(
                io.BytesIO(transcript_text.encode('utf-8-sig')),
                filename=f"transcript_{self.channel.name}.txt"
            )

            # Отправляем сообщение и сразу получаем его объект
            log_message = await closed_channel.send(embed=embed, file=transcript_file)
            return log_message.jump_url

        except Exception as e:
            log.error(f"Log sending error: {e}")
            return None