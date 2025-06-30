from disnake import TextInputStyle
import time

user_states = {}
last_cleanup = time.time()

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
            {"label": "Violation description", "custom_id": "desc", "style": TextInputStyle.paragraph, "max_length": 4000}
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
            {"label": "Why you want this position", "custom_id": "why", "style": TextInputStyle.paragraph, "max_length": 500},
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
            {"label": "Почему вы хотите на должность", "custom_id": "why", "style": TextInputStyle.paragraph, "max_length": 500},
            {"label": "О себе", "custom_id": "about", "style": TextInputStyle.paragraph, "max_length": 4000},
            {"label": "Игровой ник", "custom_id": "nick", "style": TextInputStyle.short,
             "condition": lambda platform: platform == "mindustry", "max_length": 200}
        ]
    }
}