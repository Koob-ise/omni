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
    "Staff Application": "green"
}

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
            {"label": "Age", "custom_id": "age", "style": TextInputStyle.short, "max_length": 2},
            {"label": "About yourself", "custom_id": "about", "style": TextInputStyle.paragraph, "max_length": 4000},
            {"label": "Game username", "custom_id": "nick", "style": TextInputStyle.short,
             "condition": lambda platform: platform == "mindustry", "max_length": 200}
        ]
    }
}

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
            {"label": "Возраст", "custom_id": "age", "style": TextInputStyle.short, "max_length": 2},
            {"label": "О себе", "custom_id": "about", "style": TextInputStyle.paragraph, "max_length": 4000},
            {"label": "Игровой ник", "custom_id": "nick", "style": TextInputStyle.short,
             "condition": lambda platform: platform == "mindustry", "max_length": 200}
        ]
    }
}

TEXTS = {
    "en": {
        "modals": {
            "confirm_close": {
                "title": "Confirm Closure",
                "label": "Confirmation",
                "placeholder": "Type 'yes' to confirm",
                "hint": "❗ Please type 'yes' to confirm closure",
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
                "platform": "❌ Platform information not found"
            }
        },
        "ticket_utils": {
            "ticket_title": "{title} by {user}",
            "platform_field": "Platform",
            "success": "✅ Channel created: {channel}",
            "error": "❌ Error creating ticket"
        },
        "views": {
            "close_ticket": "Close Ticket",
            "type_placeholder": "Select request type",
            "platform_placeholder": "Select platform",
            "submit_button": "Fill Form",
            "errors": {
                "select_both": "❗ Please select both type and platform first.",
                "expired": "❗ Your selection has expired, please start over."
            }
        }
    },
    "ru": {
        "modals": {
            "confirm_close": {
                "title": "Подтверждение закрытия",
                "label": "Подтверждение",
                "placeholder": "Введите 'да' для подтверждения",
                "hint": "❗ Введите 'да' для подтверждения",
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
                "platform": "❌ Информация о платформе не найдена"
            }
        },
        "ticket_utils": {
            "ticket_title": "{title} от {user}",
            "platform_field": "Платформа",
            "success": "✅ Канал создан: {channel}",
            "error": "❌ Ошибка при создании тикета"
        },
        "views": {
            "close_ticket": "Закрыть тикет",
            "type_placeholder": "Выберите тип обращения",
            "platform_placeholder": "Выберите платформу",
            "submit_button": "Заполнить форму",
            "errors": {
                "select_both": "❗ Сначала выберите тип и платформу.",
                "expired": "❗ Ваш выбор устарел, начните заново."
            }
        }
    }
}