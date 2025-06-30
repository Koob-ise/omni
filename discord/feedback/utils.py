import disnake
from disnake import Embed
import logging
import io

log = logging.getLogger(__name__)


async def generate_transcript(channel):
    transcript = []
    async for message in channel.history(limit=200, oldest_first=True):
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


async def create_ticket_channel(interaction, title, platform, form_data, lang, channels_config, roles_config):
    if not channels_config or not channels_config.get("categories"):
        log.error("Channels config is missing or invalid")
        return

    categories = channels_config.get("categories", {})
    if not categories:
        log.error("No categories found in config")
        return

    category_id = next(iter(categories.values())).get("id")
    if not category_id:
        log.error("Category ID not found in config")
        return

    category = interaction.guild.get_channel(category_id)
    if not category:
        log.error(f"Category not found: {category_id}")
        return

    overwrites = {
        interaction.guild.default_role: disnake.PermissionOverwrite(read_messages=False),
        interaction.author: disnake.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    if roles_config:
        staff_roles = roles_config.get("staff_roles", {})
        for role_name, role_info in staff_roles.items():
            if role_id := role_info.get("id"):
                if role := interaction.guild.get_role(role_id):
                    overwrites[role] = disnake.PermissionOverwrite(
                        read_messages=True, send_messages=True, manage_messages=True
                    )

    channel_name = f"{title.lower()}-{platform}-{interaction.author.display_name}".replace(" ", "-")
    channel = await interaction.guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites
    )

    ticket_type = title.lower()
    embed = Embed(
        title=f"{title} {'от' if lang == 'ru' else 'by'} {interaction.author.display_name}",
        color=disnake.Color.green()
    )
    embed.add_field(
        name="Платформа" if lang == "ru" else "Platform",
        value=platform.capitalize(),
        inline=False
    )
    embed.set_footer(text=f"ticket_type:{ticket_type};lang:{lang};opener:{interaction.author.id}")

    for key, val in form_data.items():
        embed.add_field(
            name=key,
            value=(val if len(val) <= 1024 else val[:1021] + "…"),
            inline=False,
        )

    from .components import CloseTicketView
    close_view = CloseTicketView(lang=lang)
    await channel.send(embed=embed, view=close_view)
    return channel