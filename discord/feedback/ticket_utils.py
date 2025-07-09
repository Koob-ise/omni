import disnake
from disnake import Embed
import logging
from configs.feedback_config import config, TEXTS, TICKET_COLORS
import aiohttp

log = logging.getLogger(__name__)

async def create_ticket_channel(interaction, title, platform, form_data, lang="en"):
    try:
        log.info("Starting ticket channel creation")
        log.debug(f"Parameters: title={title}, platform={platform}, lang={lang}, author={interaction.author}")

        channels_config = config.channels
        roles_config = config.roles
        log.debug(f"Channels config: {channels_config}")
        log.debug(f"Roles config: {roles_config}")

        cat_data = channels_config["categories"]["❓│Помощь / Support"]
        category_id = cat_data.get("id")
        category_webhook_config = cat_data.get("webhook", {})

        log.debug(f"Category ID: {category_id}")
        category = interaction.guild.get_channel(category_id)
        if not category:
            log.error(f"Category not found: {category_id}")
            raise ValueError("Ticket category not found")
        log.info(f"Using category: {category.name}")

        overwrites = {
            interaction.guild.default_role: disnake.PermissionOverwrite(read_messages=False),
            interaction.author: disnake.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        log.debug(f"Initial overwrites: {overwrites.keys()}")

        ticket_type = title

        channel_key = f"{platform.capitalize()}-{ticket_type}"
        log.info(f"Channel key: {channel_key}")

        staff_roles = roles_config.get("staff_roles", {})
        log.info(f"Processing {len(staff_roles)} staff roles")

        for role_name, rdata in staff_roles.items():
            role_id = rdata.get("id")
            permissions_value = rdata.get("permissions")

            if not role_id:
                log.warning(f"Skipping role {role_name}: missing ID")
                continue

            if permissions_value is None:
                log.debug(f"Skipping role {role_name}: no permissions value")
                continue

            role = interaction.guild.get_role(role_id)
            if not role:
                log.warning(f"Role not found: {role_name} (ID: {role_id})")
                continue

            log.debug(f"Checking role: {role_name} (ID: {role_id}), permissions: '{permissions_value}'")

            if channel_key in permissions_value:
                log.info(f"Adding role {role_name} (ID: {role_id}) to ticket channel")
                overwrites[role] = disnake.PermissionOverwrite(
                    read_messages=True, send_messages=True, manage_messages=True
                )
            else:
                log.debug(f"Skipping role {role_name}: '{channel_key}' not in '{permissions_value}'")

        log.info(f"Final overwrites: {list(overwrites.keys())}")

        display_name = interaction.author.display_name.replace(" ", "-").replace("#", "")
        channel_name = f"{title.lower()}-{platform}-{display_name}"[:100]
        log.info(f"Channel name: {channel_name}")

        channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )
        log.info(f"Channel created: {channel.name} (ID: {channel.id})")

        webhook_name = category_webhook_config.get("name", "Tickets Bot")
        webhook_avatar_url = category_webhook_config.get("avatar")

        avatar_bytes = None
        if webhook_avatar_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(webhook_avatar_url) as resp:
                        if resp.status == 200:
                            avatar_bytes = await resp.read()
            except Exception as e:
                log.error(f"Error downloading webhook avatar: {e}")

        webhook = await channel.create_webhook(
            name=webhook_name,
            avatar=avatar_bytes
        )
        log.info(f"Webhook created: {webhook.name}")

        texts = TEXTS[lang]["ticket_utils"]
        title_text = texts["ticket_title"].format(
            title=title,
            user=interaction.author.display_name
        )

        color_name = TICKET_COLORS.get(title, "green")

        if hasattr(disnake.Color, color_name):
            color = getattr(disnake.Color, color_name)()
        else:
            color = disnake.Color.green()
            log.warning(f"Unknown color name: {color_name}, using green fallback")

        embed = Embed(
            title=title_text,
            color=color
        )
        embed.add_field(
            name=texts["platform_field"],
            value=platform.capitalize(),
            inline=False
        )

        footer_text = f"ticket_type:{ticket_type};lang:{lang};opener:{interaction.author.id}"
        embed.set_footer(text=footer_text)
        log.debug(f"Embed footer: {footer_text}")

        for key, val in form_data.items():
            field_value = val if len(val) <= 1024 else val[:1021] + "…"
            embed.add_field(name=key, value=field_value, inline=False)
            log.debug(f"Added field: {key} = {field_value[:50]}...")

        from .views import CloseTicketView
        close_view = CloseTicketView(lang=lang)
        await webhook.send(embed=embed, view=close_view)
        log.info("Ticket message sent to channel via webhook")

        await webhook.delete()
        log.info("Webhook deleted")

        return channel

    except Exception as e:
        log.error(f"Error in create_ticket_channel: {e}", exc_info=True)
        raise