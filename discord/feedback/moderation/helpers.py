import disnake
import re
import logging
from datetime import datetime, timedelta

log = logging.getLogger(__name__)


async def get_webhook_for_channel(channel, config, category_name):
    try:
        webhook_config = config["categories"][category_name]["webhook"]
        webhook_name = webhook_config.get("name")
        webhooks = await channel.webhooks()
        webhook = disnake.utils.get(webhooks, name=webhook_name)
        if webhook:
            return webhook
        avatar_path = webhook_config.get("avatar")
        avatar_bytes = None
        if avatar_path:
            with open(avatar_path, "rb") as f:
                avatar_bytes = f.read()
        return await channel.create_webhook(name=webhook_name, avatar=avatar_bytes)
    except Exception as e:
        log.error(f"Failed to get or create webhook in {channel.name}: {e}")
        return None


async def get_webhook(channel, webhook_name):
    if not webhook_name: return None
    webhooks = await channel.webhooks()
    return disnake.utils.get(webhooks, name=webhook_name)


def parse_duration(duration_str: str) -> timedelta:
    total_seconds = 0
    pattern = r'(\d+)\s*([dhm])'
    matches = re.findall(pattern, duration_str.lower())
    if not matches:
        raise ValueError("Invalid duration format")
    for value, unit in matches:
        value = int(value)
        if unit == 'd':
            total_seconds += value * 86400
        elif unit == 'h':
            total_seconds += value * 3600
        elif unit == 'm':
            total_seconds += value * 60
    return timedelta(seconds=total_seconds)


async def find_offender_in_ticket(channel: disnake.TextChannel):
    try:
        message = await channel.history(limit=1, oldest_first=True).next()
    except (disnake.NoMoreItems, disnake.NotFound):
        log.warning(f"Could not find the initial message in ticket channel {channel.id}")
        return None, None
    if not message.embeds:
        return None, None

    embed = message.embeds[0]

    footer_text = embed.footer.text if embed.footer else ""
    metadata = {}
    for part in footer_text.split(";"):
        if ":" in part:
            key, value = part.split(":", 1)
            metadata[key.strip()] = value.strip()

    offender_tag = None
    for field in embed.fields:
        if field.name.lower() == "offender":
            offender_tag = field.value
            break

    opener_id = metadata.get("opener")

    if metadata.get("ticket_type") == "Appeal":
        return opener_id, metadata

    return offender_tag or opener_id, metadata


def has_permission(member, action, roles_config):
    base_perm = f"discord-{action}"
    ctrl_perm = f"{base_perm}-ctrl"
    for role in member.roles:
        role_id = role.id
        for role_data in roles_config["staff_roles"].values():
            if role_data["id"] == role_id and role_data.get("permissions"):
                permissions = [p.strip() for p in role_data["permissions"].split(",")]
                if base_perm in permissions or ctrl_perm in permissions:
                    return True
    return False


async def clear_user_messages(channel, member, days):
    if days <= 0:
        return 0
    deleted_count = 0
    try:
        start_time = datetime.utcnow() - timedelta(days=days)
        check = lambda msg: msg.author.id == member.id
        deleted_messages = await channel.purge(limit=None, after=start_time, check=check)
        deleted_count = len(deleted_messages)
        log.info(f"Purged {deleted_count} messages from {member.display_name} in channel {channel.name}.")
    except Exception as e:
        log.error(f"Could not purge messages for {member.display_name}: {e}")
    return deleted_count