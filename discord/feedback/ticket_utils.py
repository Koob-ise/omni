import disnake
from disnake import Embed
import logging
from configs.feedback_config import config, TEXTS, TICKET_COLORS
import re

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

        if title == "Complaint" and platform.lower() == "discord":
            offender_tag = form_data.get("offender")
            if offender_tag:
                log.info(f"Discord complaint detected. Attempting to add offender: {offender_tag}")
                offender = None
                clean_tag = offender_tag.strip()

                match = re.search(r'\d{17,}', clean_tag)
                if match:
                    try:
                        offender_id = int(match.group(0))
                        offender = interaction.guild.get_member(offender_id)
                        if not offender:
                            offender = await interaction.guild.fetch_member(offender_id)
                        log.info(f"Found offender by ID: {offender.display_name}")
                    except (ValueError, disnake.NotFound):
                        log.warning(f"Could not find a member with ID {match.group(0)}, proceeding to search by name.")
                    except Exception as e:
                        log.error(f"Error fetching member by ID {match.group(0)}: {e}")

                if not offender:
                    log.info(f"Could not find offender by ID, trying by name: {clean_tag}")
                    offender = interaction.guild.get_member_named(clean_tag)

                if offender:
                    log.info(f"Offender {offender.display_name} found. Adding to channel overwrites.")
                    overwrites[offender] = disnake.PermissionOverwrite(read_messages=True, send_messages=True)
                else:
                    log.warning(f"Could not find offender on the server using the provided tag: {clean_tag}")

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
                overwrites[role] = disnake.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
            else:
                log.debug(f"Skipping role {role_name}: '{channel_key}' not in '{permissions_value}'")

        log.info(f"Final overwrites: {list(overwrites.keys())}")
        display_name = interaction.author.display_name.replace(" ", "-").replace("#", "")
        channel_name = f"{title.lower()}-{platform}-{display_name}"[:100]
        log.info(f"Channel name: {channel_name}")

        channel = await interaction.guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        log.info(f"Channel created: {channel.name} (ID: {channel.id})")

        webhook_name = category_webhook_config.get("name", "Tickets Bot")
        webhook_avatar_path = category_webhook_config.get("avatar")
        avatar_bytes = None
        if webhook_avatar_path:
            try:
                with open(webhook_avatar_path, "rb") as f:
                    avatar_bytes = f.read()
            except FileNotFoundError:
                log.error(f"Error reading webhook avatar file: {webhook_avatar_path}")

        webhook = await channel.create_webhook(name=webhook_name, avatar=avatar_bytes)
        log.info(f"Webhook created: {webhook.name}")

        texts_en = TEXTS["en"]["ticket_utils"]
        title_text = texts_en["ticket_title"].format(title=title, user=interaction.author.display_name)
        color_name = TICKET_COLORS.get(title, "green")
        color = getattr(disnake.Color, color_name, disnake.Color.green)()

        embed = Embed(title=title_text, color=color)
        embed.add_field(name="Platform", value=platform.capitalize(), inline=False)
        footer_text = f"ticket_type:{ticket_type};lang:{lang};opener:{interaction.author.id}"
        embed.set_footer(text=footer_text)
        log.debug(f"Embed footer: {footer_text}")

        field_mapping = {"offender": "offender", "offender_game": "offender", "reason": "rule", "datetime": "violation_datetime"}
        field_order = ["offender", "rule", "violation_datetime"]
        english_form_data = {}
        for original_key, value in form_data.items():
            new_key = field_mapping.get(original_key, original_key)
            english_form_data[new_key] = value

        for field_name in field_order:
            if field_name in english_form_data:
                field_value = english_form_data[field_name]
                if len(field_value) > 1024:
                    field_value = field_value[:1021] + "…"
                embed.add_field(name=field_name, value=field_value, inline=False)
                log.debug(f"Added field: {field_name} = {field_value[:50]}...")

        for key, val in english_form_data.items():
            if key not in field_order:
                field_value = val if len(val) <= 1024 else val[:1021] + "…"
                embed.add_field(name=key, value=field_value, inline=False)
                log.debug(f"Added remaining field: {key} = {field_value[:50]}...")

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