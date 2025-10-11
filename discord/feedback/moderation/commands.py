import disnake
from disnake.ext import commands
import logging
import re
from datetime import timedelta

from .constants import *
from .helpers import get_webhook_for_channel, get_webhook, parse_duration, find_offender_in_ticket, has_permission
from .views import ConfirmPunishmentView, ConfirmRevokeView
from .actions import apply_punishment, apply_revocation
from database.core import check_ticket_has_punishment
from database.tickets import get_ticket_db_id_by_channel

log = logging.getLogger(__name__)


def setup_moderation_commands(bot, channels_config, roles_config):
    bot.roles_config = roles_config
    moderation_roles = roles_config.get("moderation_roles", {})

    @bot.slash_command(
        name="punishment",
        description="Applies a moderation action to a user within a ticket."
    )
    async def punishment(
            inter: disnake.ApplicationCommandInteraction,
            action: str = commands.Param(choices=["ban", "mute", "kick", "voice-mute", "blacklist", "warn"]),
            duration: str = commands.Param(None, description="Duration (e.g.: 7d 3h 30m). Optional."),
            delete_days: int = commands.Param(0, ge=0, le=7, description="Delete user's messages (days)."),
            reason: str = commands.Param("No comment", description="Punishment reason")
    ):
        ticket_category_id = channels_config["categories"]["❓│Помощь / Support"]["id"]
        if inter.channel.category_id != ticket_category_id:
            return await inter.response.send_message("❌ This command only works in ticket channels!", ephemeral=True)

        user_tag, metadata = await find_offender_in_ticket(inter.channel)
        if not user_tag or not metadata:
            return await inter.response.send_message("❌ Could not find ticket information.", ephemeral=True)
        is_complaint = metadata.get("ticket_type") == "Complaint"
        if not is_complaint:
            return await inter.response.send_message("❌ This command only works in complaint tickets.", ephemeral=True)

        if not has_permission(inter.author, action, roles_config):
            return await inter.response.send_message("❌ Insufficient permissions for this action!", ephemeral=True)
        if action == "kick" and duration:
            return await inter.response.send_message("❌ Duration not allowed for kick!", ephemeral=True)

        clean_tag = re.sub(r'[<@>]', '', user_tag).strip()
        offender = None
        try:
            offender_id = int(clean_tag)
            offender = await inter.guild.fetch_member(offender_id)
        except (ValueError, disnake.NotFound):
            offender = inter.guild.get_member_named(clean_tag)
        if not offender:
            return await inter.response.send_message(f"❌ User `{user_tag}` not found on server!", ephemeral=True)

        duration_delta = None
        if duration:
            try:
                duration_delta = parse_duration(duration)
                if action in ["mute", "voice-mute"] and duration_delta > timedelta(days=28):
                    return await inter.response.send_message("❌ Max duration is 28 days!", ephemeral=True)
                if duration_delta < timedelta(minutes=1):
                    return await inter.response.send_message("❌ Min duration is 1 minute!", ephemeral=True)
            except ValueError as e:
                return await inter.response.send_message(f"❌ Format error: {e}\nExample: `7d 3h 30m`", ephemeral=True)

        ticket_db_id = get_ticket_db_id_by_channel(inter.channel.id)
        if not ticket_db_id:
            log.warning(f"Could not find ticket in DB for channel {inter.channel.id}. Punishment will not be linked.")

        if check_ticket_has_punishment(ticket_db_id):
            return await inter.response.send_message(
                "❌ A punishment has already been issued in this ticket. Only one punishment is allowed per ticket.",
                ephemeral=True
            )

        embed = disnake.Embed(title="🛑 Punishment Confirmation", color=disnake.Color.orange())
        embed.add_field(name="👤 Offender", value=offender.mention, inline=True)
        embed.add_field(name="⚖️ Action", value=action, inline=True)

        duration_text = "Permanent"
        if action != 'kick':
            if duration_delta:
                days, rem = divmod(duration_delta.total_seconds(), 86400)
                hours, rem = divmod(rem, 3600)
                minutes, _ = divmod(rem, 60)
                parts = []
                if days > 0: parts.append(f"{int(days)} days")
                if hours > 0: parts.append(f"{int(hours)} hrs")
                if minutes > 0: parts.append(f"{int(minutes)} min")
                duration_text = " ".join(parts) if parts else "Less than 1 min"
            else:
                default_days = {
                    "ban": DEFAULT_BAN_DAYS, "mute": DEFAULT_MUTE_DAYS,
                    "voice-mute": DEFAULT_VOICE_MUTE_DAYS, "blacklist": DEFAULT_BLACKLIST_DAYS,
                    "warn": DEFAULT_WARN_DURATION_DAYS
                }.get(action, "?")
                duration_text = f"Default ({default_days} days)"

        embed.add_field(name="⏱ Duration", value=duration_text, inline=True)
        if delete_days > 0:
            embed.add_field(name="🗑 Delete messages", value=f"Last {delete_days} days", inline=True)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text="Confirm or cancel punishment")

        view = ConfirmPunishmentView(
            offender=offender, action=action, duration_str=duration, reason=reason,
            delete_days=delete_days, moderation_roles=moderation_roles, ticket_db_id=ticket_db_id
        )

        webhook = await get_webhook_for_channel(inter.channel, channels_config, "❓│Помощь / Support")
        if not webhook:
            return await inter.response.send_message("❌ Could not get a webhook for this channel.", ephemeral=True)

        await inter.response.send_message("⏳ Waiting for punishment confirmation...", ephemeral=True)
        confirmation_msg = await webhook.send(embed=embed, view=view, wait=True)

        try:
            await view.wait()
            if view.confirmed:
                status, deleted_count = await apply_punishment(
                    inter, offender, action, duration_delta, reason,
                    delete_days, moderation_roles, view.ticket_db_id
                )

                punishments_channel_id = channels_config["channels"]["📌│punishments"]["id"]
                punishments_channel = inter.guild.get_channel(punishments_channel_id)
                punishments_webhook_config = channels_config["channels"]["📌│punishments"].get("webhook", {})
                punishments_webhook_name = punishments_webhook_config.get("name")
                log_sender = await get_webhook(punishments_channel, punishments_webhook_name) or punishments_channel

                response_message = ""

                if status == 'SUCCESS' or status == 'SUCCESS_WARN_AND_PUNISH':
                    if status == 'SUCCESS':
                        response_message = f"✅ {action.capitalize()} applied to {offender.mention}!"
                        if log_sender:
                            pass

                    elif status == 'SUCCESS_WARN_AND_PUNISH':
                        response_message = f"✅ Warn applied. User reached {WARNS_UNTIL_ACTION} warnings and has been automatically **{ACTION_ON_WARN_LIMIT}ed**."
                        if log_sender:
                            warn_log = disnake.Embed(title="⚠️ Warn Issued", color=disnake.Color.yellow(),
                                                     timestamp=disnake.utils.utcnow())
                            warn_log.add_field(name="👤 Offender", value=f"{offender.mention} ({offender.id})",
                                               inline=True)
                            warn_log.add_field(name="🛡 Moderator", value=inter.author.mention, inline=True)
                            warn_log.add_field(name="📝 Reason", value=reason, inline=False)
                            await log_sender.send(embed=warn_log)

                            auto_punish_log = disnake.Embed(title=f"🚨 Automatic {ACTION_ON_WARN_LIMIT.capitalize()}",
                                                            color=disnake.Color.red(), timestamp=disnake.utils.utcnow())
                            auto_punish_log.add_field(name="👤 Offender", value=f"{offender.mention} ({offender.id})",
                                                      inline=True)
                            auto_punish_log.add_field(name="🛡 Moderator", value=f"{bot.user.mention} (Auto)",
                                                      inline=True)
                            auto_punish_log.add_field(name="⚖️ Action", value=ACTION_ON_WARN_LIMIT, inline=True)
                            auto_end_time = disnake.utils.utcnow() + timedelta(seconds=ACTION_ON_WARN_DURATION_SECONDS)
                            auto_punish_log.add_field(name="⏱ Ends At", value=f"<t:{int(auto_end_time.timestamp())}:f>",
                                                      inline=True)
                            auto_punish_log.add_field(name="📝 Reason",
                                                      value=f"Reached {WARNS_UNTIL_ACTION} active warnings.",
                                                      inline=False)
                            await log_sender.send(embed=auto_punish_log)

                    if deleted_count > 0:
                        response_message += f" Deleted {deleted_count} of their messages."
                    await webhook.send(content=response_message)

                elif status == 'ALREADY_LONGER':
                    await webhook.send(
                        content=f"ℹ️ A longer or equal `{action}` punishment is already active. No action was taken.")
                else:
                    await webhook.send(content=f"❌ Failed to apply punishment to {offender.mention}!")
        except Exception as e:
            log.error(f"Error confirming punishment: {e}", exc_info=True)
            await webhook.send(content="❌ An error occurred while processing punishment.")
        finally:
            try:
                await confirmation_msg.delete()
            except disnake.NotFound:
                pass

    @bot.slash_command(
        name="revoke",
        description="Revokes an active punishment from a user in an appeal ticket."
    )
    async def revoke(
            inter: disnake.ApplicationCommandInteraction,
            action: str = commands.Param(choices=["ban", "mute", "voice-mute", "blacklist", "warn"]),
            reason: str = commands.Param("Appeal approved", description="The reason for revoking the punishment.")
    ):
        ticket_category_id = channels_config["categories"]["❓│Помощь / Support"]["id"]
        if inter.channel.category_id != ticket_category_id:
            return await inter.response.send_message("❌ This command only works in ticket channels!", ephemeral=True)

        user_id, metadata = await find_offender_in_ticket(inter.channel)
        if not user_id or not metadata:
            return await inter.response.send_message("❌ Could not find ticket information.", ephemeral=True)

        is_appeal = metadata.get("ticket_type") == "Appeal"
        if not is_appeal and action != "warn":
            return await inter.response.send_message("❌ This command can only be used in an appeal ticket.",
                                                     ephemeral=True)

        if not has_permission(inter.author, action, roles_config):
            return await inter.response.send_message("❌ You don't have permission to revoke this punishment.",
                                                     ephemeral=True)

        user_to_revoke = None
        try:
            user_to_revoke = await inter.guild.fetch_member(int(user_id))
        except (ValueError, disnake.NotFound):
            try:
                user_to_revoke = await bot.fetch_user(int(user_id))
            except (ValueError, disnake.NotFound):
                return await inter.response.send_message(f"❌ Could not find user with ID `{user_id}`.", ephemeral=True)

        embed = disnake.Embed(title="✅ Revocation Confirmation", color=disnake.Color.orange())
        embed.add_field(name="👤 User", value=f"{user_to_revoke.mention} ({user_to_revoke.id})", inline=False)
        embed.add_field(name="⚖️ Action to Revoke", value=action.capitalize(), inline=False)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text="Confirm or cancel the revocation")

        view = ConfirmRevokeView(
            user_to_revoke=user_to_revoke, action=action,
            reason=reason, moderation_roles=moderation_roles
        )

        webhook = await get_webhook_for_channel(inter.channel, channels_config, "❓│Помощь / Support")
        if not webhook:
            return await inter.response.send_message("❌ Could not get a webhook for this channel.", ephemeral=True)

        await inter.response.send_message("⏳ Waiting for revocation confirmation...", ephemeral=True)
        confirmation_msg = await webhook.send(embed=embed, view=view, wait=True)

        try:
            await view.wait()
            if view.confirmed:
                status = await apply_revocation(inter, user_to_revoke, action, reason, moderation_roles)

                if status == "SUCCESS":
                    punishments_channel_id = channels_config["channels"]["📌│punishments"]["id"]
                    log_channel = inter.guild.get_channel(punishments_channel_id)
                    if log_channel:
                        log_embed = disnake.Embed(title="✅ Punishment Revoked", color=disnake.Color.green(),
                                                  timestamp=disnake.utils.utcnow())
                        log_embed.add_field(name="👤 User", value=f"{user_to_revoke.mention} ({user_to_revoke.id})",
                                            inline=True)
                        log_embed.add_field(name="🛡 Moderator", value=inter.author.mention, inline=True)
                        log_embed.add_field(name="⚖️ Action Revoked", value=action.capitalize(), inline=True)
                        log_embed.add_field(name="📝 Reason", value=reason, inline=False)

                        punishments_webhook_config = channels_config["channels"]["📌│punishments"].get("webhook", {})
                        punishments_webhook_name = punishments_webhook_config.get("name")
                        log_webhook = await get_webhook(log_channel, punishments_webhook_name)
                        await (log_webhook or log_channel).send(embed=log_embed)

                    await webhook.send(f"✅ Successfully revoked `{action}` for {user_to_revoke.mention}.")

                elif status == "NO_PUNISHMENT":
                    await webhook.send(f"❌ Could not find an active `{action}` for {user_to_revoke.mention} to revoke.")

                else:
                    await webhook.send(f"❌ An error occurred while trying to revoke the punishment.")

        except Exception as e:
            log.error(f"Error during revocation process: {e}", exc_info=True)
            await webhook.send(content="❌ An unexpected error occurred.")
        finally:
            try:
                await confirmation_msg.delete()
            except disnake.NotFound:
                pass

    @bot.slash_command(name="invite", description="Invites a member to this ticket channel.")
    async def invite(
            inter: disnake.ApplicationCommandInteraction,
            member: disnake.Member = commands.Param(description="The member to invite to the ticket.")
    ):
        ticket_category_id = channels_config["categories"]["❓│Помощь / Support"]["id"]
        if inter.channel.category_id != ticket_category_id:
            return await inter.response.send_message("❌ This command can only be used in a ticket channel.",
                                                     ephemeral=True)

        if member.bot: return await inter.response.send_message("❌ You cannot invite bots to a ticket.", ephemeral=True)
        if member.id == inter.author.id: return await inter.response.send_message("❌ You cannot invite yourself.",
                                                                                  ephemeral=True)

        current_perms = inter.channel.permissions_for(member)
        if current_perms.read_messages:
            return await inter.response.send_message(f"❌ {member.mention} can already see this channel.",
                                                     ephemeral=True)

        try:
            await inter.channel.set_permissions(
                member, read_messages=True, send_messages=True,
                reason=f"Invited by {inter.author.display_name} ({inter.author.id})"
            )
            log.info(f"{inter.author.display_name} invited {member.display_name} to ticket {inter.channel.name}.")
        except Exception as e:
            log.error(f"Failed to grant permissions to {member.display_name} in {inter.channel.name}: {e}")
            return await inter.response.send_message("❌ An error occurred while trying to update channel permissions.",
                                                     ephemeral=True)

        webhook = await get_webhook_for_channel(inter.channel, channels_config, "❓│Помощь / Support")
        if webhook:
            await webhook.send(f"👋 {member.mention} has been invited to this ticket by {inter.author.mention}.")
        else:
            await inter.channel.send(f"👋 {member.mention} has been invited to this ticket by {inter.author.mention}.")

        await inter.response.send_message(f"✅ Successfully invited {member.mention} to this ticket.", ephemeral=True)