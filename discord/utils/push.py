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

    try:
        BOT_CHANNEL_ID = channels_config["channels"]["🤖│bot"]["id"]
    except KeyError:
        print("Error: '🤖│bot' channel not found in channels_config.")
        BOT_CHANNEL_ID = None

    def has_push_permission(member, channel_name):
        for role in member.roles:
            role_id = role.id
            for role_data in roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("permissions"):
                    allowed_commands = [cmd.strip() for cmd in role_data["permissions"].split(",")]
                    if "push" in allowed_commands or f"push-{channel_name}" in allowed_commands:
                        return True
        return False

    def get_config_key_by_channel_id(channel_id):
        for key, value in channels_config["channels"].items():
            if value["id"] == channel_id:
                return key
        return None

    @bot.slash_command(
        name="push",
        description="Create a new post in a channel.",
        options=[
            Option(
                name="channel",
                description="Select a channel",
                required=True,
                choices=["🔄│updates", "📢│announcements", "📌│server-info", "📜│rules", "🔄│обновления", "📢│новости",
                         "📌│информация", "📜│правила"],
                type=OptionType.string
            ),
            Option(
                name="color",
                description="Embed color",
                required=True,
                choices=["blue", "red", "green", "yellow", "purple", "orange", "teal", "magenta", "light_grey",
                         "default"],
                type=OptionType.string
            ),
            Option(
                name="signature",
                description="Show signature",
                required=True,
                type=OptionType.boolean
            ),
            Option(
                name="image_url",
                description="Image URL",
                required=False,
                type=OptionType.string
            ),
            Option(
                name="image_file",
                description="Attach image",
                required=False,
                type=OptionType.attachment
            ),
            Option(
                name="thread_name",
                description="Create a thread",
                required=False,
                type=OptionType.string
            ),
            Option(
                name="thread_embed_title",
                description="Title for the thread embed (optional)",
                required=False,
                type=OptionType.string
            ),
            Option(
                name="thread_message",
                description="Message content inside thread",
                required=False,
                type=OptionType.string
            ),
            Option(
                name="thread_as_embed",
                description="Send thread message as embed",
                required=False,
                type=OptionType.boolean
            )
        ]
    )
    async def push_command(
            inter: disnake.ApplicationCommandInteraction,
            channel: str,
            color: str,
            signature: bool,
            image_url: str = None,
            image_file: disnake.Attachment = None,
            thread_name: str = None,
            thread_embed_title: str = None,
            thread_message: str = None,
            thread_as_embed: bool = False
    ):
        if BOT_CHANNEL_ID and inter.channel_id != BOT_CHANNEL_ID:
            return await inter.response.send_message(
                f"This command can only be used in the <#{BOT_CHANNEL_ID}> channel.",
                ephemeral=True
            )

        if not has_push_permission(inter.author, channel):
            return await inter.response.send_message(
                "You don't have permission to push messages to this channel.",
                ephemeral=True
            )

        file_url = image_file.url if image_file else image_url
        if image_url and image_file:
            return await inter.response.send_message("Please use either URL or File, not both.", ephemeral=True)

        command_data[inter.id] = {
            "type": "create",
            "channel": channel,
            "color": color,
            "signature": signature,
            "image_url": file_url,
            "channels_config": channels_config,
            "thread_name": thread_name,
            "thread_embed_title": thread_embed_title,
            "thread_message": thread_message,
            "thread_as_embed": thread_as_embed
        }

        await inter.response.send_modal(
            modal=Modal(
                title="Create Message",
                custom_id=f"info_modal_{inter.id}",
                components=[
                    TextInput(label="Title", custom_id="title", required=False, max_length=100),
                    TextInput(label="Content", custom_id="description", style=TextInputStyle.paragraph, required=False,
                              max_length=2000)
                ]
            )
        )

    @bot.slash_command(
        name="push_reply",
        description="Send an embed reply into an existing thread as the webhook.",
        options=[
            Option(
                name="color",
                description="Embed color",
                required=True,
                choices=["blue", "red", "green", "yellow", "purple", "orange", "teal", "magenta", "light_grey",
                         "default"],
                type=OptionType.string
            ),
            Option(
                name="signature",
                description="Show signature",
                required=True,
                type=OptionType.boolean
            ),
            Option(
                name="thread_id",
                description="Thread ID (optional if used inside a thread)",
                required=False,
                type=OptionType.string
            ),
            Option(
                name="image_url",
                description="Image URL",
                required=False,
                type=OptionType.string
            ),
            Option(
                name="image_file",
                description="Attach image",
                required=False,
                type=OptionType.attachment
            )
        ]
    )
    async def push_reply_command(
            inter: disnake.ApplicationCommandInteraction,
            color: str,
            signature: bool,
            thread_id: str = None,
            image_url: str = None,
            image_file: disnake.Attachment = None
    ):
        target_thread = None
        if thread_id:
            try:
                target_thread = inter.guild.get_thread(int(thread_id))
                if not target_thread:
                    target_thread = await inter.guild.fetch_channel(int(thread_id))
            except Exception:
                return await inter.response.send_message("Invalid Thread ID.", ephemeral=True)
        elif isinstance(inter.channel, disnake.Thread):
            target_thread = inter.channel

        if not target_thread or not isinstance(target_thread, disnake.Thread):
            return await inter.response.send_message(
                "Command must be used inside a thread or you must provide a valid Thread ID.",
                ephemeral=True
            )

        parent_channel = target_thread.parent
        if not parent_channel:
            return await inter.response.send_message("Could not find parent channel for this thread.", ephemeral=True)

        config_key = get_config_key_by_channel_id(parent_channel.id)
        if not config_key:
            return await inter.response.send_message(
                f"The parent channel of this thread (<#{parent_channel.id}>) is not configured for push commands.",
                ephemeral=True
            )

        if not has_push_permission(inter.author, config_key):
            return await inter.response.send_message("You don't have permission to push to this channel.",
                                                     ephemeral=True)

        file_url = image_file.url if image_file else image_url
        if image_url and image_file:
            return await inter.response.send_message("Please use either URL or File, not both.", ephemeral=True)

        command_data[inter.id] = {
            "type": "reply",
            "thread_id": target_thread.id,
            "config_key": config_key,
            "color": color,
            "signature": signature,
            "image_url": file_url,
            "channels_config": channels_config
        }

        await inter.response.send_modal(
            modal=Modal(
                title="Reply to Thread",
                custom_id=f"info_modal_{inter.id}",
                components=[
                    TextInput(label="Title", custom_id="title", required=False, max_length=100),
                    TextInput(label="Content", custom_id="description", style=TextInputStyle.paragraph, required=False,
                              max_length=2000)
                ]
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

        action_type = data.get("type", "create")
        color_name = data["color"]
        signature_enabled = data["signature"]
        image_url = data["image_url"]
        channels_config = data["channels_config"]

        title = inter.text_values["title"]
        description = inter.text_values["description"]

        if not title and not description and not image_url:
            return await inter.response.send_message("Message cannot be empty.", ephemeral=True)

        try:
            color_attr = color_name.lower()
            color_obj = getattr(disnake.Color, color_attr)()
        except AttributeError:
            color_obj = disnake.Color.default()

        embed = disnake.Embed(color=color_obj)
        if title: embed.title = title
        if description: embed.description = description

        if signature_enabled:
            embed.set_footer(
                text=f"{inter.author.display_name} | OmniCorp © 2025",
                icon_url=inter.author.avatar.url if inter.author.avatar else inter.author.default_avatar.url
            )

        if image_url:
            try:
                embed.set_image(url=image_url)
            except Exception:
                return await inter.response.send_message("Invalid image URL.", ephemeral=True)

        if action_type == "create":
            channel_key = data["channel"]
            channel_id = channels_config["channels"][channel_key]["id"]
            target_channel = inter.guild.get_channel(channel_id)

            webhook_config = channels_config["channels"][channel_key].get("webhook", {})
            webhook = await get_webhook(target_channel, webhook_config.get("name"))

            if not webhook:
                return await inter.response.send_message("Webhook not found.", ephemeral=True)

            try:
                sent_message = await webhook.send(embed=embed, wait=True)
                response_msg = "Message sent!"

                thread_name = data.get("thread_name")
                thread_msg = data.get("thread_message")
                thread_embed_title = data.get("thread_embed_title")
                thread_as_embed = data.get("thread_as_embed")

                if thread_name:
                    try:
                        thread = await sent_message.create_thread(name=thread_name, auto_archive_duration=1440)
                        response_msg += f" Thread created."

                        if thread_msg or thread_embed_title:
                            if thread_as_embed or thread_embed_title:
                                t_embed = disnake.Embed(
                                    title=thread_embed_title,
                                    description=thread_msg,
                                    color=color_obj
                                )
                                await webhook.send(embed=t_embed, thread=thread)
                            else:
                                if thread_msg:
                                    await webhook.send(content=thread_msg, thread=thread)

                    except Exception as e:
                        response_msg += f" (Thread error: {e})"

                await inter.response.send_message(response_msg, ephemeral=True)

            except Exception as e:
                await inter.response.send_message(f"Error: {e}", ephemeral=True)

        elif action_type == "reply":
            thread_id = data["thread_id"]
            config_key = data["config_key"]

            target_thread = inter.guild.get_thread(thread_id)
            if not target_thread:
                target_thread = await inter.guild.fetch_channel(thread_id)

            webhook_config = channels_config["channels"][config_key].get("webhook", {})
            parent_channel = target_thread.parent or inter.guild.get_channel(
                channels_config["channels"][config_key]["id"])

            webhook = await get_webhook(parent_channel, webhook_config.get("name"))

            if not webhook:
                return await inter.response.send_message("Webhook not found for parent channel.", ephemeral=True)

            try:
                await webhook.send(embed=embed, thread=target_thread)
                await inter.response.send_message("Reply sent to thread successfully!", ephemeral=True)
            except Exception as e:
                await inter.response.send_message(f"Error sending reply: {e}", ephemeral=True)