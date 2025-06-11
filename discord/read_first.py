#read_first.py
from database.db import create_user
import disnake
from disnake import Embed, Webhook, ui
from disnake.ext import commands
import asyncio
import json
import os


class LanguageSelect(ui.Select):
    def __init__(self, roles_config):
        self.roles_config = roles_config
        options = [
            disnake.SelectOption(
                label="Русский",
                description="Доступ к русскоязычным каналам",
                emoji="🇷🇺",
                value="russian"
            ),
            disnake.SelectOption(
                label="English",
                description="Access to English channels",
                emoji="🇬🇧",
                value="english"
            ),
            disnake.SelectOption(
                label="Русский + English",
                description="Доступ ко всем языковым каналам",
                emoji="🌐",
                value="bilingual"
            )
        ]
        super().__init__(
            custom_id="language_select",
            placeholder="Выберите язык / Select language",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: disnake.MessageInteraction):
        guild = interaction.guild
        member = interaction.author

        # Получаем роли из конфига
        ru_role = guild.get_role(self.roles_config["language_roles"]["russian"])
        en_role = guild.get_role(self.roles_config["language_roles"]["english"])
        both_role = guild.get_role(self.roles_config["language_roles"]["bilingual"])

        try:
            discord_user = create_user('discord', str(member.id))
            # Удаляем все языковые роли
            for role in [ru_role, en_role, both_role]:
                if role and role in member.roles:
                    await member.remove_roles(role)

            # Выдаем выбранную роль
            if self.values[0] == "russian" and ru_role:
                await member.add_roles(ru_role)
                await interaction.response.send_message(
                    "✅ Язык установлен: **Русский**\n\n"
                    "• Этот канал будет скрыт\n"
                    "• Для смены языка используйте канал #🔧│персонализация\n"
                    "• Вам доступны русскоязычные каналы сервера",
                    ephemeral=True
                )
            elif self.values[0] == "english" and en_role:
                await member.add_roles(en_role)
                await interaction.response.send_message(
                    "✅ Language set to: **English**\n\n"
                    "• This channel will be hidden\n"
                    "• To change language use #🔧│personalization channel\n"
                    "• You now have access to English channels",
                    ephemeral=True
                )
            elif self.values[0] == "bilingual" and both_role:
                await member.add_roles(both_role)
                await interaction.response.send_message(
                    "✅ Language set to: **Russian + English**\n\n"
                    "• Этот канал будет скрыт\n"
                    "• Для смены языка используйте #🔧│персонализация или #🔧│personalization\n"
                    "• Вам доступны ВСЕ языковые каналы сервера",
                    ephemeral=True
                )
        except disnake.Forbidden:
            await interaction.response.send_message(
                "❌ У бота недостаточно прав для управления ролями!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Произошла ошибка: {str(e)}",
                ephemeral=True
            )


class LanguageView(ui.View):
    def __init__(self, roles_config):
        super().__init__(timeout=None)
        self.roles_config = roles_config
        self.add_item(LanguageSelect(roles_config))


async def setup_language_roles(bot: commands.Bot):
    """Настройка обработчика выбора языка"""
    roles_path = os.path.join(os.path.dirname(__file__), "../configs/roles_config.json")
    with open(roles_path, "r", encoding="utf-8") as f:
        roles_config = json.load(f)

    view = LanguageView(roles_config)
    bot.add_view(view)
    print("✅ Обработчик языковых ролей настроен")


async def check_read_first_channel(bot: commands.Bot, channel_id: int, webhook_config: dict):
    """Проверка и создание приветственного сообщения"""
    roles_path = os.path.join(os.path.dirname(__file__), "../configs/roles_config.json")
    with open(roles_path, "r", encoding="utf-8") as f:
        roles_config = json.load(f)

    channel = bot.get_channel(channel_id)
    if not channel:
        print(f"❌ Канал {channel_id} не найден!")
        return

    # Удаление сообщений от пользователей
    deleted = 0
    async for message in channel.history(limit=None):
        if not message.author.bot:
            try:
                await message.delete()
                deleted += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"⚠ Ошибка удаления: {e}")

    print(f"♻ Удалено {deleted} сообщений")

    # Проверяем, есть ли уже наше приветственное сообщение
    has_welcome_message = False
    async for message in channel.history(limit=100):
        # Проверяем либо прямое сообщение от бота, либо сообщение от вебхука бота
        if (message.author == bot.user or
            (isinstance(message.author, disnake.User) and message.author.display_name == webhook_config.get("name", "Omnicorp Bot"))):
            if message.embeds and any("Добро пожаловать" in embed.title or "Welcome" in embed.title for embed in message.embeds):
                has_welcome_message = True
                break

    if has_welcome_message:
        print("ℹ Приветственное сообщение уже существует")
        return

    # Создание нового сообщения только если его нет
    try:
        webhook = await channel.create_webhook(
            name=webhook_config.get("name", "Omnicorp Bot"),
            reason=webhook_config.get("reason", "Language selection")
        )

        embed = Embed(
            title="Добро пожаловать в OmniCorp! / Welcome to OmniCorp!",
            description=(
                "**Пожалуйста, выберите ваш язык:**\n"
                "**Please select your language:**\n\n"
                "• Выбор языка определит доступные вам каналы\n"
                "• Language selection will determine available channels\n\n"
                "🇷🇺 **Русский** - доступ к русскоязычным каналам\n"
                "🇬🇧 **English** - access to English channels\n"
                "🌐 **Русский + English** - доступ ко ВСЕМ языковым каналам\n\n"
                "**Важно:**\n"
                "• После выбора этот канал будет скрыт\n"
                "• Для смены языка используйте:\n"
                "  - #🔧│персонализация (для русских)\n"
                "  - #🔧│personalization (for English)\n\n"
                "_Вы можете изменить язык в любое время_"
            ),
            color=disnake.Color.orange()
        )

        # Добавляем изображения из конфига
        if "banner" in webhook_config and webhook_config["banner"]:
            embed.set_image(url=webhook_config["banner"])
        if "logo" in webhook_config and webhook_config["logo"]:
            embed.set_thumbnail(url=webhook_config["logo"])
        else:
            embed.set_thumbnail(url="https://i.imgur.com/default_logo.png")

        embed.set_footer(text="OmniCorp © 2025")

        view = LanguageView(roles_config)
        await webhook.send(
            embed=embed,
            username=webhook_config.get("name", "Omnicorp Bot"),
            avatar_url=webhook_config.get("avatar", None),
            view=view
        )

        await webhook.delete()
        print("✅ Приветственное сообщение с меню выбора отправлено")

    except Exception as e:
        print(f"⚠ Ошибка при работе с вебхуком: {e}")