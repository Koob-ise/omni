import disnake
from disnake.ext import commands
from disnake.ui import View, Button
from database.db import add_ban, add_mute, add_kick, add_voice_mute, blacklist
import logging
import re
import asyncio
from datetime import datetime, timedelta
from discord.utils.deleter.helpers import can_be_deleted

log = logging.getLogger(__name__)

DEFAULT_BAN_DURATION = 7
DEFAULT_MUTE_DURATION = 1
DEFAULT_VOICE_MUTE_DURATION = 1
DEFAULT_BLACKLIST_DURATION = 600


async def get_ticket_webhook(channel, config):
    """Получает или создает вебхук для тикет-канала."""
    webhook_config = config["categories"]["❓│Помощь / Support"]["webhook"]
    webhook_name = webhook_config.get("name")

    webhooks = await channel.webhooks()
    webhook = disnake.utils.get(webhooks, name=webhook_name)

    if webhook:
        return webhook

    try:
        avatar_path = webhook_config.get("avatar")
        avatar_bytes = None
        if avatar_path:
            with open(avatar_path, "rb") as f:
                avatar_bytes = f.read()
        return await channel.create_webhook(name=webhook_name, avatar=avatar_bytes)
    except Exception as e:
        log.error(f"Failed to create webhook in {channel.name}: {e}")
        return None


class ConfirmPunishmentView(View):
    def __init__(self, offender, action, duration_str, reason, delete_days, moderation_roles):
        super().__init__(timeout=60)
        self.offender = offender
        self.action = action
        self.duration_str = duration_str
        self.reason = reason
        self.delete_days = delete_days
        self.moderation_roles = moderation_roles
        self.confirmed = False

    @disnake.ui.button(label="Confirm", style=disnake.ButtonStyle.green)
    async def confirm(self, button: Button, inter: disnake.MessageInteraction):
        if not self.check_control_permission(inter):
            await inter.response.send_message("❌ You don't have permission to confirm!", ephemeral=True)
            return

        self.confirmed = True
        button.disabled = True
        self.children[1].disabled = True
        await inter.response.edit_message(content="✅ Punishment confirmed", view=self)
        self.stop()

    @disnake.ui.button(label="Cancel", style=disnake.ButtonStyle.red)
    async def cancel(self, button: Button, inter: disnake.MessageInteraction):
        if not self.check_control_permission(inter):
            await inter.response.send_message("❌ You don't have permission to cancel!", ephemeral=True)
            return

        button.disabled = True
        self.children[0].disabled = True
        await inter.response.edit_message(content="❌ Punishment canceled", view=self)
        self.stop()

    def check_control_permission(self, inter):
        ctrl_perm = f"discord-{self.action}-ctrl"

        for role in inter.author.roles:
            role_id = role.id
            for role_data in inter.bot.roles_config["staff_roles"].values():
                if role_data["id"] == role_id and role_data.get("permissions"):
                    permissions = [p.strip() for p in role_data["permissions"].split(",")]
                    if ctrl_perm in permissions:
                        return True
        return False


def parse_duration(duration_str: str) -> timedelta:
    total_seconds = 0
    pattern = r'(\d+)\s*([dhm])'
    matches = re.findall(pattern, duration_str.lower())

    if not matches:
        raise ValueError("Invalid duration format")

    for value, unit in matches:
        value = int(value)
        if unit == 'd':
            total_seconds += value * 86400
        elif unit == 'h':
            total_seconds += value * 3600
        elif unit == 'm':
            total_seconds += value * 60

    return timedelta(seconds=total_seconds)


async def find_offender_in_ticket(channel: disnake.TextChannel):
    try:
        message = await channel.history(limit=1, oldest_first=True).next()
    except (disnake.NoMoreItems, disnake.NotFound):
        log.warning(f"Could not find the initial message in ticket channel {channel.id}")
        return None

    if not message.embeds:
        return None

    embed = message.embeds[0]

    for field in embed.fields:
        if field.name == "offender":
            return field.value

    log.warning(f"Field 'offender' not found in the initial message of ticket {channel.id}")
    return None


def has_permission(member, action, roles_config):
    base_perm = f"discord-{action}"
    ctrl_perm = f"{base_perm}-ctrl"

    for role in member.roles:
        role_id = role.id
        for role_data in roles_config["staff_roles"].values():
            if role_data["id"] == role_id and role_data.get("permissions"):
                permissions = [p.strip() for p in role_data["permissions"].split(",")]
                if base_perm in permissions or ctrl_perm in permissions:
                    return True
    return False


