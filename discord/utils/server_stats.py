import disnake
from disnake.ext import tasks
import logging

logger = logging.getLogger(__name__)

class ServerStats:
    def __init__(self, bot, channels_config, guild_id):
        self.bot = bot
        self.voice_channels = channels_config.get("voice_channels", {})
        self.guild_id = guild_id
        self._task = None

    async def start(self):
        if self._task and not self._task.is_running():
            self._task.start()
            return

        @tasks.loop(minutes=5)
        async def update_stats():
            await self._update_all_channels()

        self._task = update_stats
        self._task.start()

    async def _update_all_channels(self):
        try:
            guild = self.bot.get_guild(self.guild_id)
            if not guild:
                logger.warning(f"Гильдия {self.guild_id} не найдена!")
                return

            for stat_name, channel_data in self.voice_channels.items():
                await self._update_single_channel(guild, stat_name, channel_data)

        except Exception as e:
            logger.error(f"Ошибка обновления: {e}", exc_info=True)

    async def _update_single_channel(self, guild, stat_name, channel_data):
        channel = guild.get_channel(channel_data["id"])
        if not channel or not isinstance(channel, disnake.VoiceChannel):
            return

        new_name = self._generate_name(guild, stat_name)
        if new_name and channel.name != new_name:
            await channel.edit(name=new_name)
            logger.info(f"Обновлён канал: {new_name}")

    def _generate_name(self, guild, stat_name):
        stats_map = {
            "All members": f"All members: {guild.member_count}",
            "Members": f"Members: {sum(not m.bot for m in guild.members)}",
            "Boosts": f"Boosts: {guild.premium_subscription_count}",
            "Boost tier": f"Boost tier: {guild.premium_tier}"
        }
        return stats_map.get(stat_name)

async def setup_server_stats(bot, channels_config, guild_id):
    stats = ServerStats(bot, channels_config, guild_id)
    await stats.start()