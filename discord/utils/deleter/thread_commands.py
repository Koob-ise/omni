import disnake
from .permissions import PermissionChecker
from .confirmation import create_confirmation_view


class ThreadCommands:
    def __init__(self, bot: disnake.ext.commands.Bot, permission_checker: PermissionChecker):
        self.bot = bot
        self.permission_checker = permission_checker

        @bot.slash_command(
            name="delete_thread",
            description="Deletes the current thread or forum post."
        )
        async def delete_thread_cmd(inter: disnake.ApplicationCommandInteraction):
            if not isinstance(inter.channel, disnake.Thread):
                await inter.response.send_message(
                    "❌ This command can only be used in threads or forum posts.",
                    ephemeral=True
                )
                return

            is_owner = inter.channel.owner_id == inter.author.id
            is_moderator = self.permission_checker.has_thread_delete_permission(inter.author)

            if not is_owner and not is_moderator:
                await inter.response.send_message(
                    "❌ You do not have permission to delete this thread/post.",
                    ephemeral=True
                )
                return

            item_type = 'post' if isinstance(inter.channel.parent, disnake.ForumChannel) else 'thread'
            await create_confirmation_view(
                inter,
                f"⚠️ Are you sure you want to delete the {item_type} **{inter.channel.name}**?",
                action_type="delete_thread",
                thread=inter.channel
            )

        @bot.message_command(
            name="Delete Thread",
            description="Deletes a thread via its creation message."
        )
        async def delete_thread_from_message(inter: disnake.ApplicationCommandInteraction, message: disnake.Message):
            if message.type != disnake.MessageType.thread_created or not message.reference:
                await inter.response.send_message(
                    "❌ This command can only be used on a thread creation message.",
                    ephemeral=True
                )
                return

            try:
                thread = await inter.bot.fetch_channel(message.reference.channel_id)
            except disnake.NotFound:
                thread = None

            if not thread or not isinstance(thread, disnake.Thread):
                await inter.response.send_message(
                    "❌ Could not find the associated thread. It might have been deleted already.",
                    ephemeral=True
                )
                return

            is_owner = thread.owner_id == inter.author.id
            is_moderator = self.permission_checker.has_thread_delete_permission(inter.author)

            if not is_owner and not is_moderator:
                await inter.response.send_message(
                    "❌ You do not have permission to delete this thread.",
                    ephemeral=True
                )
                return

            await create_confirmation_view(
                inter,
                f"⚠️ Are you sure you want to delete the thread **{thread.name}** and its creation message?",
                action_type="delete_thread",
                thread=thread,
                creation_message=message
            )