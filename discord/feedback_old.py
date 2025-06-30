import disnake
from disnake import ui, TextInputStyle, Embed
import io
import logging
from datetime import datetime
import re
import asyncio
import time

# Logger setup
logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)

# Global config storage
global_channels_config = None
global_roles_config = None

# English configuration
TYPE_OPTIONS = [
    {"label": "Complaint", "value": "complaint", "emoji": "⚠️"},
    {"label": "Appeal", "value": "appeal", "emoji": "📩"},
    {"label": "Staff Application", "value": "staff", "emoji": "🛠️"}
]

PLATFORM_OPTIONS = [
    {"label": "Mindustry", "value": "mindustry", "emoji": "🧱"},
    {"label": "Discord", "value": "discord", "emoji": "💬"}
]

MODAL_CONFIGS = {
    "complaint": {
        "title": "Complaint",
        "inputs": [
            {"label": "Offender's username", "custom_id": "offender", "style": TextInputStyle.short, "max_length": 200},
            {"label": "Rule violation", "custom_id": "rule", "style": TextInputStyle.short, "max_length": 5},
            {"label": "Violation description", "custom_id": "desc", "style": TextInputStyle.paragraph,
             "max_length": 4000}
        ]
    },
    "appeal": {
        "title": "Appeal",
        "inputs": [
            {"label": "Punishment reason", "custom_id": "reason", "style": TextInputStyle.short, "max_length": 500},
            {"label": "Punishment date", "custom_id": "date", "style": TextInputStyle.short, "max_length": 20},
            {"label": "Description", "custom_id": "desc", "style": TextInputStyle.paragraph, "max_length": 4000},
            {"label": "Game username and server", "custom_id": "nick", "style": TextInputStyle.short,
             "condition": lambda platform: platform == "mindustry", "max_length": 300}
        ]
    },
    "staff": {
        "title": "Staff Application",
        "inputs": [
            {"label": "Desired position", "custom_id": "position", "style": TextInputStyle.short, "max_length": 100},
            {"label": "Why you want this position", "custom_id": "why", "style": TextInputStyle.paragraph,
             "max_length": 500},
            {"label": "About yourself", "custom_id": "about", "style": TextInputStyle.paragraph, "max_length": 4000},
            {"label": "Game username", "custom_id": "nick", "style": TextInputStyle.short,
             "condition": lambda platform: platform == "mindustry", "max_length": 200}
        ]
    }
}

# Russian configuration for feedback channel
TYPE_OPTIONS_RU = [
    {"label": "Жалоба", "value": "complaint", "emoji": "⚠️"},
    {"label": "Апелляция", "value": "appeal", "emoji": "📩"},
    {"label": "Заявка на стафф", "value": "staff", "emoji": "🛠️"}
]

PLATFORM_OPTIONS_RU = [
    {"label": "Mindustry", "value": "mindustry", "emoji": "🧱"},
    {"label": "Discord", "value": "discord", "emoji": "💬"}
]

MODAL_CONFIGS_RU = {
    "complaint": {
        "title": "Жалоба",
        "inputs": [
            {"label": "Ник нарушителя", "custom_id": "offender", "style": TextInputStyle.short, "max_length": 200},
            {"label": "Пункт правила", "custom_id": "rule", "style": TextInputStyle.short, "max_length": 5},
            {"label": "Описание нарушения", "custom_id": "desc", "style": TextInputStyle.paragraph, "max_length": 4000}
        ]
    },
    "appeal": {
        "title": "Апелляция",
        "inputs": [
            {"label": "Причина наказания", "custom_id": "reason", "style": TextInputStyle.short, "max_length": 500},
            {"label": "Дата наказания", "custom_id": "date", "style": TextInputStyle.short, "max_length": 20},
            {"label": "Описание", "custom_id": "desc", "style": TextInputStyle.paragraph, "max_length": 4000},
            {"label": "Игровой ник и сервер", "custom_id": "nick", "style": TextInputStyle.short,
             "condition": lambda platform: platform == "mindustry", "max_length": 300}
        ]
    },
    "staff": {
        "title": "Заявка на стафф",
        "inputs": [
            {"label": "Желаемая должность", "custom_id": "position", "style": TextInputStyle.short, "max_length": 100},
            {"label": "Почему вы хотите на должность", "custom_id": "why", "style": TextInputStyle.paragraph,
             "max_length": 500},
            {"label": "О себе", "custom_id": "about", "style": TextInputStyle.paragraph, "max_length": 4000},
            {"label": "Игровой ник", "custom_id": "nick", "style": TextInputStyle.short,
             "condition": lambda platform: platform == "mindustry", "max_length": 200}
        ]
    }
}


