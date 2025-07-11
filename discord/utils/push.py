import disnake
from disnake import Option, OptionType, TextInputStyle, HTTPException
from disnake.ui import TextInput, Modal

async def get_webhook(channel, webhook_name):
    webhooks = await channel.webhooks()
    for webhook in webhooks:
        if webhook.name == webhook_name:
            return webhook
    return None

def setup_slash_commands_push(bot, channels_config, roles_config):
    command_data = {}

    def has_push_permission(member, channel_name):
        for role in member.roles:
            role_id = role.id
            for role_data in roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("permissions"):
                    allowed_commands = [cmd.strip() for cmd in role_data["permissions"].split(",")]
                    if "push" in allowed_commands or f"push-{channel_name}" in allowed_commands:
                        return True
        return False

    @bot.slash_command(
        name="push",
        description="Update information in the selected channel.",
        options=[
            Option(
                name="channel",
                description="Select a channel to send the message to",
                required=True,
                choices=["🔄│updates", "📢│announcements","📌│server-info", "📜│rules", "🔄│обновления", "📢│новости", "📌│информация", "📜│правила"],
                type=OptionType.string
            ),
            Option(
                name="color",
                description="Select the embed color",
                required=True,
                choices=["blue", "red", "green", "yellow", "purple", "orange", "teal", "magenta", "light_grey", "default"],
                type=OptionType.string
            ),
            Option(
                name="image_url",
                description="Image URL (optional)",
                required=False,
                type=OptionType.string
            ),
            Option(
                name="image_file",
                description="Attach an image (optional)",
                required=False,
                type=OptionType.attachment
            )
        ]
    )
    async def push_command(
            inter: disnake.ApplicationCommandInteraction,
            channel: str,
            color: str,
            image_url: str = None,
            image_file: disnake.Attachment = None
    ):
        if not has_push_permission(inter.author, channel):
            await inter.response.send_message(
                "You don't have permission to push messages to this channel.",
                ephemeral=True
            )
            return

        components = [
            TextInput(
                label="Title",
                custom_id="title",
                style=TextInputStyle.short,
                max_length=100,
                value="Information"
            ),
            TextInput(
                label="Content",
                custom_id="description",
                style=TextInputStyle.paragraph,
                max_length=2000,
                value="Server information."
            )
        ]

        if image_url and image_file:
            return await inter.response.send_message(
                "Please provide either an image URL or attach a file, not both.",
                ephemeral=True
            )

        file_url = image_file.url if image_file else image_url

        command_data[inter.id] = {
            "channel": channel,
            "color": color,
            "image_url": file_url,
            "channels_config": channels_config
        }

        await inter.response.send_modal(
            modal=Modal(
                title="Create Informational Message",
                custom_id=f"info_modal_{inter.id}",
                components=components
            )
        )

    @bot.listen("on_modal_submit")
    async def on_modal_submit(inter: disnake.ModalInteraction):
        if not inter.custom_id.startswith("info_modal_"):
            return

        original_inter_id = int(inter.custom_id.split("_")[-1])
        data = command_data.get(original_inter_id)
        if not data:
            return await inter.response.send_message("Command data lost. Please try again.", ephemeral=True)

        del command_data[original_inter_id]

        channel = data["channel"]
        color_name = data["color"]
        image_url = data["image_url"]
        channels_config = data["channels_config"]

        title = inter.text_values["title"]
        description = inter.text_values["description"]

        channel_id = channels_config["channels"][channel]["id"]
        target_channel = inter.guild.get_channel(channel_id)

        if not target_channel:
            return await inter.response.send_message("Channel not found!", ephemeral=True)

        webhook_config = channels_config["channels"][channel].get("webhook", {})
        webhook_name = webhook_config.get("name")
        webhook = await get_webhook(target_channel, webhook_name)

        try:
            color_attr = color_name.lower()
            color_obj = getattr(disnake.Color, color_attr)()
        except AttributeError:
            color_obj = disnake.Color.default()

        embed = disnake.Embed(
            title=title,
            description=description,
            color=color_obj
        )
        embed.set_footer(
            text=f"{inter.author.display_name} | OmniCorp © 2025",
            icon_url=inter.author.avatar.url if inter.author.avatar else inter.author.default_avatar.url
        )
        if image_url:
            try:
                embed.set_image(url=image_url)
            except Exception:
                return await inter.response.send_message(
                    "The image URL is invalid or unsupported by Discord. Please check the link.",
                    ephemeral=True
                )

        try:
            await webhook.send(embed=embed)
            await inter.response.send_message("Message sent successfully!", ephemeral=True)
        except HTTPException as e:
            if "embeds.0.image.url" in str(e):
                await inter.response.send_message(
                    "Invalid image URL provided. Please check the link.",
                    ephemeral=True
                )
            else:
                await inter.response.send_message(
                    f"Error sending message: {e.text or str(e)}",
                    ephemeral=True
                )
        except Exception as e:
            await inter.response.send_message(
                f"Unexpected error: {str(e)}",
                ephemeral=True
            )