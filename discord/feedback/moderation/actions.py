import disnake
import logging
from datetime import timedelta

from database.punishments import (
    add_ban, add_mute, add_kick, add_voice_mute, add_warn, blacklist,
    revoke_ban, revoke_mute, revoke_blacklist, revoke_voice_mute, revoke_warn
)
from database.core import create_user, count_active_warns, deactivate_all_warns, get_user_internal_id
from .constants import (
    DEFAULT_BAN_SECONDS, DEFAULT_MUTE_SECONDS, DEFAULT_VOICE_MUTE_SECONDS,
    DEFAULT_BLACKLIST_SECONDS, DEFAULT_WARN_DURATION_SECONDS, WARNS_UNTIL_ACTION,
    ACTION_ON_WARN_LIMIT, ACTION_ON_WARN_DURATION_SECONDS
)
from .helpers import clear_user_messages

log = logging.getLogger(__name__)


async def apply_punishment(inter, offender, action, duration_delta, reason, delete_days, moderation_roles,
                           ticket_db_id):
    deleted_count = 0
    if delete_days > 0:
        deleted_count = await clear_user_messages(inter.channel, offender, delete_days)
        log.info(f"Moderator {inter.author.display_name} deleted {deleted_count} messages for {offender.display_name}.")

    try:
        role_id = moderation_roles.get(action)
        role = inter.guild.get_role(role_id) if role_id else None

        status = 'FAILED'

        if action == "ban":
            if role: await offender.add_roles(role, reason=reason)
            duration_seconds = int(duration_delta.total_seconds()) if duration_delta else DEFAULT_BAN_SECONDS
            status = add_ban("discord", offender.id, inter.author.id, reason, duration_seconds, ticket_id=ticket_db_id)

        elif action == "mute":
            if role: await offender.add_roles(role, reason=reason)
            duration_seconds = int(duration_delta.total_seconds()) if duration_delta else DEFAULT_MUTE_SECONDS
            status = add_mute("discord", offender.id, inter.author.id, reason, duration_seconds, ticket_id=ticket_db_id)

        elif action == "voice-mute":
            if role: await offender.add_roles(role, reason=reason)
            duration_seconds = int(duration_delta.total_seconds()) if duration_delta else DEFAULT_VOICE_MUTE_SECONDS
            status = add_voice_mute("discord", offender.id, inter.author.id, reason, duration_seconds,
                                    ticket_id=ticket_db_id)

        elif action == "kick":
            await offender.kick(reason=reason)
            status = add_kick("discord", offender.id, inter.author.id, reason, ticket_id=ticket_db_id)

        elif action == "blacklist":
            await inter.guild.ban(offender, reason=reason, delete_message_days=0)
            duration_seconds = int(duration_delta.total_seconds()) if duration_delta else DEFAULT_BLACKLIST_SECONDS
            status = blacklist("discord", offender.id, inter.author.id, reason, duration_seconds,
                               ticket_id=ticket_db_id)

        elif action == "warn":
            duration_seconds = int(duration_delta.total_seconds()) if duration_delta else DEFAULT_WARN_DURATION_SECONDS

            user_internal_id = get_user_internal_id("discord", offender.id) or create_user(discord_id=offender.id)
            current_warns = count_active_warns(user_internal_id)

            add_warn("discord", offender.id, inter.author.id, reason, duration_seconds, ticket_id=ticket_db_id)

            if (current_warns + 1) >= WARNS_UNTIL_ACTION:
                deactivate_all_warns(user_internal_id)

                auto_action_reason = f"Automatic {ACTION_ON_WARN_LIMIT} for reaching {WARNS_UNTIL_ACTION} warnings."
                if ACTION_ON_WARN_LIMIT == "mute":
                    auto_action_role = inter.guild.get_role(moderation_roles.get("mute"))
                    if auto_action_role: await offender.add_roles(auto_action_role, reason=auto_action_reason)
                    add_mute("discord", offender.id, inter.author.id, auto_action_reason,
                             ACTION_ON_WARN_DURATION_SECONDS, ticket_id=ticket_db_id)

                elif ACTION_ON_WARN_LIMIT == "ban":
                    auto_action_role = inter.guild.get_role(moderation_roles.get("ban"))
                    if auto_action_role: await offender.add_roles(auto_action_role, reason=auto_action_reason)
                    add_ban("discord", offender.id, inter.author.id, auto_action_reason,
                            ACTION_ON_WARN_DURATION_SECONDS, ticket_id=ticket_db_id)

                return 'SUCCESS_WARN_AND_PUNISH', deleted_count
            else:
                return 'SUCCESS', deleted_count

        if status == 'ADDED':
            return 'SUCCESS', deleted_count
        elif status == 'SKIPPED':
            return 'ALREADY_LONGER', deleted_count

        return 'FAILED', deleted_count

    except Exception as e:
        log.error(f"Error applying punishment: {e}", exc_info=True)
        return 'FAILED', deleted_count


async def apply_revocation(inter, user_to_revoke, action, reason, moderation_roles):
    try:
        revoke_functions = {
            "ban": revoke_ban, "mute": revoke_mute, "voice-mute": revoke_voice_mute,
            "blacklist": revoke_blacklist, "warn": revoke_warn
        }
        success_db = revoke_functions[action](
            platform="discord", main_user_id=user_to_revoke.id,
            revoked_by_id=inter.author.id, reason=reason
        )
        if not success_db:
            return "NO_PUNISHMENT"

        if action == "blacklist":
            try:
                await inter.guild.unban(user_to_revoke, reason=f"Revoked by {inter.author.display_name}: {reason}")
            except disnake.NotFound:
                log.warning(f"Attempted to unban user {user_to_revoke.id} who was not banned (revoking blacklist).")
        else:
            if isinstance(user_to_revoke, disnake.Member):
                role_id = moderation_roles.get(action)
                if role_id:
                    role = inter.guild.get_role(role_id)
                    if role and role in user_to_revoke.roles:
                        await user_to_revoke.remove_roles(role,
                                                          reason=f"Punishment revoked by {inter.author.display_name}")
        return "SUCCESS"
    except Exception as e:
        log.error(f"Error applying revocation for {user_to_revoke.display_name}: {e}")
        return "FAILED"