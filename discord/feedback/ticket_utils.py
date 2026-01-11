import disnake
from disnake import Embed
import logging
from configs.feedback_config import config, TEXTS, TICKET_COLORS
import re
from database.tickets import log_ticket_open
from database.core import (
    get_user_internal_id, get_info_for_all_active_punishments, create_user,
    get_info_for_active_discord_complaints, find_mindustry_complaints_by_nickname,
    get_all_user_punishments
)

log = logging.getLogger(__name__)


def get_rule_description_text(input_string, lang):
    if not hasattr(config, 'rules') or not config.rules.get(lang):
        log.warning(f"Rules for language '{lang}' not found in config.")
        return None

    rules_data = config.rules[lang]  # {'full': {...}, 'basic': {...}}

    requested_rules = re.findall(r"(\d+(?:\.\d+)+)", input_string)

    if not requested_rules:
        return None

    requested_rules = sorted(list(set(requested_rules)), key=lambda x: [int(d) for d in x.split('.')])

    full_text_list = []
    basic_text_list = []

    for rule_num in requested_rules:
        if rule_num in rules_data.get("full", {}):
            full_text_list.append(f"**{rule_num}** {rules_data['full'][rule_num]}")

        if rule_num in rules_data.get("basic", {}):
            basic_text_list.append(f"**{rule_num}** {rules_data['basic'][rule_num]}")

    result_parts = []

    if full_text_list:
        result_parts.append("\n".join(full_text_list))

    if basic_text_list:
        header = "[ Basic version ]" if lang == "en" else "[ Базовая версия ]"
        result_parts.append(f"\n**{header}**\n" + "\n".join(basic_text_list))

    return "\n".join(result_parts) if result_parts else None


