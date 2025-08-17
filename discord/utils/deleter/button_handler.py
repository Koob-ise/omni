import disnake
import asyncio
from datetime import timedelta, datetime
from .helpers import can_be_deleted
from .confirmation import deletion_data


class ButtonHandler:
    def __init__(self, bot, permission_checker):
        self.bot = bot
        self.permission_checker = permission_checker

        @bot.listen("on_button_click")
        async def on_confirmation_button_click(inter: disnake.MessageInteraction):
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
                return
            if inter.author.id != data["author_id"]:
                try:
                    await inter.response.send_message("Only the original user can confirm this action.", ephemeral=True)
                except (disnake.errors.NotFound, disnake.errors.InteractionResponded):
                    pass
                return
            if action == "cancel":
                try:
                    await inter.response.edit_message(content="❌ Action cancelled.", view=None)
                except disnake.errors.NotFound:
                    pass
                if original_inter_id in deletion_data:
                    del deletion_data[original_inter_id]
                return
            try:
                if data["type"] == "delete_single":
                    if not self.permission_checker.has_single_delete_permission(inter.author,
                                                                                data["message"].channel.id):
                        try:
                            await inter.response.edit_message(
                                content="❌ You no longer have permission to delete messages in this channel.",
                                view=None)
                        except disnake.errors.NotFound:
                            pass
                        return
                    try:
                        await data["message"].delete()
                    except disnake.errors.NotFound:
                        pass
                    try:
                        await inter.response.edit_message(content="✅ Message deleted successfully!", view=None)
                    except disnake.errors.NotFound:
                        pass
                elif data["type"] == "delete_embed":
                    if not self.permission_checker.has_delete_permission(inter.author, data["channel_name"]):
                        try:
                            await inter.response.edit_message(
                                content="❌ You no longer have permission to delete embeds in this channel.", view=None)
                        except disnake.errors.NotFound:
                            pass
                        return
                    try:
                        await data["message"].delete()
                    except disnake.errors.NotFound:
                        pass
                    try:
                        await inter.response.edit_message(content="✅ Embed message deleted successfully!", view=None)
                    except disnake.errors.NotFound:
                        pass
                elif data["type"] == "delete_thread":
                    if not self.permission_checker.has_thread_delete_permission(inter.author):
                        try:
                            await inter.response.edit_message(
                                content="❌ You no longer have permission to delete threads.", view=None)
                        except disnake.errors.NotFound:
                            pass
                        return
                    thread = data["thread"]
                    try:
                        await thread.delete()
                    except disnake.errors.NotFound:
                        pass
                    try:
                        await inter.response.edit_message(content="✅ Thread deleted successfully!", view=None)
                    except disnake.errors.NotFound:
                        pass
                elif data["type"] == "delete_forum_post":
                    if not self.permission_checker.has_forum_delete_permission(inter.author):
                        try:
                            await inter.response.edit_message(
                                content="❌ You no longer have permission to delete forum posts.", view=None)
                        except disnake.errors.NotFound:
                            pass
                        return
                    forum_post = data["forum_post"]
                    try:
                        await forum_post.delete()
                    except disnake.errors.NotFound:
                        pass
                    try:
                        await inter.response.edit_message(content="✅ Forum post deleted successfully!", view=None)
                    except disnake.errors.NotFound:
                        pass
                elif data["type"] == "clear":
                    if not self.permission_checker.has_clear_permission(inter.author):
                        try:
                            await inter.response.edit_message(
                                content="❌ You no longer have permission to use this command.", view=None)
                        except disnake.errors.NotFound:
                            pass
                        return
                    member = data.get("member")
                    channel = data["channel"]
                    if member:
                        def check_func(m):
                            return m.author == member and can_be_deleted(m)
                    else:
                        check_func = can_be_deleted
                    if data.get("target_message"):
                        target_msg = data["target_message"]
                        try:
                            await target_msg.delete()
                        except disnake.errors.NotFound:
                            pass
                        deleted_after = []
                        try:
                            async for msg in channel.history(after=target_msg, limit=data["amount"]):
                                if check_func(msg):
                                    try:
                                        await msg.delete()
                                        deleted_after.append(msg)
                                        await asyncio.sleep(0.25)
                                    except disnake.errors.NotFound:
                                        continue
                        except disnake.errors.NotFound:
                            pass
                        total_deleted = len(deleted_after) + 1
                        try:
                            await inter.response.edit_message(
                                content=f"✅ Deleted {total_deleted} messages (including the target).", view=None)
                        except disnake.errors.NotFound:
                            pass
                    elif data["input_type"] == "time":
                        start_time = datetime.utcnow() - timedelta(seconds=data["time_seconds"])
                        deleted = []
                        try:
                            await inter.response.edit_message(content=f"⏳ Deleting messages from the last period...",
                                                              view=None)
                        except disnake.errors.NotFound:
                            pass
                        try:
                            async for msg in channel.history(after=start_time):
                                if check_func(msg):
                                    try:
                                        await msg.delete()
                                        deleted.append(msg)
                                        await asyncio.sleep(0.25)
                                    except disnake.errors.NotFound:
                                        continue
                        except disnake.errors.NotFound:
                            pass
                        try:
                            await inter.edit_original_message(
                                content=f"✅ Deleted {len(deleted)} messages from the last period.")
                        except disnake.errors.NotFound:
                            pass
                    else:
                        deleted = []
                        count_needed = data["amount"]
                        try:
                            async for msg in channel.history(limit=1000):
                                if len(deleted) >= count_needed:
                                    break
                                if check_func(msg):
                                    try:
                                        await msg.delete()
                                        deleted.append(msg)
                                        await asyncio.sleep(0.25)
                                    except disnake.errors.NotFound:
                                        continue
                        except disnake.errors.NotFound:
                            pass
                        try:
                            await inter.response.edit_message(content=f"✅ Deleted {len(deleted)} messages.", view=None)
                        except disnake.errors.NotFound:
                            pass
                elif data["type"] == "clear_after":
                    if not self.permission_checker.has_clear_permission(inter.author):
                        try:
                            await inter.response.edit_message(
                                content="❌ You no longer have permission to use this command.", view=None)
                        except disnake.errors.NotFound:
                            pass
                        return
                    target_msg = data["target_message"]
                    channel = data["channel"]
                    try:
                        await target_msg.delete()
                    except disnake.errors.NotFound:
                        pass
                    deleted_after = []
                    try:
                        async for msg in channel.history(after=target_msg):
                            if can_be_deleted(msg):
                                try:
                                    await msg.delete()
                                    deleted_after.append(msg)
                                    await asyncio.sleep(0.25)
                                except disnake.errors.NotFound:
                                    continue
                    except disnake.errors.NotFound:
                        pass
                    total_deleted = len(deleted_after) + 1
                    try:
                        await inter.response.edit_message(
                            content=f"✅ Deleted {total_deleted} messages (including the target).", view=None)
                    except disnake.errors.NotFound:
                        pass
            except Exception as e:
                try:
                    await inter.response.edit_message(content=f"❌ Error: {str(e)}", view=None)
                except (disnake.errors.NotFound, disnake.errors.InteractionResponded):
                    try:
                        await inter.followup.send(f"❌ Error during deletion: {str(e)}", ephemeral=True)
                    except:
                        pass
            finally:
                if original_inter_id in deletion_data:
                    del deletion_data[original_inter_id]