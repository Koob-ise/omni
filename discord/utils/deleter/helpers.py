import re
from datetime import datetime, timedelta
import disnake


def is_thread_creation_message(message: disnake.Message) -> bool:
    return message.type == disnake.MessageType.thread_created


def can_be_deleted(message: disnake.Message) -> bool:
    if is_thread_creation_message(message):
        return False

    if not message.embeds:
        return True

    for embed in message.embeds:
        if embed.url and ".gif" in embed.url.lower():
            return True
        if embed.image and embed.image.url and ".gif" in embed.image.url.lower():
            return True
        if embed.thumbnail and embed.thumbnail.url and ".gif" in embed.thumbnail.url.lower():
            return True

    return False


def parse_time_input(time_str: str):
    if time_str.isdigit():
        return int(time_str), "count"

    total_seconds = 0
    pattern = r'(\d+)\s*([dhm])'
    matches = re.findall(pattern, time_str.lower())

    if not matches:
        return None, "invalid"

    for value, unit in matches:
        value = int(value)
        if unit == 'd':
            total_seconds += value * 86400
        elif unit == 'h':
            total_seconds += value * 3600
        elif unit == 'm':
            total_seconds += value * 60

    return total_seconds, "time"


async def estimate_message_count(channel, seconds, member=None) -> int:
    try:
        now = datetime.utcnow()
        start_time = now - timedelta(seconds=seconds)
        count = 0
        limit = 500
        async for message in channel.history(after=start_time, limit=None):
            if member and message.author != member:
                continue
            if can_be_deleted(message):
                count += 1
            if count >= limit:
                break
        return min(count, limit)
    except disnake.HTTPException:
        return 50