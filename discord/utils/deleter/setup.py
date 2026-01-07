import disnake
from .permissions import PermissionChecker
from .commands import DeletionCommands
from .thread_commands import ThreadCommands
from .thread_manager import ThreadManager
from .button_handler import ButtonHandler
from discord.webhook_manager import setup_webhooks


# ВАЖНО: функция стала `async`
async def setup_deleter(bot: disnake.ext.commands.Bot,
                        roles_config: dict,
                        channels_config: dict,
                        deleter_webhooks: dict):


    # --- ВОТ ГЛАВНОЕ ИЗМЕНЕНИЕ ---
    prohibited_channels = [
        "❓│Помощь / Support",
        "📌│closed-tickets"
    ]
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

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
        prohibited_thread_parent_names=prohibited_channels,
        deleter_webhooks=deleter_webhooks
    )

    bot.thread_manager = thread_manager

    ButtonHandler(
        bot=bot,
        permission_checker=permission_checker,
        channels_config=channels_config,
        prohibited_thread_parent_names=prohibited_channels
    )