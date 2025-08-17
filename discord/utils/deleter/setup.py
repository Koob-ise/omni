from .permissions import PermissionChecker
from .commands import DeletionCommands
from .button_handler import ButtonHandler

def setup_deletion_commands(bot, roles_config, channels_config):
    permission_checker = PermissionChecker(roles_config, channels_config)
    DeletionCommands(bot, permission_checker, channels_config)
    ButtonHandler(bot, permission_checker)