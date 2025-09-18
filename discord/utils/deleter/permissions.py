import disnake

class PermissionChecker:
    def __init__(self, roles_config, channels_config):
        self.roles_config = roles_config
        self.channels_config = channels_config

    def has_delete_permission(self, member, channel_name):
        for role in member.roles:
            role_id = role.id
            for role_data in self.roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("permissions"):
                    allowed_commands = [cmd.strip() for cmd in role_data["permissions"].split(",")]
                    if "push" in allowed_commands or f"push-{channel_name}" in allowed_commands:
                        return True
        return False

    def has_clear_permission(self, member):
        for role in member.roles:
            role_id = role.id
            for role_data in self.roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("permissions"):
                    allowed_commands = [cmd.strip() for cmd in role_data["permissions"].split(",")]
                    if "clear" in allowed_commands:
                        return True
        return False

    def has_thread_delete_permission(self, member):
        for role in member.roles:
            role_id = role.id
            for role_data in self.roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("permissions"):
                    allowed_commands = [cmd.strip() for cmd in role_data["permissions"].split(",")]
                    if "delete_thread" in allowed_commands or "clear" in allowed_commands:
                        return True
        return False

    def has_forum_delete_permission(self, member):
        for role in member.roles:
            role_id = role.id
            for role_data in self.roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("permissions"):
                    allowed_commands = [cmd.strip() for cmd in role_data["permissions"].split(",")]
                    if "delete_forum" in allowed_commands or "clear" in allowed_commands:
                        return True
        return False

    def has_single_delete_permission(self, member, channel_id):
        channel_name = None
        for name, data in self.channels_config["channels"].items():
            if data["id"] == channel_id:
                channel_name = name
                break
        return self.has_clear_permission(member) or (channel_name and self.has_delete_permission(member, channel_name))

    def is_thread_owner(self, member, thread):
        return thread.owner_id == member.id