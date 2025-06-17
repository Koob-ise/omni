import disnake
from disnake import Option, OptionType, TextInputStyle
from disnake.ui import TextInput, Modal

def setup_slash_commands(bot, channels_config):
    command_data = {}

    @bot.slash_command(
        name="push",
        description="Posting news, server status, or update information in the selected channel.",
        options=[
            Option(
                name="channel",
                description="Select a channel to send the message to",
                required=True,
                choices=["🔄│updates", "🎮│server-status", "📢│announcements", "🔄│обновления", "🎮│статус-сервера",
                         "📢│новости"],
                type=OptionType.string
            ),
            Option(
                name="color",
                description="Select the embed color",
                required=True,
                choices=["Blue", "Red", "Green", "Yellow", "Purple", "Orange", "Teal", "Pink", "Gray", "Black"],
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
        color = data["color"]
        image_url = data["image_url"]
        channels_config = data["channels_config"]

        title = inter.text_values["title"]
        description = inter.text_values["description"]
        footer = inter.text_values.get("footer", "OmniCorp © 2025")

        channel_id = channels_config["channels"][channel]["id"]
        target_channel = inter.guild.get_channel(channel_id)

        if not target_channel:
            return await inter.response.send_message("Channel not found!", ephemeral=True)

        color_map = {
            "Blue": disnake.Color.blue(),
            "Red": disnake.Color.red(),
            "Green": disnake.Color.green(),
            "Yellow": disnake.Color.yellow(),
            "Purple": disnake.Color.purple(),
            "Orange": disnake.Color.orange(),
            "Teal": disnake.Color.teal(),
            "Pink": disnake.Color.magenta(),
            "Gray": disnake.Color.light_grey(),
            "Black": disnake.Color.default()
        }

        embed = disnake.Embed(
            title=title,
            description=description,
            color=color_map[color]
        )
        embed.set_footer(
            text=f"{inter.author.display_name} | OmniCorp © 2025",
            icon_url=inter.author.avatar.url if inter.author.avatar else inter.author.default_avatar.url
        )
        if image_url:
            embed.set_image(url=image_url)

        try:
            webhook = await target_channel.create_webhook(name="Omnicorp Bot")
            await webhook.send(
                embed=embed,
                username="Omnicorp Bot",
                avatar_url=None
            )
            await webhook.delete()
            await inter.response.send_message("Message sent successfully!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"Error sending message: {str(e)}", ephemeral=True)
