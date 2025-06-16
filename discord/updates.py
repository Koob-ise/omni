import disnake
from disnake import Embed, Webhook
import asyncio


async def check_updates_channel(bot: disnake.Client, channel_id: int, webhook_config: dict):
    """Проверка и создание сообщения в канале обновлений"""
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

    print(f"♻ Удалено {deleted} сообщений в канале обновлений")

    # Проверяем, есть ли уже наше сообщение
    has_message = False
    async for message in channel.history(limit=100):
        if (message.author == bot.user or
                (isinstance(message.author, disnake.User) and message.author.display_name == webhook_config.get("name", "Omnicorp Bot"))):
            if message.embeds and any("Обновления" in embed.title for embed in message.embeds):
                has_message = True
                break

    if has_message:
        print("ℹ Сообщение в канале обновлений уже существует")
        return

    # Создание нового сообщения
    try:
        webhook = await channel.create_webhook(
            name=webhook_config.get("name", "Omnicorp Bot"),
            reason=webhook_config.get("reason", "Updates message")
        )

        embed = Embed(
            title="Обновления",
            description="Обновления сервера OmniCorp.",
            color=disnake.Color.purple()
        )

        embed.set_thumbnail(url=webhook_config["logo"])
        embed.set_footer(text="OmniCorp © 2025")

        await webhook.send(
            embed=embed,
            username=webhook_config.get("name", "Omnicorp Bot"),
            avatar_url=webhook_config.get("avatar", None)
        )

        await webhook.delete()
        print("✅ Сообщение в канале обновлений отправлено")

    except Exception as e:
        print(f"⚠ Ошибка при работе с вебхуком в канале обновлений: {e}")