import disnake
import asyncio
from .permissions import PermissionChecker
from .helpers import can_be_deleted, parse_time_input, estimate_message_count
from .confirmation import create_confirmation_view, deletion_data


class DeletionCommands:
    def __init__(self, bot, permission_checker, channels_config):
        self.bot = bot
        self.permission_checker = permission_checker
        self.channels_config = channels_config

        @bot.message_command(name="Delete this message")
        async def delete_single_message(inter: disnake.ApplicationCommandInteraction, message: disnake.Message):
            if not can_be_deleted(message):
                await inter.response.send_message("❌ Cannot delete this message because it contains non-GIF embeds.",
                                                  ephemeral=True)
                return
            if not self.permission_checker.has_single_delete_permission(inter.author, message.channel.id):
                await inter.response.send_message("❌ You don't have permission to delete messages in this channel.",
                                                  ephemeral=True)
                return
            await create_confirmation_view(inter, f"⚠️ Are you sure you want to delete this message?", "delete_single",
                                           message=message)

        @bot.message_command(name="Delete Embed")
        async def delete_embed_context_menu(inter: disnake.ApplicationCommandInteraction, message: disnake.Message):
            if not message.embeds:
                await inter.response.send_message("This message doesn't contain any embeds.", ephemeral=True)
                return
            channel_name = None
            for name, data in self.channels_config["channels"].items():
                if data["id"] == message.channel.id:
                    channel_name = name
                    break
            if not channel_name:
                await inter.response.send_message("This channel is not configured for deletion.", ephemeral=True)
                return
            if not self.permission_checker.has_delete_permission(inter.author, channel_name):
                await inter.response.send_message("You don't have permission to delete embeds in this channel.",
                                                  ephemeral=True)
                return
            await create_confirmation_view(inter, "⚠️ Are you sure you want to delete this embed message?",
                                           "delete_embed", message=message, channel_name=channel_name)

        @bot.message_command(name="Delete Thread")
        async def delete_thread_command(inter: disnake.ApplicationCommandInteraction, message: disnake.Message):
            if not message.thread:
                await inter.response.send_message("❌ This message is not the start of a thread.", ephemeral=True)
                return
            if not self.permission_checker.has_thread_delete_permission(inter.author):
                await inter.response.send_message("❌ You don't have permission to delete threads.", ephemeral=True)
                return
            await create_confirmation_view(inter,
                                           f"⚠️ Are you sure you want to delete the thread **{message.thread.name}** and all its messages?",
                                           "delete_thread", thread=message.thread)

        @bot.message_command(name="Delete Forum Post")
        async def delete_forum_post_command(inter: disnake.ApplicationCommandInteraction, message: disnake.Message):
            if not isinstance(message.channel, disnake.ForumChannel):
                await inter.response.send_message("❌ This command can only be used in forum channels.", ephemeral=True)
                return
            if not message.thread or message.thread.starter_message.id != message.id:
                await inter.response.send_message("❌ This message is not the start of a forum post.", ephemeral=True)
                return
            if not self.permission_checker.has_forum_delete_permission(inter.author):
                await inter.response.send_message("❌ You don't have permission to delete forum posts.", ephemeral=True)
                return
            await create_confirmation_view(inter,
                                           f"⚠️ Are you sure you want to delete the forum post **{message.thread.name}** and all its messages?",
                                           "delete_forum_post", forum_post=message.thread, starter_message=message)

        @bot.slash_command(
            name="clear",
            description="Delete messages by count or time (e.g. 50, 1d, 2h30m)",
            options=[
                disnake.Option(
                    name="input",
                    description="Number of messages or time period (e.g. 50, 1d, 2h30m)",
                    type=disnake.OptionType.string,
                    required=True,
                ),
                disnake.Option(
                    name="member",
                    description="Target member (only their messages will be deleted)",
                    type=disnake.OptionType.user,
                    required=False,
                )
            ]
        )
        async def clear(
                inter: disnake.ApplicationCommandInteraction,
                input: str,
                member: disnake.Member = None
        ):
            if not self.permission_checker.has_clear_permission(inter.author):
                await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
                return
            target_msg = getattr(inter, "target", None)
            value, input_type = parse_time_input(input)
            if input_type == "invalid":
                await inter.response.send_message(
                    "❌ Invalid format. Use a number (50) or time (1d, 2h30m). Examples: 50, 1d, 2h, 30m, 1d2h30m",
                    ephemeral=True)
                return
            if target_msg:
                if not can_be_deleted(target_msg):
                    await inter.response.send_message(
                        "❌ Cannot delete the target message because it contains non-GIF embeds.", ephemeral=True)
                    return
                if input_type == "time":
                    await inter.response.send_message(
                        "❌ Time format not supported with target message. Please use a number.", ephemeral=True)
                    return
                if member:
                    content = f"⚠️ Are you sure you want to delete this message and {value} messages after it by {member.mention}?"
                else:
                    content = f"⚠️ Are you sure you want to delete this message and {value} messages after it?"
                data = {"amount": value, "target_message": target_msg, "member": member}
            elif input_type == "time":
                estimated_count = await estimate_message_count(inter.channel, value, member)
                if member:
                    content = f"⚠️ Are you sure you want to delete approximately {estimated_count} messages from the last {input} by {member.mention}?"
                else:
                    content = f"⚠️ Are you sure you want to delete approximately {estimated_count} messages from the last {input}?"
                data = {"time_seconds": value, "estimated_count": estimated_count, "member": member}
            else:
                if member:
                    content = f"⚠️ Are you sure you want to delete {value} messages by {member.mention}?"
                else:
                    content = f"⚠️ Are you sure you want to delete {value} messages?"
                data = {"amount": value, "member": member}
            data["channel"] = inter.channel
            await create_confirmation_view(inter, content, "clear", input_type=input_type, **data)

        @bot.message_command(name="Delete this and following")
        async def clear_include_message(
                inter: disnake.ApplicationCommandInteraction,
                message: disnake.Message
        ):
            if not self.permission_checker.has_clear_permission(inter.author):
                await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
                return
            if not can_be_deleted(message):
                await inter.response.send_message("❌ Cannot delete this message because it contains non-GIF embeds.",
                                                  ephemeral=True)
                return
            await create_confirmation_view(inter,
                                           "⚠️ Are you sure you want to delete this message and all messages after it?",
                                           "clear_after", target_message=message, channel=inter.channel)