from disnake import TextInputStyle

class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.channels_config = None
            cls._instance.roles_config = None
        return cls._instance

    def init(self, channels_config, roles_config):
        self.channels_config = channels_config
        self.roles_config = roles_config

    @property
    def channels(self):
        if self.channels_config is None:
            raise RuntimeError("Channels config not initialized")
        return self.channels_config

    @property
    def roles(self):
        if self.roles_config is None:
            raise RuntimeError("Roles config not initialized")
        return self.roles_config


config = Config()

TICKET_COLORS = {
    "Complaint": "red",
    "Appeal": "orange",
    "Staff Application": "green",
    "feedback": "green"
}

TYPE_OPTIONS = [
    {"label": "Complaint", "value": "complaint", "emoji": "⚠️"},
    {"label": "Appeal", "value": "appeal", "emoji": "📝"},
    {"label": "Staff Application", "value": "staff", "emoji": "🛡️"}
]

PLATFORM_OPTIONS = [
    {"label": "Mindustry", "value": "mindustry", "emoji": "🎮"},
    {"label": "Discord", "value": "discord", "emoji": "💬"}
]

MODAL_CONFIGS = {
    "complaint": {
        "title": "Complaint",
        "inputs": [
            {"label": "Offender's tag", "custom_id": "offender", "style": TextInputStyle.short, "max_length": 200},
            {"label": "Rule violation", "custom_id": "rule", "style": TextInputStyle.short, "max_length": 15},
            {"label": "Date & time of violation (GMT/Timezone)", "custom_id": "violation_datetime", "style": TextInputStyle.short, "max_length": 50},
            {"label": "Violation description", "custom_id": "desc", "style": TextInputStyle.paragraph, "max_length": 1000},
            {"label": "Your game username and server", "custom_id": "username", "style": TextInputStyle.short, "condition": lambda platform: platform == "mindustry", "max_length": 300}
        ]
    },
    "appeal": {
        "title": "Appeal",
        "inputs": [
            {"label": "Punishment reason", "custom_id": "reason", "style": TextInputStyle.short, "max_length": 500},
            {"label": "Punishment date & time (GMT/Timezone)", "custom_id": "punishment_datetime", "style": TextInputStyle.short, "max_length": 50},
            {"label": "Description", "custom_id": "desc", "style": TextInputStyle.paragraph, "max_length": 1000},
            {"label": "Your game username", "custom_id": "username", "style": TextInputStyle.short, "condition": lambda platform: platform == "mindustry", "max_length": 200},
            {"label": "Server", "custom_id": "server", "style": TextInputStyle.short, "condition": lambda platform: platform == "mindustry", "max_length": 100}
        ]
    },
    "staff": {
        "title": "Staff Application",
        "inputs": [
            {"label": "Desired position", "custom_id": "position", "style": TextInputStyle.short, "max_length": 100},
            {"label": "Why you want this position", "custom_id": "why", "style": TextInputStyle.paragraph, "max_length": 500},
            {"label": "Age", "custom_id": "age", "style": TextInputStyle.short, "max_length": 2},
            {"label": "About yourself", "custom_id": "about", "style": TextInputStyle.paragraph, "max_length": 1000},
            {"label": "Your game username", "custom_id": "username", "style": TextInputStyle.short, "condition": lambda platform: platform == "mindustry", "max_length": 200}
        ]
    }
}

MODAL_CONFIGS_RU = {
    "complaint": {
        "title": "Жалоба",
        "inputs": [
            {"label": "Тег нарушителя", "custom_id": "offender", "style": TextInputStyle.short, "max_length": 200},
            {"label": "Пункт правила", "custom_id": "rule", "style": TextInputStyle.short, "max_length": 15},
            {"label": "Дата и время нарушения (GMT/Часовой пояс)", "custom_id": "violation_datetime", "style": TextInputStyle.short, "max_length": 50},
            {"label": "Описание нарушения", "custom_id": "desc", "style": TextInputStyle.paragraph, "max_length": 1000},
            {"label": "Ваш игровой ник и сервер", "custom_id": "username", "style": TextInputStyle.short, "condition": lambda platform: platform == "mindustry", "max_length": 300}
        ]
    },
    "appeal": {
        "title": "Апелляция",
        "inputs": [
            {"label": "Причина наказания", "custom_id": "reason", "style": TextInputStyle.short, "max_length": 500},
            {"label": "Дата и время наказания (GMT/Часовой пояс)", "custom_id": "punishment_datetime", "style": TextInputStyle.short, "max_length": 50},
            {"label": "Описание", "custom_id": "desc", "style": TextInputStyle.paragraph, "max_length": 1000},
            {"label": "Ваш игровой ник", "custom_id": "username", "style": TextInputStyle.short, "condition": lambda platform: platform == "mindustry", "max_length": 200},
            {"label": "Сервер", "custom_id": "server", "style": TextInputStyle.short, "condition": lambda platform: platform == "mindustry", "max_length": 100}
        ]
    },
    "staff": {
        "title": "Заявка на стафф",
        "inputs": [
            {"label": "Желаемая должность", "custom_id": "position", "style": TextInputStyle.short, "max_length": 100},
            {"label": "Почему вы хотите эту должность", "custom_id": "why", "style": TextInputStyle.paragraph, "max_length": 500},
            {"label": "Возраст", "custom_id": "age", "style": TextInputStyle.short, "max_length": 2},
            {"label": "О себе", "custom_id": "about", "style": TextInputStyle.paragraph, "max_length": 1000},
            {"label": "Ваш игровой ник", "custom_id": "username", "style": TextInputStyle.short, "condition": lambda platform: platform == "mindustry", "max_length": 200}
        ]
    }
}

