import disnake
from disnake import Embed
import logging
from .config import config, TYPE_OPTIONS_RU, TYPE_OPTIONS

log = logging.getLogger(__name__)


async def create_ticket_channel(interaction, title, platform, form_data, lang="en"):
    try:
        # Получаем конфигурацию
        channels_config = config.channels
        roles_config = config.roles

        # Получаем категорию
        if not channels_config.get("categories"):
            log.error("No categories in config")
            raise ValueError("No categories configured")

        category_id = next(iter(channels_config["categories"].values()))["id"]
        category = interaction.guild.get_channel(category_id)

        if not category:
            log.error(f"Category not found: {category_id}")
            raise ValueError("Ticket category not found")

        # Создаем права доступа
        overwrites = {
            interaction.guild.default_role: disnake.PermissionOverwrite(read_messages=False),
            interaction.author: disnake.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        # Добавляем права для персонала
        staff_roles = roles_config.get("staff_roles", {})
        for rdata in staff_roles.values():
            role_id = rdata.get("id")
            if role_id:
                role = interaction.guild.get_role(role_id)
                if role:
                    overwrites[role] = disnake.PermissionOverwrite(
                        read_messages=True, send_messages=True, manage_messages=True
                    )

        # Формируем имя канала
        display_name = interaction.author.display_name.replace(" ", "-").replace("#", "")
        channel_name = f"{title.lower()}-{platform}-{display_name}"[:100]  # Ограничение длины имени

        # Создаем канал
        channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        # Определяем тип тикета
        if lang == "ru":
            ticket_type = next((opt["value"] for opt in TYPE_OPTIONS_RU if opt["label"] == title), title)
        else:
            ticket_type = next((opt["value"] for opt in TYPE_OPTIONS if opt["label"] == title), title)

        # Создаем embed
        embed = Embed(
            title=f"{title} {'от' if lang == 'ru' else 'by'} {interaction.author.display_name}",
            color=disnake.Color.green()
        )
        embed.add_field(
            name="Платформа" if lang == "ru" else "Platform",
            value=platform.capitalize(),
            inline=False
        )

        # Добавляем метаданные в подвал
        embed.set_footer(text=f"ticket_type:{ticket_type};lang:{lang};opener:{interaction.author.id}")

        # Добавляем поля формы
        for key, val in form_data.items():
            # Обрезаем длинные значения
            field_value = val if len(val) <= 1024 else val[:1021] + "…"
            embed.add_field(name=key, value=field_value, inline=False)

        # Добавляем кнопку закрытия
        from .views import CloseTicketView
        close_view = CloseTicketView(lang=lang)
        await channel.send(embed=embed, view=close_view)

        return channel

    except Exception as e:
        log.error(f"Error in create_ticket_channel: {e}", exc_info=True)
        raise