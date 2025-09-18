import disnake
from disnake.ext import commands
from .permissions import PermissionChecker
from .helpers import can_be_deleted, parse_time_input, estimate_message_count
from .confirmation import create_confirmation_view


class DeletionCommands:
    def __init__(self, bot: disnake.ext.commands.Bot, permission_checker: PermissionChecker, channels_config: dict):
        self.bot = bot
        self.permission_checker = permission_checker
        self.channels_config = channels_config

        @bot.message_command(name="Delete this message", description="Deletes a specific message.")
        async def delete_single_message(inter: disnake.ApplicationCommandInteraction, message: disnake.Message):
            if not can_be_deleted(message):
                await inter.response.send_message("❌ Cannot delete this message. System messages and non-GIF embeds are protected.", ephemeral=True)
                return
            if not self.permission_checker.has_single_delete_permission(inter.author, message.channel.id):
                await inter.response.send_message("❌ You don't have permission to delete messages in this channel.", ephemeral=True)
                return
            await create_confirmation_view(inter, "⚠️ Are you sure you want to delete this message?", "delete_single", message=message)

        @bot.message_command(name="Delete Embed", description="Removes all embeds from a specific message.")
        async def delete_embed_context_menu(inter: disnake.ApplicationCommandInteraction, message: disnake.Message):
            if not message.embeds:
                await inter.response.send_message("This message doesn't contain any embeds.", ephemeral=True)
                return

            channel_name = next((name for name, data in self.channels_config["channels"].items() if data["id"] == message.channel.id), None)

            if not channel_name:
                await inter.response.send_message("This channel is not configured for embed deletion.", ephemeral=True)
                return
            if not self.permission_checker.has_delete_permission(inter.author, channel_name):
                await inter.response.send_message("You don't have permission to delete embeds in this channel.", ephemeral=True)
                return
            await create_confirmation_view(inter, "⚠️ Are you sure you want to remove the embed from this message?", "delete_embed", message=message, channel_name=channel_name)

        @bot.slash_command(
            name="clear",
            description="Deletes messages by count or time period (e.g., 50, 1d, 2h30m)."
        )
        async def clear(
                inter: disnake.ApplicationCommandInteraction,
                amount: str = commands.Param(description="Number of messages or a time period (e.g., 50, 1d, 2h30m)."),
                member: disnake.Member = commands.Param(description="The user whose messages to delete (optional).", default=None)
        ):
            if not self.permission_checker.has_clear_permission(inter.author):
                await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
                return

            value, input_type = parse_time_input(amount)
            if input_type == "invalid":
                await inter.response.send_message("❌ Invalid format. Use a number (e.g., 50) or a time period (e.g., 1d, 2h30m).", ephemeral=True)
                return

            data = {"member": member, "channel": inter.channel}
            member_text = f" from {member.mention}" if member else " in this channel"

            if input_type == "time":
                estimated_count = await estimate_message_count(inter.channel, value, member)
                content = f"⚠️ Are you sure you want to delete ~{estimated_count} messages from the last {amount}{member_text}?"
                data.update({"time_seconds": value, "estimated_count": estimated_count})
            else:
                content = f"⚠️ Are you sure you want to delete the last {value} messages{member_text}?"
                data["amount"] = value

            await create_confirmation_view(inter, content, action_type="clear", input_type=input_type, **data)

        @bot.message_command(name="Delete messages after this", description="Deletes a message and all messages that follow it.")
        async def clear_after(inter: disnake.ApplicationCommandInteraction, message: disnake.Message):
            if not self.permission_checker.has_clear_permission(inter.author):
                await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
                return
            if not can_be_deleted(message):
                await inter.response.send_message("❌ Cannot use this as a starting point. System messages and non-GIF embeds are protected.", ephemeral=True)
                return
            await create_confirmation_view(inter, "⚠️ Are you sure you want to delete this message and all messages after it?", "clear_after", target_message=message, channel=inter.channel)