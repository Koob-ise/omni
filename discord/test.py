import disnake

def test(bot, roles_config):
    @bot.slash_command(name="test")
    async def test(inter: disnake.ApplicationCommandInteraction):
        has_permission = False

        for role in inter.author.roles:
            role_id = role.id
            for role_data in roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("choose"):
                    allowed_commands = [cmd.strip() for cmd in role_data["choose"].split(",")]
                    if "test" in allowed_commands:
                        has_permission = True
                        break
            if has_permission:
                break

        if not has_permission:
            await inter.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await inter.response.send_message('нормально все')
