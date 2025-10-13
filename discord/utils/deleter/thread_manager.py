import disnake
from disnake.ui import Button, View
from .permissions import PermissionChecker
from .confirmation import create_confirmation_view


class ThreadManager:
    def __init__(self, bot: disnake.ext.commands.Bot, permission_checker: PermissionChecker, channels_config: dict,
                 prohibited_thread_parent_names: list):
        self.bot = bot
        self.permission_checker = permission_checker
        self.processed_threads = set()

        self.prohibited_parent_ids = set()
        if channels_config and prohibited_thread_parent_names:
            all_channels = channels_config.get("channels", {})
            for name in prohibited_thread_parent_names:
                if name in all_channels:
                    self.prohibited_parent_ids.add(all_channels[name]["id"])

    async def handle_new_thread(self, thread: disnake.Thread):
        if thread.id in self.processed_threads:
            return

        if thread.parent_id in self.prohibited_parent_ids:
            return

        self.processed_threads.add(thread.id)
        await self.send_delete_button(thread)

    async def send_delete_button(self, thread: disnake.Thread):
        try:
            view = View(timeout=None)
            view.add_item(
                Button(
                    style=disnake.ButtonStyle.danger,
                    label="Delete Thread",
                    custom_id=f"delete_user_thread_{thread.id}"
                )
            )
            await thread.send(
                "ℹ️ The thread creator and moderators can delete this thread using the button below.",
                view=view
            )
        except disnake.HTTPException as e:
            print(f"Error sending delete button to thread {thread.id}: {e}")

    async def delete_creation_message(self, thread: disnake.Thread):
        if isinstance(thread.parent, disnake.ForumChannel):
            return

        try:
            async for message in thread.parent.history(limit=100):
                if (message.type == disnake.MessageType.thread_created and
                        message.reference and
                        message.reference.channel_id == thread.id):
                    await message.delete()
                    break
        except disnake.HTTPException as e:
            print(f"Error deleting thread creation message for thread {thread.id}: {e}")

    async def handle_thread_button_click(self, inter: disnake.MessageInteraction):
        try:
            thread_id = int(inter.component.custom_id.split("_")[3])
            thread = self.bot.get_channel(thread_id)

            if not thread or not isinstance(thread, disnake.Thread):
                await inter.response.send_message("❌ Thread not found.", ephemeral=True)
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
                f"⚠️ Are you sure you want to delete the thread **{thread.name}**?",
                action_type="delete_thread",
                thread=thread
            )
        except (ValueError, IndexError) as e:
            print(f"Error parsing thread ID from custom_id '{inter.component.custom_id}': {e}")
            await inter.response.send_message("❌ An error occurred parsing the thread ID.", ephemeral=True)
        except disnake.HTTPException as e:
            print(f"Error during thread button click handling: {e}")
            await inter.response.send_message("❌ An unexpected error occurred.", ephemeral=True)