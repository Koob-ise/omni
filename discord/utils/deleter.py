import disnake

def setup_slash_commands_deleter(bot, roles_config):
    def has_clear_permission(member):
        for role in member.roles:
            role_id = role.id
            for role_data in roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("permissions"):
                    allowed_commands = [cmd.strip() for cmd in role_data["permissions"].split(",")]
                    if "clear" in allowed_commands:
                        return True
        return False

    @bot.slash_command(
        name="clear",
        description="Deletes messages (including the target one)",
        options=[
            disnake.Option(
                name="amount",
                description="Number of messages to delete (including target)",
                type=disnake.OptionType.integer,
                required=False,
                min_value=1,
                max_value=100
            )
        ]
    )
    async def clear(
            inter: disnake.ApplicationCommandInteraction,
            amount: int = None
    ):
        if not has_clear_permission(inter.author):
            await inter.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)

        if hasattr(inter, "target") and inter.target:
            target_msg = inter.target
            await target_msg.delete()
            deleted = await inter.channel.purge(after=target_msg, limit=amount)
            await inter.followup.send(f"🗑️ Deleted {len(deleted) + 1} messages (including target).", ephemeral=True)

        elif amount:
            deleted = await inter.channel.purge(limit=amount)
            await inter.followup.send(f"🗑️ Deleted {len(deleted)} messages.", ephemeral=True)

        else:
            await inter.followup.send("❌ Specify amount or use right-click → 'Delete this and following'.",
                                      ephemeral=True)

    @bot.message_command(name="Delete this and following")
    async def clear_include_message(
            inter: disnake.ApplicationCommandInteraction,
            message: disnake.Message
    ):
        if not has_clear_permission(inter.author):
            await inter.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)
        await message.delete()
        deleted = await inter.channel.purge(after=message)
        await inter.followup.send(f"🗑️ Deleted {len(deleted) + 1} messages (including this one).", ephemeral=True)