async def clear_user_messages(channel, member, days):
    """Deletes messages from a specific member in a given channel within a timeframe."""
    if days <= 0:
        return 0
    deleted_count = 0
    try:
        start_time = datetime.utcnow() - timedelta(days=days)
        check = lambda msg: msg.author.id == member.id and can_be_deleted(msg)

        deleted_messages = await channel.purge(limit=None, after=start_time, check=check)
        deleted_count = len(deleted_messages)
        log.info(f"Purged {deleted_count} messages from {member.display_name} in channel {channel.name}.")
    except Exception as e:
        log.error(f"Could not purge messages for {member.display_name}: {e}")
    return deleted_count


async def apply_punishment(inter, offender, action, duration_delta, reason, delete_days, moderation_roles):
    deleted_count = 0
    if delete_days > 0:
        deleted_count = await clear_user_messages(inter.channel, offender, delete_days)
        log.info(
            f"Moderator {inter.author.display_name} requested deletion of {delete_days} days of messages for {offender.display_name}. Deleted {deleted_count} messages in ticket.")

    try:
        role_id = None
        if action == "mute":
            role_id = moderation_roles.get("mute")
        elif action == "voice-mute":
            role_id = moderation_roles.get("voice-mute")
        elif action == "ban":
            role_id = moderation_roles.get("ban")

        role = inter.guild.get_role(role_id) if role_id else None

        if action == "ban":
            if role:
                await offender.add_roles(role, reason=reason)
            ban_days = DEFAULT_BAN_DURATION
            if duration_delta:
                ban_days = duration_delta.days
            add_ban("discord", offender.id, inter.author.id, reason, ban_days)

        elif action == "mute":
            if role:
                await offender.add_roles(role, reason=reason)
            mute_days = DEFAULT_MUTE_DURATION
            if duration_delta:
                mute_days = duration_delta.days
            add_mute("discord", offender.id, inter.author.id, reason, mute_days)

        elif action == "voice-mute":
            if role:
                await offender.add_roles(role, reason=reason)
            voice_mute_days = DEFAULT_VOICE_MUTE_DURATION
            if duration_delta:
                voice_mute_days = duration_delta.days
            add_voice_mute("discord", offender.id, inter.author.id, reason, voice_mute_days)

        elif action == "kick":
            await offender.kick(reason=reason)
            add_kick("discord", offender.id, inter.author.id, reason)

        elif action == "blacklist":
            await inter.guild.ban(
                offender,
                reason=reason,
                delete_message_days=0
            )
            blacklist_days = DEFAULT_BLACKLIST_DURATION
            if duration_delta:
                blacklist_days = duration_delta.days
            blacklist("discord", offender.id, inter.author.id, reason, blacklist_days)

        return True, deleted_count
    except Exception as e:
        log.error(f"Error applying punishment: {e}")
        return False, deleted_count


