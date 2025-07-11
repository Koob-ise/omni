import disnake
from disnake.ui import Button, View


def setup_delete_embed_command(bot, roles_config, channels_config):
    deletion_data = {}

    def has_delete_permission(member, channel_name):
        for role in member.roles:
            role_id = role.id
            for role_data in roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("permissions"):
                    allowed_commands = [cmd.strip() for cmd in role_data["permissions"].split(",")]
                    if "push" in allowed_commands or f"push-{channel_name}" in allowed_commands:
                        return True
        return False

    @bot.message_command(name="Delete Embed")
    async def delete_embed_context_menu(inter: disnake.ApplicationCommandInteraction, message: disnake.Message):
        if not message.embeds:
            await inter.response.send_message("This message doesn't contain any embeds.", ephemeral=True)
            return

        channel_name = None
        for name, data in channels_config["channels"].items():
            if data["id"] == message.channel.id:
                channel_name = name
                break

        if not channel_name:
            await inter.response.send_message("This channel is not configured for deletion.", ephemeral=True)
            return

        if not has_delete_permission(inter.author, channel_name):
            await inter.response.send_message(
                "You don't have permission to delete embeds in this channel.",
                ephemeral=True
            )
            return

        deletion_data[inter.id] = {
            "message": message,
            "channel_name": channel_name
        }

        view = View(timeout=60)
        confirm_button = Button(style=disnake.ButtonStyle.danger, label="Delete", custom_id=f"confirm_{inter.id}")
        cancel_button = Button(style=disnake.ButtonStyle.secondary, label="Cancel", custom_id=f"cancel_{inter.id}")

        view.add_item(confirm_button)
        view.add_item(cancel_button)

        await inter.response.send_message(
            "Are you sure you want to delete this embed message?",
            ephemeral=True,
            view=view
        )

    @bot.listen("on_button_click")
    async def on_delete_button_click(inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        if not custom_id.startswith(("confirm_", "cancel_")):
            return

        try:
            action, inter_id_str = custom_id.split("_", 1)
            original_inter_id = int(inter_id_str)
        except ValueError:
            return

        data = deletion_data.get(original_inter_id)
        if not data:
            return await inter.response.send_message("Command data lost. Please try again.", ephemeral=True)

        if action == "cancel":
            await inter.response.edit_message(content="Deletion cancelled.", view=None)
            if original_inter_id in deletion_data:
                del deletion_data[original_inter_id]
            return

        message = data["message"]
        channel_name = data["channel_name"]

        if not has_delete_permission(inter.author, channel_name):
            await inter.response.edit_message(
                content="You no longer have permission to delete embeds in this channel.",
                view=None
            )
            if original_inter_id in deletion_data:
                del deletion_data[original_inter_id]
            return

        try:
            await message.delete()
            await inter.response.edit_message(content="Embed message deleted successfully!", view=None)
        except Exception as e:
            await inter.response.edit_message(
                content=f"Failed to delete embed: {str(e)}",
                view=None
            )
        finally:
            if original_inter_id in deletion_data:
                del deletion_data[original_inter_id]