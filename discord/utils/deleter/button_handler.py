import disnake
from datetime import timedelta, datetime
from .helpers import can_be_deleted
from .confirmation import deletion_data


class ButtonHandler:
    def __init__(self, bot, permission_checker, channels_config: dict, prohibited_thread_parent_names: list):
        self.bot = bot
        self.permission_checker = permission_checker

        self.prohibited_parent_ids = set()
        if channels_config and prohibited_thread_parent_names:
            all_channels = channels_config.get("channels", {})
            for name in prohibited_thread_parent_names:
                if name in all_channels:
                    self.prohibited_parent_ids.add(all_channels[name]["id"])

        bot.listen("on_button_click")(self.on_button_click)

    async def _handle_delete_single(self, inter, data):
        message = data["message"]
        try:
            await message.delete()
            await inter.edit_original_response(content="✅ Сообщение успешно удалено!", view=None)
        except disnake.NotFound:
            await inter.edit_original_response(content="✅ Сообщение уже было удалено.", view=None)

    async def _handle_delete_embed(self, inter, data):
        message = data["message"]
        try:
            await message.edit(embeds=[])
            await inter.edit_original_response(content="✅ Вложения успешно удалены!", view=None)
        except disnake.NotFound:
            await inter.edit_original_response(content="✅ Сообщение уже было удалено.", view=None)

    async def _handle_delete_thread(self, inter, data):
        thread = data["thread"]

        if thread.parent_id in self.prohibited_parent_ids:
            await inter.edit_original_response(content="❌ Удаление веток в этом канале запрещено.", view=None)
            return

        if not (self.permission_checker.has_thread_delete_permission(
                inter.author) or thread.owner_id == inter.author.id):
            await inter.edit_original_response(content="❌ У вас больше нет прав на удаление этой ветки.",
                                               view=None)
            return

        if creation_message := data.get("creation_message"):
            try:
                await creation_message.delete()
            except disnake.NotFound:
                pass
        elif hasattr(self.bot, 'thread_manager'):
            await self.bot.thread_manager.delete_creation_message(thread)

        try:
            await thread.delete()
            await inter.edit_original_response(content="✅ Ветка успешно удалена!", view=None)
        except disnake.NotFound:
            await inter.edit_original_response(content="✅ Ветка уже была удалена.", view=None)

    async def _handle_clear(self, inter, data):
        if not self.permission_checker.has_clear_permission(inter.author):
            await inter.edit_original_response(content="❌ У вас больше нет прав на удаление сообщений.", view=None)
            return

        channel = data["channel"]
        member = data.get("member")
        check = lambda msg: (not member or msg.author == member) and can_be_deleted(msg)
        deleted_count = 0

        if data["input_type"] == "time":
            start_time = datetime.utcnow() - timedelta(seconds=data["time_seconds"])
            deleted_messages = await channel.purge(after=start_time, check=check, limit=500)
            deleted_count = len(deleted_messages)
        else:
            amount_to_delete = data["amount"]

            if not member:
                deleted_messages = await channel.purge(limit=amount_to_delete, check=check)
                deleted_count = len(deleted_messages)
            else:
                messages_to_delete = []
                async for message in channel.history(limit=2000):
                    if len(messages_to_delete) >= amount_to_delete:
                        break
                    if check(message):
                        messages_to_delete.append(message)

                if messages_to_delete:
                    try:
                        await channel.delete_messages(messages_to_delete)
                        deleted_count = len(messages_to_delete)
                    except disnake.HTTPException as e:
                        await inter.edit_original_response(content=f"❌ Произошла ошибка при удалении: {e}",
                                                           view=None)
                        return

        await inter.edit_original_response(content=f"✅ Успешно удалено {deleted_count} сообщений!", view=None)

    async def _handle_clear_after(self, inter, data):
        if not self.permission_checker.has_clear_permission(inter.author):
            await inter.edit_original_response(content="❌ У вас больше нет прав на удаление сообщений.", view=None)
            return

        channel = data["channel"]
        target_message = data["target_message"]
        deleted_count = 0

        deleted_messages = await channel.purge(after=target_message, check=can_be_deleted)
        deleted_count = len(deleted_messages)
        try:
            await target_message.delete()
            deleted_count += 1
        except disnake.NotFound:
            pass

        await inter.edit_original_response(content=f"✅ Успешно удалено {deleted_count} сообщений!", view=None)

    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        if custom_id.startswith("delete_user_thread_"):
            if hasattr(self.bot, 'thread_manager'):
                await self.bot.thread_manager.handle_thread_button_click(inter)
            return

        if not custom_id.startswith(("confirm_", "cancel_")):
            return

        try:
            action, inter_id_str = custom_id.split("_", 1)
            original_inter_id = int(inter_id_str)
        except ValueError:
            return

        data = deletion_data.get(original_inter_id)
        if not data or inter.author.id != data.get("author_id"):
            return

        original_inter_id = int(inter_id_str)

        try:
            if action == "cancel":
                await inter.response.edit_message(content="❌ Действие отменено.", view=None)
                return

            await inter.response.defer()

            action_handlers = {
                "delete_single": self._handle_delete_single,
                "delete_embed": self._handle_delete_embed,
                "delete_thread": self._handle_delete_thread,
                "clear": self._handle_clear,
                "clear_after": self._handle_clear_after,
            }

            handler = action_handlers.get(data.get("type"))
            if handler:
                await handler(inter, data)
            else:
                await inter.edit_original_response(content="❌ Неизвестный тип действия.", view=None)

        except disnake.HTTPException as e:
            try:
                await inter.edit_original_response(content=f"❌ Произошла ошибка: {e}", view=None)
            except disnake.HTTPException:
                pass
        finally:
            if original_inter_id in deletion_data:
                del deletion_data[original_inter_id]