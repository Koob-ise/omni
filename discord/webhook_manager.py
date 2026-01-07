import disnake
import json
import logging
from typing import Dict, Tuple, Optional

log = logging.getLogger(__name__)


async def _get_or_create_webhook(bot, channel, webhook_config: dict, default_name: str) -> Optional[disnake.Webhook]:
    if not webhook_config:
        return None

    webhook_name = webhook_config.get("name", default_name)
    avatar_path = webhook_config.get("avatar")

    try:
        if not channel:
            return None

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
                log.warning(f"Avatar file not found for {webhook_name} in #{channel.name}: {avatar_path}")
            except Exception as e:
                log.warning(f"Failed to load avatar for {webhook_name} in #{channel.name}: {e}")

        if not webhook:
            log.info(f"Creating new webhook '{webhook_name}' in #{channel.name}")
            webhook = await channel.create_webhook(
                name=webhook_name,
                avatar=avatar_bytes
            )
            log.info(f"Created webhook: {webhook.name} ({webhook.id})")
        else:
            log.debug(f"Using existing webhook for '{webhook_name}' in #{channel.name}")
            # Обновляем аватар, если у существующего вебхука его нет, а в конфиге он есть
            if avatar_bytes and not webhook.avatar:
                try:
                    await webhook.edit(avatar=avatar_bytes)
                    log.info(f"Updated avatar for {webhook_name} in #{channel.name}")
                except Exception as e:
                    log.warning(f"Failed to update avatar for {webhook_name} in #{channel.name}: {e}")

        return webhook

    except disnake.Forbidden:
        log.error(f"Missing permissions to manage webhooks in #{channel.name} ({channel.id})")
    except Exception as e:
        log.error(f"Error processing webhook '{webhook_name}' for #{channel.name}: {str(e)}")

    return None


async def setup_webhooks(bot, channels_config: dict) -> Tuple[Dict[str, disnake.Webhook], Dict[int, disnake.Webhook]]:

    main_webhooks: Dict[str, disnake.Webhook] = {}
    deleter_webhooks: Dict[int, disnake.Webhook] = {}

    # Загружаем конфиг дефолтного вебхука для удаления
    default_deleter_config = channels_config.get("default_thread_deleter_webhook")

    for channel_name, channel_data in channels_config.get("channels", {}).items():
        channel_id = channel_data.get("id")
        if not channel_id:
            log.warning(f"Channel {channel_name} is missing 'id' in config.")
            continue

        channel = bot.get_channel(channel_id)
        if not channel:
            log.warning(f"Channel not found in bot's cache: {channel_name} ({channel_id})")
            continue

        # 1. Создаем/ищем ОСНОВНОЙ вебхук (как и раньше)
        main_webhook_config = channel_data.get("webhook")
        if main_webhook_config:
            main_wh = await _get_or_create_webhook(bot, channel, main_webhook_config, default_name="OmniCorp Bot")
            if main_wh:
                main_webhooks[channel_name] = main_wh

        # 2. Создаем/ищем ВЕБХУК ДЛЯ УДАЛЕНИЯ

        # Ищем конфиг-переопределение в самом канале
        deleter_config = channel_data.get("thread_deleter_webhook")

        # Если его нет, используем дефолтный конфиг
        if not deleter_config:
            deleter_config = default_deleter_config

        # Если конфиг (дефолтный или переопределенный) есть, создаем вебхук
        if deleter_config:
            deleter_wh = await _get_or_create_webhook(bot, channel, deleter_config, default_name="Thread Manager")
            if deleter_wh:
                # Сохраняем по ID канала, чтобы thread_manager мог его найти
                deleter_webhooks[channel_id] = deleter_wh

    return main_webhooks, deleter_webhooks