class ConfirmCloseModal(ui.Modal):
    def __init__(self, channel, opener, ticket_data, channels_config, lang="en"):
        # Определяем тексты в зависимости от языка
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
        self.texts = texts.get(lang, texts["en"])  # По умолчанию английский

        super().__init__(
            title=self.texts["title"],
            custom_id="confirm_close",
            components=[
                ui.TextInput(
                    label=self.texts["label"],
                    placeholder=self.texts["placeholder"],
                    custom_id="confirm",
                    style=TextInputStyle.short,
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

            # Проверка для обоих языков
            user_input = modal_interaction.text_values["confirm"].lower()
            if not (user_input == "yes" or (self.lang == "ru" and user_input == "да")):
                await modal_interaction.followup.send(self.texts["error"], ephemeral=True)
                return

            closed_by = modal_interaction.user
            transcript = await self._generate_transcript()
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

    async def _generate_transcript(self):
        """Generate conversation history"""
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
        """Create embed with ticket information"""
        embed = Embed(
            title=f"Closed ticket: {self.ticket_data['title']}",
            color=disnake.Color.red(),
            timestamp=disnake.utils.utcnow()
        )
        embed.add_field(name="Type", value=self.ticket_data['type'], inline=True)
        embed.add_field(name="Platform", value=self.ticket_data['platform'], inline=True)
        embed.add_field(name="Opened by", value=self.opener.mention, inline=True)
        embed.add_field(name="Closed by", value=closed_by.mention, inline=True)

        # Add all form fields
        for field_name, field_value in self.ticket_data['content'].items():
            embed.add_field(
                name=field_name,
                value=field_value[:1000] + "..." if len(field_value) > 1000 else field_value,
                inline=False
            )
        return embed

    async def _send_log(self, interaction, embed, transcript_text):
        """Send log to closed tickets channel"""
        closed_channel_id = self.channels_config["channels"].get("📌│closed-tickets", {}).get("id")
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


class CloseTicketView(ui.View):
    def __init__(self, lang="en"):
        super().__init__(timeout=None)
        self.lang = lang

        self.add_item(ui.Button(
            label="Закрыть тикет" if lang == "ru" else "Close Ticket",
            style=disnake.ButtonStyle.red,
            custom_id="persistent_close_ticket"
        ))


# Глобальный словарь для хранения состояний пользователей
user_states = {}
last_cleanup = time.time()


async def create_ticket_channel(interaction, title, platform, roles_config, channels_config, form_data, lang="en"):
    # Create channel
    category_id = next(iter(channels_config["categories"].values()))["id"]
    category = interaction.guild.get_channel(category_id)

    overwrites = {
        interaction.guild.default_role: disnake.PermissionOverwrite(read_messages=False),
        interaction.author: disnake.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    for rdata in roles_config["staff_roles"].values():
        if role := interaction.guild.get_role(rdata["id"]):
            overwrites[role] = disnake.PermissionOverwrite(
                read_messages=True, send_messages=True, manage_messages=True
            )

    channel_name = f"{title.lower()}-{platform}-{interaction.author.display_name}".replace(" ", "-")
    channel = await interaction.guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)

    # Преобразуем тип тикета в value
    if lang == "ru":
        ticket_type = next((opt["value"] for opt in TYPE_OPTIONS_RU if opt["label"] == title), title)
    else:
        ticket_type = next((opt["value"] for opt in TYPE_OPTIONS if opt["label"] == title), title)

    # Create embed for ticket
    embed = Embed(
        title=f"{title} {'от' if lang == 'ru' else 'by'} {interaction.author.display_name}",
        color=disnake.Color.green()
    )
    embed.add_field(
        name="Платформа" if lang == "ru" else "Platform",
        value=platform.capitalize(),
        inline=False
    )

    # Add hidden metadata to footer
    embed.set_footer(text=f"ticket_type:{ticket_type};lang:{lang};opener:{interaction.author.id}")

    for key, val in form_data.items():
        embed.add_field(
            name=key,
            value=(val if len(val) <= 1024 else val[:1021] + "…"),
            inline=False,
        )

    # Create persistent close button
    close_view = CloseTicketView(lang=lang)
    await channel.send(embed=embed, view=close_view)
    return channel


class FeedbackView(ui.View):
    def __init__(self, lang="en", is_russian=False):
        super().__init__(timeout=None)
        self.lang = lang
        self.is_russian = is_russian

        # Селект для типа обращения
        type_options = TYPE_OPTIONS_RU if is_russian else TYPE_OPTIONS
        type_placeholder = "Выберите тип обращения" if is_russian else "Select request type"
        self.type_select = ui.StringSelect(
            placeholder=type_placeholder,
            min_values=1,
            max_values=1,
            options=[disnake.SelectOption(**opt) for opt in type_options],
            custom_id=f"type_select_{lang}"
        )
        self.type_select.callback = self.type_callback
        self.add_item(self.type_select)

        # Селект для платформы
        platform_options = PLATFORM_OPTIONS_RU if is_russian else PLATFORM_OPTIONS
        platform_placeholder = "Выберите платформу" if is_russian else "Select platform"
        self.platform_select = ui.StringSelect(
            placeholder=platform_placeholder,
            min_values=1,
            max_values=1,
            options=[disnake.SelectOption(**opt) for opt in platform_options],
            custom_id=f"platform_select_{lang}"
        )
        self.platform_select.callback = self.platform_callback
        self.add_item(self.platform_select)

        # Кнопка отправки (всегда активна)
        submit_label = "Заполнить форму" if is_russian else "Fill Form"
        self.submit_button = ui.Button(
            label=submit_label,
            style=disnake.ButtonStyle.green,
            custom_id=f"submit_{lang}"
        )
        self.submit_button.callback = self.submit_callback
        self.add_item(self.submit_button)

    async def type_callback(self, interaction: disnake.MessageInteraction):
        # Откладываем ответ без обновления сообщения
        await interaction.response.defer(ephemeral=True, with_message=False)

        # Обновляем состояние пользователя
        state_key = (interaction.message.id, interaction.user.id)
        selected_value = interaction.data["values"][0]

        # Обновляем состояние
        if state_key not in user_states:
            user_states[state_key] = {}
        user_states[state_key]["selected_type"] = selected_value
        user_states[state_key]["timestamp"] = time.time()

    async def platform_callback(self, interaction: disnake.MessageInteraction):
        # Откладываем ответ без обновления сообщения
        await interaction.response.defer(ephemeral=True, with_message=False)

        # Обновляем состояние пользователя
        state_key = (interaction.message.id, interaction.user.id)
        selected_value = interaction.data["values"][0]

        # Обновляем состояние
        if state_key not in user_states:
            user_states[state_key] = {}
        user_states[state_key]["selected_platform"] = selected_value
        user_states[state_key]["timestamp"] = time.time()

    async def submit_callback(self, interaction: disnake.MessageInteraction):
        state_key = (interaction.message.id, interaction.user.id)
        state = user_states.get(state_key, {})

        # Проверяем, есть ли оба выбранных значения
        if not (state.get("selected_type") and state.get("selected_platform")):
            error_msg = "❗ Сначала выберите тип и платформу." if self.is_russian else "❗ Please select both type and platform first."
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        # Проверяем, не устарело ли состояние
        if time.time() - state.get("timestamp", 0) > 1800:  # 30 минут
            error_msg = "❗ Ваш выбор устарел, начните заново." if self.is_russian else "❗ Your selection has expired, please start over."
            await interaction.response.send_message(error_msg, ephemeral=True)
            # Удаляем устаревшее состояние
            if state_key in user_states:
                del user_states[state_key]
            return

        # Определяем конфиг модального окна
        if self.is_russian:
            modal_config = MODAL_CONFIGS_RU[state["selected_type"]]
            title_for_ticket = MODAL_CONFIGS[state["selected_type"]]["title"]
        else:
            modal_config = MODAL_CONFIGS[state["selected_type"]]
            title_for_ticket = modal_config["title"]

        # Создаем компоненты для модального окна
        inputs = []
        for input_config in modal_config["inputs"]:
            if "condition" in input_config and not input_config["condition"](state["selected_platform"]):
                continue
            inputs.append(ui.TextInput(
                label=input_config["label"],
                custom_id=input_config["custom_id"],
                style=input_config["style"],
                max_length=input_config.get("max_length", 4000)
            ))

        # Создаем модальное окно
        class FeedbackModal(ui.Modal):
            def __init__(self, is_russian):
                super().__init__(
                    title=modal_config["title"],
                    custom_id=f"modal_{state['selected_type']}_{state['selected_platform']}",
                    components=inputs
                )
                self.is_russian = is_russian

            async def callback(self, modal_interaction: disnake.ModalInteraction):
                await modal_interaction.response.defer(ephemeral=True)
                try:
                    channel = await create_ticket_channel(
                        modal_interaction,
                        title_for_ticket,
                        state["selected_platform"],
                        global_roles_config,
                        global_channels_config,
                        modal_interaction.text_values,
                        lang="ru" if self.is_russian else "en"
                    )
                    success_msg = f"✅ Канал создан: {channel.mention}" if self.is_russian else f"✅ Channel created: {channel.mention}"
                    await modal_interaction.followup.send(success_msg, ephemeral=True)
                except Exception as e:
                    log.error(f"Ticket creation error: {e}")
                    error_msg = "❌ Ошибка при создании тикета" if self.is_russian else "❌ Error creating ticket"
                    await modal_interaction.followup.send(error_msg, ephemeral=True)
                finally:
                    state_key = (interaction.message.id, interaction.user.id)
                    if state_key in user_states:
                        del user_states[state_key]

        # Передаем флаг при создании модального окна
        await interaction.response.send_modal(FeedbackModal(is_russian=self.is_russian))

async def setup_feedback_channel(bot, channels_config, roles_config, guild_id):
    """Setup both Russian and English feedback channels"""
    global global_channels_config, global_roles_config
    global_channels_config = channels_config
    global_roles_config = roles_config

    # Регистрируем обработчик кнопок
    @bot.listen("on_button_click")
    async def handle_close_button(interaction: disnake.MessageInteraction):
        if interaction.component.custom_id != "persistent_close_ticket":
            return

        # Получаем канал и сообщение
        channel = interaction.channel
        message = await channel.fetch_message(interaction.message.id)

        if not message.embeds:
            await interaction.response.send_message(
                "❌ Ticket information not found",
                ephemeral=True
            )
            return

        embed = message.embeds[0]
        footer_text = embed.footer.text

        if not footer_text:
            await interaction.response.send_message(
                "❌ Metadata not found in ticket",
                ephemeral=True
            )
            return

        # Парсим метаданные
        metadata = {}
        for part in footer_text.split(";"):
            if ":" in part:
                key, value = part.split(":", 1)
                metadata[key] = value

        if "ticket_type" not in metadata or "lang" not in metadata or "opener" not in metadata:
            await interaction.response.send_message(
                "❌ Invalid ticket metadata",
                ephemeral=True
            )
            return

        # Извлекаем данные
        ticket_type = metadata["ticket_type"]
        lang = metadata["lang"]
        opener_id = int(metadata["opener"])

        # Получаем opener
        opener = interaction.guild.get_member(opener_id)
        if not opener:
            try:
                opener = await interaction.guild.fetch_member(opener_id)
            except disnake.NotFound:
                await interaction.response.send_message(
                    "❌ Ticket opener not found",
                    ephemeral=True
                )
                return

        # Получаем платформу
        platform_field = next((field for field in embed.fields if field.name in ["Platform", "Платформа"]), None)
        if not platform_field:
            await interaction.response.send_message(
                "❌ Platform information not found",
                ephemeral=True
            )
            return
        platform = platform_field.value

        # Собираем данные формы
        form_data = {}
        for field in embed.fields:
            if field.name not in ["Platform", "Платформа"]:
                form_data[field.name] = field.value

        # Создаем модальное окно подтверждения
        modal = ConfirmCloseModal(
            channel=channel,
            opener=opener,
            ticket_data={
                'title': embed.title,
                'type': ticket_type,
                'platform': platform,
                'content': form_data
            },
            channels_config=global_channels_config,
            lang=lang
        )
        await interaction.response.send_modal(modal)

    # Получаем объект сервера по ID
    guild = bot.get_guild(guild_id)
    if not guild:
        log.error(f"Сервер с ID {guild_id} не найден")
        return

    # Setup Russian feedback channel
    ru_key = "⚖│обратная-связь"
    ru_ch_cfg = channels_config["channels"].get(ru_key)
    if ru_ch_cfg:
        ru_channel = guild.get_channel(ru_ch_cfg["id"])
        if ru_channel:
            try:
                # Очищаем канал
                await ru_channel.purge(limit=100)

                # Создаем вебхук
                ru_webhook = await ru_channel.create_webhook(
                    name=ru_ch_cfg["webhook"]["name"],
                    avatar=await bot.user.display_avatar.read(),
                )

                # Создаем embed
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

                # Создаем представление
                ru_view = FeedbackView(lang="ru", is_russian=True)

                # Отправляем сообщение через вебхук
                await ru_webhook.send(
                    embed=ru_embed,
                    view=ru_view,
                    username=ru_ch_cfg["webhook"]["name"]
                )

                # Удаляем вебхук
                await ru_webhook.delete()
            except Exception as e:
                log.error(f"Ошибка настройки русского канала: {e}")
        else:
            log.error(f"Русский канал не найден: ID {ru_ch_cfg['id']}")
    else:
        log.error("Конфиг для русского канала не найден")

    # Setup English feedback channel
    en_key = "⚖│feedback"
    en_ch_cfg = channels_config["channels"].get(en_key)
    if en_ch_cfg:
        en_channel = guild.get_channel(en_ch_cfg["id"])
        if en_channel:
            try:
                await en_channel.purge(limit=100)
                en_webhook = await en_channel.create_webhook(
                    name=en_ch_cfg["webhook"]["name"],
                    avatar=await bot.user.display_avatar.read(),
                )

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

                en_view = FeedbackView(lang="en", is_russian=False)
                await en_webhook.send(
                    embed=en_embed,
                    view=en_view,
                    username=en_ch_cfg["webhook"]["name"]
                )

                await en_webhook.delete()
            except Exception as e:
                log.error(f"Error setting up English feedback: {e}")
        else:
            log.error(f"English feedback channel not found: ID {en_ch_cfg['id']}")
    else:
        log.error("English feedback config not found")

    # Запускаем периодическую очистку устаревших состояний
    async def cleanup_task():
        while True:
            await asyncio.sleep(1800)  # Каждые 30 минут
            current_time = time.time()
            global last_cleanup
            if current_time - last_cleanup > 1800:
                for key in list(user_states.keys()):
                    if current_time - user_states[key]["timestamp"] > 1800:
                        del user_states[key]
                last_cleanup = current_time

    bot.loop.create_task(cleanup_task())