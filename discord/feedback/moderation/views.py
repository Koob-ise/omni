import disnake
from disnake.ui import View, Button

class ConfirmPunishmentView(View):
    def __init__(self, offender, action, duration_str, reason, delete_days, moderation_roles, ticket_db_id):
        super().__init__(timeout=60)
        self.offender = offender
        self.action = action
        self.duration_str = duration_str
        self.reason = reason
        self.delete_days = delete_days
        self.moderation_roles = moderation_roles
        self.confirmed = False
        self.ticket_db_id = ticket_db_id

    @disnake.ui.button(label="Confirm", style=disnake.ButtonStyle.green)
    async def confirm(self, button: Button, inter: disnake.MessageInteraction):
        if not self.check_control_permission(inter):
            await inter.response.send_message("? You don't have permission to confirm!", ephemeral=True)
            return
        self.confirmed = True
        button.disabled = True
        self.children[1].disabled = True
        embed = disnake.Embed(description="? Punishment confirmed.", color=disnake.Color.green())
        await inter.response.edit_message(embed=embed, view=None)
        self.stop()

    @disnake.ui.button(label="Cancel", style=disnake.ButtonStyle.red)
    async def cancel(self, button: Button, inter: disnake.MessageInteraction):
        if not self.check_control_permission(inter):
            await inter.response.send_message("? You don't have permission to cancel!", ephemeral=True)
            return
        button.disabled = True
        self.children[0].disabled = True
        embed = disnake.Embed(description="? Punishment canceled.", color=disnake.Color.red())
        await inter.response.edit_message(embed=embed, view=None)
        self.stop()

    def check_control_permission(self, inter):
        ctrl_perm = f"discord-{self.action}-ctrl"
        for role in inter.author.roles:
            role_id = role.id
            for role_data in inter.bot.roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("permissions"):
                    permissions = [p.strip() for p in role_data["permissions"].split(",")]
                    if ctrl_perm in permissions:
                        return True
        return False


class ConfirmRevokeView(View):
    def __init__(self, user_to_revoke, action, reason, moderation_roles):
        super().__init__(timeout=60)
        self.user_to_revoke = user_to_revoke
        self.action = action
        self.reason = reason
        self.moderation_roles = moderation_roles
        self.confirmed = False

    @disnake.ui.button(label="Confirm", style=disnake.ButtonStyle.green)
    async def confirm(self, button: Button, inter: disnake.MessageInteraction):
        if not self.check_control_permission(inter):
            await inter.response.send_message("? You don't have permission to confirm this revocation!", ephemeral=True)
            return
        self.confirmed = True
        button.disabled = True
        self.children[1].disabled = True
        embed = disnake.Embed(description="? Revocation confirmed.", color=disnake.Color.green())
        await inter.response.edit_message(embed=embed, view=None)
        self.stop()

    @disnake.ui.button(label="Cancel", style=disnake.ButtonStyle.red)
    async def cancel(self, button: Button, inter: disnake.MessageInteraction):
        if not self.check_control_permission(inter):
            await inter.response.send_message("? You don't have permission to cancel this revocation!", ephemeral=True)
            return
        button.disabled = True
        self.children[0].disabled = True
        embed = disnake.Embed(description="? Revocation canceled.", color=disnake.Color.red())
        await inter.response.edit_message(embed=embed, view=None)
        self.stop()

    def check_control_permission(self, inter):
        ctrl_perm = f"discord-{self.action}-ctrl"
        for role in inter.author.roles:
            role_id = role.id
            for role_data in inter.bot.roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("permissions"):
                    permissions = [p.strip() for p in role_data["permissions"].split(",")]
                    if ctrl_perm in permissions:
                        return True
        return False