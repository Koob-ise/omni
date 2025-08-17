import disnake
from disnake import TextInputStyle
from disnake.ui import TextInput, Modal

async def get_webhook(channel, webhook_name):
    webhooks = await channel.webhooks()
    for webhook in webhooks:
        if webhook.name == webhook_name:
            return webhook
    return None

def setup_edit_embed_command(bot, roles_config, channels_config):
    editing_data = {}

    def has_edit_permission(member, channel_name):
        for role in member.roles:
            role_id = role.id
            for role_data in roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("permissions"):
                    allowed_commands = [cmd.strip() for cmd in role_data["permissions"].split(",")]
                    if "push" in allowed_commands or f"push-{channel_name}" in allowed_commands:
                        return True
        return False

    @bot.message_command(name="Edit Embed")
    async def edit_embed_context_menu(inter: disnake.ApplicationCommandInteraction, message: disnake.Message):
        if not message.embeds:
            await inter.response.send_message("This message doesn't contain any embeds.", ephemeral=True)
            return

        channel_name = None
        for name, data in channels_config["channels"].items():
            if data["id"] == message.channel.id:
                channel_name = name
                break

        if not channel_name:
            await inter.response.send_message("This channel is not configured for editing.", ephemeral=True)
            return

        if not has_edit_permission(inter.author, channel_name):
            await inter.response.send_message(
                "You don't have permission to edit embeds in this channel.",
                ephemeral=True
            )
            return

        channel_id = channels_config["channels"][channel_name]["id"]
        target_channel = inter.guild.get_channel(channel_id)
        if not target_channel:
            return await inter.response.send_message("Channel not found!", ephemeral=True)

        webhook_config = channels_config["channels"][channel_name].get("webhook", {})
        webhook_name = webhook_config.get("name")
        webhook = await get_webhook(target_channel, webhook_name)

        if not webhook:
            await inter.response.send_message("Webhook not found for this channel.", ephemeral=True)
            return

        embed = message.embeds[0]
        editing_data[inter.id] = {
            "message": message,
            "original_embed": embed,
            "channel_name": channel_name,
            "webhook": webhook
        }

        components = [
            TextInput(
                label="Title",
                custom_id="title",
                style=TextInputStyle.short,
                max_length=100,
                value=embed.title or "Information"
            ),
            TextInput(
                label="Content",
                custom_id="description",
                style=TextInputStyle.paragraph,
                max_length=2000,
                value=embed.description or "Server information."
            ),
            TextInput(
                label="Color (blue, red, green, etc.)",
                custom_id="color",
                style=TextInputStyle.short,
                max_length=20,
                value=str(embed.color) if embed.color else "default"
            )
        ]

        await inter.response.send_modal(
            modal=Modal(
                title="Edit Embed",
                custom_id=f"edit_modal_{inter.id}",
                components=components
            )
        )

    @bot.listen("on_modal_submit")
    async def on_edit_modal_submit(inter: disnake.ModalInteraction):
        if not inter.custom_id.startswith("edit_modal_"):
            return

        original_inter_id = int(inter.custom_id.split("_")[-1])
        data = editing_data.get(original_inter_id)
        if not data:
            return await inter.response.send_message("Command data lost. Please try again.", ephemeral=True)

        del editing_data[original_inter_id]

        message = data["message"]
        channel_name = data["channel_name"]
        original_embed = data["original_embed"]
        webhook = data["webhook"]

        title = inter.text_values["title"]
        description = inter.text_values["description"]
        color_name = inter.text_values["color"]

        if not has_edit_permission(inter.author, channel_name):
            return await inter.response.send_message(
                "You no longer have permission to edit embeds in this channel.",
                ephemeral=True
            )

        try:
            if color_name.isdigit():
                color_obj = disnake.Color(int(color_name))
            else:
                color_attr = color_name.lower()
                color_obj = getattr(disnake.Color, color_attr)()
        except (AttributeError, ValueError):
            color_obj = disnake.Color.default()

        new_embed = disnake.Embed(
            title=title,
            description=description,
            color=color_obj
        )

        if original_embed.fields:
            for field in original_embed.fields:
                new_embed.add_field(
                    name=field.name,
                    value=field.value,
                    inline=field.inline
                )

        if original_embed.footer:
            new_embed.set_footer(
                text=original_embed.footer.text,
                icon_url=original_embed.footer.icon_url
            )

        if original_embed.image:
            new_embed.set_image(url=original_embed.image.url)

        if original_embed.thumbnail:
            new_embed.set_thumbnail(url=original_embed.thumbnail.url)

        try:
            await webhook.edit_message(message.id, embed=new_embed)
            await inter.response.send_message("Embed edited successfully!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(
                f"Failed to edit embed: {str(e)}",
                ephemeral=True
            )