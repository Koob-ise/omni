import disnake
from .permissions import PermissionChecker
from .commands import DeletionCommands
from .button_handler import ButtonHandler
from .thread_commands import ThreadCommands
from .thread_manager import ThreadManager


def setup_deletion_commands(bot: disnake.ext.commands.Bot, roles_config: dict, channels_config: dict):
    permission_checker = PermissionChecker(roles_config, channels_config)

    DeletionCommands(bot, permission_checker, channels_config)
    ButtonHandler(bot, permission_checker)
    ThreadCommands(bot, permission_checker)

    if not hasattr(bot, 'thread_handlers_registered'):
        bot.thread_manager = ThreadManager(bot, permission_checker)

        @bot.listen("on_thread_create")
        async def on_thread_create(thread: disnake.Thread):
            if isinstance(thread.parent, disnake.ForumChannel):
                await bot.thread_manager.handle_new_thread(thread)
            else:
                await bot.thread_manager.handle_new_thread(thread)

        bot.thread_handlers_registered = True