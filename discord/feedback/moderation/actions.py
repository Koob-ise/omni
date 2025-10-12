import disnake
import logging
from datetime import timedelta

from database.punishments import add_punishment, revoke_punishment
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
        # Обработка 'warn' отдельно из-за сложной логики авто-наказания
        if action == "warn":
            duration_seconds = int(duration_delta.total_seconds()) if duration_delta else DEFAULT_WARN_DURATION_SECONDS
            user_internal_id = get_user_internal_id("discord", offender.id) or create_user(discord_id=offender.id)
            current_warns = count_active_warns(user_internal_id)

            add_punishment("discord", offender.id, inter.author.id, reason, "warn", duration_seconds,
                           ticket_id=ticket_db_id)

            if (current_warns + 1) >= WARNS_UNTIL_ACTION:
                deactivate_all_warns(user_internal_id)
                auto_action_reason = f"Автоматическое наказание ({ACTION_ON_WARN_LIMIT}) за {WARNS_UNTIL_ACTION} предупреждений."
                auto_action = ACTION_ON_WARN_LIMIT
                auto_action_role = inter.guild.get_role(moderation_roles.get(auto_action))

                if auto_action_role:
                    await offender.add_roles(auto_action_role, reason=auto_action_reason)

                add_punishment("discord", offender.id, inter.author.id, auto_action_reason, auto_action,
                               ACTION_ON_WARN_DURATION_SECONDS, ticket_id=ticket_db_id)

                return 'SUCCESS_WARN_AND_PUNISH', deleted_count
            else:
                return 'SUCCESS', deleted_count

        # Обработка всех остальных действий
        role_id = moderation_roles.get(action)
        role = inter.guild.get_role(role_id) if role_id else None
        status_db = 'FAILED_DB'

        default_durations = {
            "ban": DEFAULT_BAN_SECONDS, "mute": DEFAULT_MUTE_SECONDS,
            "voice-mute": DEFAULT_VOICE_MUTE_SECONDS, "blacklist": DEFAULT_BLACKLIST_SECONDS
        }
        duration_seconds = int(duration_delta.total_seconds()) if duration_delta else default_durations.get(action)

        # Применение эффектов в Discord и запись в БД
        if action == "kick":
            await offender.kick(reason=reason)
            status_db = add_punishment("discord", offender.id, inter.author.id, reason, "kick", ticket_id=ticket_db_id)
        elif action == "blacklist":
            await inter.guild.ban(offender, reason=reason, delete_message_days=0)
            status_db = add_punishment("discord", offender.id, inter.author.id, reason, "blacklist", duration_seconds,
                                       ticket_id=ticket_db_id)
        else:  # ban, mute, voice-mute
            if role:
                await offender.add_roles(role, reason=reason)
            status_db = add_punishment("discord", offender.id, inter.author.id, reason, action, duration_seconds,
                                       ticket_id=ticket_db_id)

        if status_db == 'ADDED':
            return 'SUCCESS', deleted_count
        elif status_db == 'SKIPPED':
            return 'ALREADY_LONGER', deleted_count

        return 'FAILED', deleted_count

    except Exception as e:
        log.error(f"Error applying punishment: {e}", exc_info=True)
        return 'FAILED', deleted_count


async def apply_revocation(inter, user_to_revoke, action, reason, moderation_roles):
    try:
        success_db = revoke_punishment(
            platform="discord", main_user_id=user_to_revoke.id,
            revoked_by_id=inter.author.id, reason=reason, action_type=action
        )
        if not success_db:
            return "NO_PUNISHMENT"

        # Применение эффектов в Discord
        if action == "blacklist":
            try:
                await inter.guild.unban(user_to_revoke, reason=f"Revoked by {inter.author.display_name}: {reason}")
            except disnake.NotFound:
                log.warning(f"Attempted to unban user {user_to_revoke.id} who was not banned.")
        elif action != "warn":  # Для ban, mute, voice-mute нужно снять роль
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