TYPE_OPTIONS_RU = [
    {"label": "Жалоба", "value": "complaint", "emoji": "⚠️"},
    {"label": "Апелляция", "value": "appeal", "emoji": "📝"},
    {"label": "Заявка на стафф", "value": "staff", "emoji": "🛡️"}
]

PLATFORM_OPTIONS_RU = [
    {"label": "Mindustry", "value": "mindustry", "emoji": "🎮"},
    {"label": "Discord", "value": "discord", "emoji": "💬"}
]

TEXTS = {
    "en": {
        "modals": {
            "confirm_close": {
                "confirmation_message": "Are you sure you want to close the ticket?",
                "cancelled": "Ticket closing cancelled.",
                "closing_in_progress": "Please wait, the ticket is being closed...",
                "title": "Confirm Closure",
                "label": "Confirmation",
                "placeholder": "Type 'yes' to confirm",
                "hint": "⚠️ Please type 'yes' to confirm closure",
                "success": "✅ Ticket closed successfully",
                "error": "❌ Invalid confirmation",
                "db_error": "⚠️ Ticket save error",
                "delete_error": "❌ Channel deletion error",
                "critical_error": "❌ Critical error"
            },
            "embed_titles": {
                "closed_ticket": "Closed ticket: {title}",
                "type": "Type",
                "platform": "Platform",
                "opened_by": "Opened by",
                "closed_by": "Closed by"
            }
        },
        "setup": {
            "feedback": {
                "title": "Feedback System",
                "description": (
                    "**1.** Select request type: `Complaint`, `Appeal` or `Staff Application`\n"
                    "**2.** Select platform: `Mindustry` or `Discord`\n"
                    "**3.** Click `Fill Form` button\n\n"
                    "After submitting the form, a private channel will be created accessible only to you and staff."
                )
            },
            "errors": {
                "ticket_info": "❌ Ticket information not found",
                "metadata": "❌ Metadata not found in ticket",
                "invalid_metadata": "❌ Invalid ticket metadata",
                "opener": "❌ Ticket opener not found",
                "platform": "❌ Platform information not found",
                "close_permission": "❌ You do not have permission to close this ticket.",
                "offender_cannot_close": "❌ You are listed as the offender in this complaint and cannot close it."
            }
        },
        "ticket_utils": {
            "ticket_title": "{title} by {user}",
            "platform_field": "Platform",
            "success": "✅ Channel created: {channel}",
            "error": "❌ Error creating ticket",
            "errors": {
                "missing_tag": "❌ Please provide the offender's Discord tag!",
                "member_not_found": "❌ User `{tag}` not found on the server! Check the tag format"
            }
        },
        "views": {
            "close_ticket": "Close Ticket",
            "type_placeholder": "Select request type",
            "platform_placeholder": "Select platform",
            "submit_button": "Fill Form",
            "errors": {
                "select_both": "⚠️ Please select both type and platform first.",
                "expired": "⚠️ Your selection has expired, please start over."
            }
        }
    },
    "ru": {
        "modals": {
            "confirm_close": {
                "confirmation_message": "Вы уверены, что хотите закрыть тикет?",
                "cancelled": "Закрытие тикета отменено.",
                "closing_in_progress": "Подождите, тикет закрывается...",
                "title": "Подтверждение закрытия",
                "label": "Подтверждение",
                "placeholder": "Введите 'да' для подтверждения",
                "hint": "⚠️ Введите 'да' для подтверждения",
                "success": "✅ Тикет успешно закрыт",
                "error": "❌ Неверное подтверждение",
                "db_error": "⚠️ Ошибка сохранения тикета",
                "delete_error": "❌ Ошибка удаления канала",
                "critical_error": "❌ Критическая ошибка"
            },
            "embed_titles": {
                "closed_ticket": "Закрытый тикет: {title}",
                "type": "Тип",
                "platform": "Платформа",
                "opened_by": "Открыт",
                "closed_by": "Закрыт"
            }
        },
        "setup": {
            "feedback": {
                "title": "Обратная связь",
                "description": (
                    "**1.** Выберите тип обращения: `Жалоба`, `Апелляция` или `Заявка на стафф`\n"
                    "**2.** Выберите платформу: `Mindustry` или `Discord`\n"
                    "**3.** Нажмите кнопку `Заполнить форму`\n\n"
                    "После заполнения формы будет создан приватный канал, доступный только вам и администрации."
                )
            },
            "errors": {
                "ticket_info": "❌ Информация о тикете не найдена",
                "metadata": "❌ Метаданные не найдены в тикете",
                "invalid_metadata": "❌ Неверные метаданные тикета",
                "opener": "❌ Автор тикета не найден",
                "platform": "❌ Информация о платформе не найдена",
                "close_permission": "❌ У вас нет прав для закрытия этого тикета.",
                "offender_cannot_close": "❌ Вы указаны как нарушитель в этой жалобе и не можете ее закрыть."
            }
        },
        "ticket_utils": {
            "ticket_title": "{title} от {user}",
            "platform_field": "Платформа",
            "success": "✅ Канал создан: {channel}",
            "error": "❌ Ошибка при создании тикета",
            "errors": {
                "missing_tag": "❌ Укажите тег нарушителя в Discord!",
                "member_not_found": "❌ Пользователь `{tag}` не найден на сервере! Проверьте формат"
            }
        },
        "views": {
            "close_ticket": "Закрыть тикет",
            "type_placeholder": "Выберите тип обращения",
            "platform_placeholder": "Выберите платформу",
            "submit_button": "Заполнить форму",
            "errors": {
                "select_both": "⚠️ Сначала выберите тип и платформу.",
                "expired": "⚠️ Ваш выбор устарел, начните заново."
            }
        }
    }
}