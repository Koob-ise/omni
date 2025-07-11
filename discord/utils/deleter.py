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

    check_no_embeds = lambda message: not message.embeds

    @bot.slash_command(
        name="clear",
        description="Deletes messages, skipping those with embeds.",
        options=[
            disnake.Option(
                name="amount",
                description="The number of messages to delete.",
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
            await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)

        if hasattr(inter, "target") and inter.target:
            target_msg = inter.target

            if target_msg.embeds:
                await inter.followup.send("❌ Cannot delete the target message because it contains an embed.",
                                          ephemeral=True)
                return

            await target_msg.delete()
            deleted = await inter.channel.purge(after=target_msg, limit=amount, check=check_no_embeds)
            await inter.followup.send(f"🗑️ Deleted {len(deleted) + 1} messages (including the target).",
                                      ephemeral=True)

        elif amount:
            deleted = await inter.channel.purge(limit=amount, check=check_no_embeds)
            await inter.followup.send(f"🗑️ Deleted {len(deleted)} messages.", ephemeral=True)

        else:
            await inter.followup.send("❌ Please specify an amount or use the command by right-clicking on a message.",
                                      ephemeral=True)

    @bot.message_command(name="Delete this and following")
    async def clear_include_message(
            inter: disnake.ApplicationCommandInteraction,
            message: disnake.Message
    ):
        if not has_clear_permission(inter.author):
            await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        if message.embeds:
            await inter.response.send_message("❌ Cannot delete this message because it contains an embed.",
                                              ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)
        await message.delete()
        deleted = await inter.channel.purge(after=message, check=check_no_embeds)
        await inter.followup.send(f"🗑️ Deleted {len(deleted) + 1} messages (including the target).",
                                  ephemeral=True)