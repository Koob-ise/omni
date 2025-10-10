import disnake
import json
import logging
from typing import Dict

log = logging.getLogger(__name__)


async def setup_webhooks(bot, config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        channels_config = json.load(f)

    webhooks: Dict[str, disnake.Webhook] = {}

    for channel_name, channel_data in channels_config["channels"].items():
        if "webhook" not in channel_data:
            continue

        webhook_config = channel_data["webhook"]
        webhook_name = webhook_config.get("name", "OmniCorp Bot")
        avatar_path = webhook_config.get("avatar")

        try:
            channel = bot.get_channel(channel_data["id"])
            if not channel:
                log.warning(f"Channel not found: {channel_name} ({channel_data['id']})")
                continue

            channel_webhooks = await channel.webhooks()

            webhook = next(
                (wh for wh in channel_webhooks if wh.name == webhook_name),
                None
            )

            avatar_bytes = None
            if avatar_path:
                try:
                    with open(avatar_path, "rb") as avatar_file:
                        avatar_bytes = avatar_file.read()
                except FileNotFoundError:
                    log.warning(f"Avatar file not found for {channel_name}: {avatar_path}")
                except Exception as e:
                    log.warning(f"Failed to load avatar for {channel_name}: {e}")

            if not webhook:
                log.info(f"Creating new webhook for {channel_name}")
                webhook = await channel.create_webhook(
                    name=webhook_name,
                    avatar=avatar_bytes
                )
                log.info(f"Created webhook: {webhook.name} ({webhook.url})")
            else:
                log.debug(f"Using existing webhook for {channel_name}: {webhook.name}")
                if avatar_bytes and not webhook.avatar:
                    try:
                        await webhook.edit(avatar=avatar_bytes)
                        log.info(f"Updated avatar for {channel_name}")
                    except Exception as e:
                        log.warning(f"Failed to update avatar for {channel_name}: {e}")

            webhooks[channel_name] = webhook
        except disnake.Forbidden:
            log.error(f"Missing permissions to manage webhooks in #{channel_name}")
        except Exception as e:
            log.error(f"Error processing webhook for {channel_name}: {str(e)}")