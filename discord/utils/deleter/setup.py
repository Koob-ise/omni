import disnake
from .permissions import PermissionChecker
from .commands import DeletionCommands
from .thread_commands import ThreadCommands
from .thread_manager import ThreadManager
from .button_handler import ButtonHandler


def setup_deleter(bot: disnake.ext.commands.Bot, roles_config: dict, channels_config: dict):
    prohibited_channels = ["??closed-tickets"]

    permission_checker = PermissionChecker(
        roles_config=roles_config,
        channels_config=channels_config
    )

    DeletionCommands(
        bot=bot,
        permission_checker=permission_checker,
        channels_config=channels_config
    )

    ThreadCommands(
        bot=bot,
        permission_checker=permission_checker
    )

    thread_manager = ThreadManager(
        bot=bot,
        permission_checker=permission_checker,
        channels_config=channels_config,
        prohibited_thread_parent_names=prohibited_channels
    )


    bot.thread_manager = thread_manager

    ButtonHandler(
        bot=bot,
        permission_checker=permission_checker,
        channels_config=channels_config,
        prohibited_thread_parent_names=prohibited_channels
    )