def _add_history_fields(embed, user_internal_id, guild_id, lang="en"):
    if not user_internal_id:
        return

    log.info(f"Fetching punishment history for internal ID: {user_internal_id}")
    history = get_all_user_punishments(user_internal_id)

    if not history:
        return

    active_warns = []
    active_punishments = []
    inactive_punishments = []

    punishments_channel_id = config.channels["channels"]["📌│punishments"]["id"]

    for action in history:
        action_type = action['action_type']
        reason = action.get('reason', 'No reason')
        date_str = action['time'].split(' ')[0]
        log_id = action.get('log_message_id')

        link_part = f"[{action_type.capitalize()}]"
        if log_id:
            url = f"https://discord.com/channels/{guild_id}/{punishments_channel_id}/{log_id}"
            link_part = f"[{action_type.capitalize()}]({url})"

        entry = f"{link_part} {reason} ({date_str})"

        if action['is_active']:
            if action_type == 'warn':
                active_warns.append(entry)
            else:
                active_punishments.append(entry)
        else:
            inactive_punishments.append(entry)

    def format_field(items):
        joined = "\n".join(items)
        if len(joined) > 1024:
            return joined[:1021] + "..."
        return joined

    h_active = "Active Punishments" if lang == "en" else "Активные наказания"
    h_warns = "Active Warns" if lang == "en" else "Активные варны"
    h_inactive = "Past Punishments" if lang == "en" else "Прошлые наказания"

    if active_punishments:
        embed.add_field(name=h_active, value=format_field(active_punishments), inline=False)

    if active_warns:
        count_text = f"**Count: {len(active_warns)}**\n" if lang == "en" else f"**Количество: {len(active_warns)}**\n"
        embed.add_field(name=h_warns, value=format_field([count_text + "\n".join(active_warns)]), inline=False)

    if inactive_punishments:
        embed.add_field(name=h_inactive, value=format_field(inactive_punishments), inline=False)


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

        offender_identifier = None
        offender_internal_id = None

        if title == "Complaint":
            if platform.lower() == "discord":
                offender_tag = form_data.get("offender")
                if offender_tag and offender_tag.strip():
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
                            log.warning(
                                f"Could not find a member with ID {match.group(0)}, proceeding to search by name.")
                        except Exception as e:
                            log.error(f"Error fetching member by ID {match.group(0)}: {e}")

                    if not offender:
                        log.info(f"Could not find offender by ID, trying by name: {clean_tag}")
                        offender = interaction.guild.get_member_named(clean_tag)

                    if offender:
                        log.info(f"Offender {offender.display_name} found. Adding to channel overwrites.")
                        overwrites[offender] = disnake.PermissionOverwrite(read_messages=True, send_messages=True)
                        offender_identifier = str(offender.id)
                        offender_internal_id = get_user_internal_id('discord', offender.id)
                    else:
                        log.warning(f"Could not find offender on the server using the provided tag: {clean_tag}")

            elif platform.lower() == "mindustry":
                raw_nickname = form_data.get("offender_game") or form_data.get("offender")
                if raw_nickname and raw_nickname.strip():
                    offender_identifier = raw_nickname.strip()
                    log.info(f"Mindustry complaint detected. Storing offender identifier: {offender_identifier}")
                    offender_internal_id = get_user_internal_id('mindustry', offender_identifier)

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
                overwrites[role] = disnake.PermissionOverwrite(read_messages=True, send_messages=True,
                                                               manage_messages=True)
            else:
                log.debug(f"Skipping role {role_name}: '{channel_key}' not in '{permissions_value}'")

        log.info(f"Final overwrites: {list(overwrites.keys())}")
        display_name = interaction.author.display_name.replace(" ", "-").replace("#", "")
        channel_name = f"{title.lower()}-{platform}-{display_name}"[:100]
        log.info(f"Channel name: {channel_name}")

        channel = await interaction.guild.create_text_channel(name=channel_name, category=category,
                                                              overwrites=overwrites)
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

        if title == "Appeal":
            log.info(f"Appeal ticket detected from user {interaction.author.id} on platform {platform}.")

            if platform.lower() == "discord":
                user_internal_id = get_user_internal_id("discord", interaction.author.id)
                if user_internal_id:
                    _add_history_fields(embed, user_internal_id, interaction.guild.id, lang)
                else:
                    log.warning(f"Could not find internal ID for user {interaction.author.id}.")

            else:
                appellant_nick = form_data.get("username")
                if appellant_nick:
                    log.info(f"Searching for Mindustry complaints against '{appellant_nick}'.")

                    mindustry_internal_id = get_user_internal_id("mindustry", appellant_nick)
                    if mindustry_internal_id:
                        _add_history_fields(embed, mindustry_internal_id, interaction.guild.id, lang)

                    found_complaints = find_mindustry_complaints_by_nickname(appellant_nick)

                    if found_complaints:
                        log.info(f"Found {len(found_complaints)} related Mindustry complaints.")
                        server_id = interaction.guild.id
                        closed_tickets_channel_id = config.channels["channels"]["📌│closed-tickets"]["id"]

                        complaint_links = []
                        for i, complaint in enumerate(found_complaints):
                            log_message_id = complaint.get('log_message_id')
                            if log_message_id:
                                link = f"https://discord.com/channels/{server_id}/{closed_tickets_channel_id}/{log_message_id}"
                                complaint_links.append(f"**Complaint #{i + 1}**: [View Log]({link})")

                        if complaint_links:
                            embed.add_field(
                                name="Related Mindustry Tickets",
                                value="\n".join(complaint_links),
                                inline=False
                            )
                else:
                    log.warning("Appellant's game nick not provided in the appeal form.")

        if title == "Complaint" and offender_internal_id:
            log.info(f"Fetching punishment history for offender internal ID: {offender_internal_id}")
            _add_history_fields(embed, offender_internal_id, interaction.guild.id, lang)

        embed.add_field(name="Platform", value=platform.capitalize(), inline=False)
        footer_text = f"ticket_type:{ticket_type};lang:{lang};opener:{interaction.author.id}"
        embed.set_footer(text=footer_text)
        log.debug(f"Embed footer: {footer_text}")

        field_mapping = {"offender": "offender", "offender_game": "offender", "reason": "rule",
                         "datetime": "violation_datetime"}
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

                if field_name == "rule":
                    rule_descriptions = get_rule_description_text(english_form_data[field_name], lang)
                    if rule_descriptions:
                        field_title = "📜 Rule Details" if lang == "en" else "📜 Описание правил"

                        if len(rule_descriptions) > 1024:
                            rule_descriptions = rule_descriptions[:1021] + "..."

                        embed.add_field(name=field_title, value=rule_descriptions, inline=False)
                        log.info(f"Added rule descriptions for: {english_form_data[field_name]}")

        for key, val in english_form_data.items():
            if key not in field_order:
                field_value = val if len(val) <= 1024 else val[:1021] + "…"
                embed.add_field(name=key, value=field_value, inline=False)
                log.debug(f"Added remaining field: {key} = {field_value[:50]}...")

        from .views import CloseTicketView
        close_view = CloseTicketView(lang=lang)
        await webhook.send(embed=embed, view=close_view)
        log.info("Ticket message sent to channel via webhook")

        formatted_ticket_type = f"{platform.capitalize()}-{title}"
        log_ticket_open(
            opener_discord_id=interaction.author.id,
            channel_id=channel.id,
            ticket_type=formatted_ticket_type,
            offender_identifier=offender_identifier
        )

        await webhook.delete()
        log.info("Webhook deleted")

        return channel

    except Exception as e:
        log.error(f"Error in create_ticket_channel: {e}", exc_info=True)
        raise