def setup_moderation_commands(bot, channels_config, roles_config):
    bot.roles_config = roles_config
    moderation_roles = roles_config.get("moderation_roles", {})

    @bot.slash_command(
        name="punishment",
        description="Applies a moderation action to a user within a ticket."
    )
    async def punishment(
            inter: disnake.ApplicationCommandInteraction,
            action: str = commands.Param(choices=["ban", "mute", "kick", "voice-mute", "blacklist"]),
            duration: str = commands.Param(
                None,
                description="Duration (e.g.: 7d 3h 30m). Optional for all actions"
            ),
            delete_days: int = commands.Param(
                0,
                ge=0,
                le=30,
                description="Delete user's messages from last N days in this channel (optional).",
            ),
            reason: str = commands.Param("No comment", description="Punishment reason")
    ):
        ticket_category_id = channels_config["categories"]["❓│Помощь / Support"]["id"]
        if inter.channel.category_id != ticket_category_id:
            return await inter.response.send_message("❌ Command only available in report channels!", ephemeral=True)

        try:
            initial_message = await inter.channel.history(limit=1, oldest_first=True).next()
            if not initial_message.embeds:
                raise disnake.NotFound
        except (disnake.NoMoreItems, disnake.NotFound):
            return await inter.response.send_message(
                "❌ Could not find the initial ticket message with an embed.", ephemeral=True
            )
        embed = initial_message.embeds[0]

        platform_field = next((field for field in embed.fields if field.name.lower() in ["platform", "платформа"]),
                              None)
        footer_text = embed.footer.text if embed.footer else ""

        is_complaint = "ticket_type:Complaint" in footer_text
        is_discord = platform_field and platform_field.value.lower() == "discord"

        if not (is_complaint and is_discord):
            return await inter.response.send_message(
                "❌ This command can only be used in a Discord complaint ticket.",
                ephemeral=True
            )

        if not has_permission(inter.author, action, roles_config):
            return await inter.response.send_message("❌ Insufficient permissions for this action!", ephemeral=True)

        if action == "kick" and duration:
            return await inter.response.send_message(
                "❌ Duration not allowed for kick!",
                ephemeral=True
            )

        offender_tag = await find_offender_in_ticket(inter.channel)
        if not offender_tag:
            return await inter.response.send_message(
                "❌ Could not automatically find offender in ticket! "
                "Please specify tag manually: @username",
                ephemeral=True
            )

        clean_tag = re.sub(r'[<@>]', '', offender_tag).strip()

        offender = None
        try:
            offender_id = int(clean_tag)
            offender = await inter.guild.fetch_member(offender_id)
        except (ValueError, disnake.NotFound):
            offender = inter.guild.get_member_named(clean_tag)

        if not offender:
            return await inter.response.send_message(
                f"❌ User {offender_tag} not found on server!",
                ephemeral=True
            )

        duration_delta = None
        if duration:
            try:
                duration_delta = parse_duration(duration)

                if action in ["mute", "voice-mute"]:
                    if duration_delta > timedelta(days=28):
                        return await inter.response.send_message(
                            "❌ Maximum duration is 28 days!",
                            ephemeral=True
                        )
                    if duration_delta < timedelta(minutes=1):
                        return await inter.response.send_message(
                            "❌ Minimum duration is 1 minute!",
                            ephemeral=True
                        )

            except ValueError as e:
                return await inter.response.send_message(
                    f"❌ Duration format error: {e}\n"
                    "Correct format: `7d 3h 30m` (days, hours, minutes)\n"
                    "Examples: `3d`, `2h 30m`, `7d 12h`",
                    ephemeral=True
                )

        embed = disnake.Embed(
            title="🛑 Punishment Confirmation",
            color=disnake.Color.orange()
        )
        embed.add_field(name="👤 Offender", value=offender.mention, inline=True)
        embed.add_field(name="⚖️ Action", value=action, inline=True)

        duration_text = "Default"
        if duration_delta:
            days = duration_delta.days
            hours = duration_delta.seconds // 3600
            minutes = (duration_delta.seconds % 3600) // 60

            duration_parts = []
            if days: duration_parts.append(f"{days} days")
            if hours: duration_parts.append(f"{hours} hrs")
            if minutes: duration_parts.append(f"{minutes} min")

            duration_text = " ".join(duration_parts) if duration_parts else "Less than 1 min"
        elif action == "blacklist":
            duration_text = f"Default ({DEFAULT_BLACKLIST_DURATION} days)"
        elif action in ["ban", "mute", "voice-mute"]:
            default_days = {
                "ban": DEFAULT_BAN_DURATION,
                "mute": DEFAULT_MUTE_DURATION,
                "voice-mute": DEFAULT_VOICE_MUTE_DURATION
            }.get(action, "?")

            duration_text = f"Default ({default_days} days)"

        embed.add_field(name="⏱ Duration", value=duration_text, inline=True)

        if delete_days > 0:
            embed.add_field(
                name="🗑 Delete messages",
                value=f"Last {delete_days} days (in this channel)",
                inline=True
            )

        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text="Confirm or cancel punishment")

        view = ConfirmPunishmentView(
            offender=offender,
            action=action,
            duration_str=duration,
            reason=reason,
            delete_days=delete_days,
            moderation_roles=moderation_roles
        )

        webhook = await get_ticket_webhook(inter.channel, channels_config)
        if not webhook:
            return await inter.response.send_message("❌ Could not get a webhook for this channel.", ephemeral=True)

        await inter.response.send_message("⏳ Waiting for punishment confirmation...", ephemeral=True)
        confirmation_msg = await webhook.send(embed=embed, view=view, wait=True)

        try:
            await view.wait()
            if view.confirmed:
                success, deleted_count = await apply_punishment(
                    inter, offender, action, duration_delta, reason, delete_days, moderation_roles
                )

                if success:
                    punishments_channel_id = channels_config["channels"]["📌│punishments"]["id"]
                    channel = inter.guild.get_channel(punishments_channel_id)
                    if channel:
                        log_embed = disnake.Embed(
                            title="🚨 Punishment Applied",
                            color=disnake.Color.red(),
                            timestamp=disnake.utils.utcnow()
                        )
                        log_embed.add_field(name="👤 Offender", value=f"{offender.mention} ({offender.id})", inline=True)
                        log_embed.add_field(name="🛡 Moderator", value=inter.author.mention, inline=True)
                        log_embed.add_field(name="⚖️ Action", value=action, inline=True)

                        if duration_delta:
                            end_time = disnake.utils.utcnow() + duration_delta
                            duration_info = f"<t:{int(end_time.timestamp())}:f>"
                        else:
                            default_days = {
                                "ban": DEFAULT_BAN_DURATION,
                                "mute": DEFAULT_MUTE_DURATION,
                                "voice-mute": DEFAULT_VOICE_MUTE_DURATION,
                                "blacklist": DEFAULT_BLACKLIST_DURATION
                            }.get(action, "?")
                            duration_info = f"Default ({default_days} days)"

                        log_embed.add_field(name="⏱ Duration", value=duration_info, inline=True)

                        if delete_days > 0:
                            log_embed.add_field(
                                name="🗑 Messages deleted",
                                value=f"{deleted_count} from last {delete_days} days in ticket",
                                inline=True
                            )

                        log_embed.add_field(name="📝 Reason", value=reason, inline=False)

                        try:
                            punishments_webhook_config = channels_config["channels"]["📌│punishments"].get("webhook", {})
                            punishments_webhook_name = punishments_webhook_config.get("name")
                            log_webhook = await get_webhook(channel, punishments_webhook_name)
                            if log_webhook:
                                await log_webhook.send(embed=log_embed)
                            else:
                                await channel.send(embed=log_embed)
                        except Exception as e:
                            log.error(f"Error sending log: {e}")

                    response_message = f"✅ {action.capitalize()} applied to {offender.mention}!"
                    if deleted_count > 0:
                        response_message += f" Deleted {deleted_count} of their messages from this channel."
                    elif delete_days > 0:
                        response_message += " No messages from the user were found to delete in this channel."

                    await webhook.send(content=response_message)
                else:
                    await webhook.send(content=f"❌ Failed to apply punishment to {offender.mention}!")
        except Exception as e:
            log.error(f"Error confirming punishment: {e}")
            await webhook.send(content="❌ An error occurred while processing punishment")
        finally:
            try:
                await confirmation_msg.delete()
            except disnake.NotFound:
                pass

    @bot.slash_command(
        name="invite",
        description="Invites a member to this ticket channel."
    )
    async def invite(
            inter: disnake.ApplicationCommandInteraction,
            member: disnake.Member = commands.Param(description="The member to invite to the ticket.")
    ):
        """Invites a member to the ticket channel."""
        ticket_category_id = channels_config["categories"]["❓│Помощь / Support"]["id"]
        if inter.channel.category_id != ticket_category_id:
            return await inter.response.send_message(
                "❌ This command can only be used in a ticket channel.",
                ephemeral=True
            )

        if member.bot:
            return await inter.response.send_message(
                "❌ You cannot invite bots to a ticket.",
                ephemeral=True
            )

        if member.id == inter.author.id:
            return await inter.response.send_message(
                "❌ You cannot invite yourself.",
                ephemeral=True
            )

        current_perms = inter.channel.permissions_for(member)
        if current_perms.read_messages:
            return await inter.response.send_message(
                f"❌ {member.mention} can already see this channel.",
                ephemeral=True
            )

        try:
            await inter.channel.set_permissions(
                member,
                read_messages=True,
                send_messages=True,
                reason=f"Invited by {inter.author.display_name} ({inter.author.id})"
            )
            log.info(f"{inter.author.display_name} invited {member.display_name} to ticket {inter.channel.name}.")
        except Exception as e:
            log.error(f"Failed to grant permissions to {member.display_name} in {inter.channel.name}: {e}")
            return await inter.response.send_message(
                "❌ An error occurred while trying to update channel permissions.",
                ephemeral=True
            )

        webhook = await get_ticket_webhook(inter.channel, channels_config)
        if webhook:
            await webhook.send(f"👋 {member.mention} has been invited to this ticket by {inter.author.mention}.")
        else:
            await inter.channel.send(f"👋 {member.mention} has been invited to this ticket by {inter.author.mention}.")

        await inter.response.send_message(
            f"✅ Successfully invited {member.mention} to this ticket.",
            ephemeral=True
        )


async def get_webhook(channel, webhook_name):
    if not webhook_name: return None
    webhooks = await channel.webhooks()
    return disnake.utils.get(webhooks, name=webhook_name)