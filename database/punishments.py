from datetime import datetime, timedelta
import pytz
from .core import (
    _add_action, create_user, get_active_punishment, deactivate_action,
    revoke_action, get_user_internal_id, logger, resolve_user_ids, db_connection
)


def _handle_punishment_stacking(user_internal_id, action_type, new_end_time_dt):
    existing_punishment = get_active_punishment(user_internal_id, action_type)

    if existing_punishment:
        gmt = pytz.timezone('GMT')
        existing_end_time_str = existing_punishment['expires_at']

        if not existing_end_time_str:
            logger.info(
                f"Skipped adding {action_type} for user_id {user_internal_id} as a permanent one already exists.")
            return False

        existing_end_time_dt = gmt.localize(datetime.strptime(existing_end_time_str, '%Y-%m-%d %H:%M:%S'))

        if new_end_time_dt > existing_end_time_dt:
            deactivate_action(existing_punishment['id'])
            return True
        else:
            logger.info(
                f"Skipped adding {action_type} for user_id {user_internal_id} as a longer or equal punishment already exists.")
            return False

    return True


def add_punishment(platform, main_user_id, performer_id, reason, action_type, duration_seconds=None, ticket_id=None):
    main_user_internal_id, performer_internal_id = resolve_user_ids(platform, main_user_id, performer_id)

    if action_type == "kick":
        punishment_id = _add_action(main_user_internal_id, performer_internal_id, "kick", reason=reason, ticket_id=ticket_id)
        return 'ADDED', punishment_id

    if duration_seconds is None:
        raise ValueError(f"duration_seconds is required for '{action_type}'")

    gmt = pytz.timezone('GMT')
    end_time_dt = datetime.now(gmt) + timedelta(seconds=duration_seconds)
    expires_at_str = end_time_dt.strftime('%Y-%m-%d %H:%M:%S')

    if action_type == "warn":
        punishment_id = _add_action(main_user_internal_id, performer_internal_id, "warn", reason=reason,
                    duration_seconds=duration_seconds,
                    expires_at=expires_at_str, ticket_id=ticket_id)
        return 'ADDED', punishment_id

    stackable_actions = ["mute", "ban", "blacklist", "voice_mute"]
    if action_type in stackable_actions:
        if _handle_punishment_stacking(main_user_internal_id, action_type, end_time_dt):
            punishment_id = _add_action(main_user_internal_id, performer_internal_id, action_type, reason=reason,
                        duration_seconds=duration_seconds, expires_at=expires_at_str,
                        ticket_id=ticket_id)
            return 'ADDED', punishment_id
        return 'SKIPPED', None

    raise ValueError(f"Unsupported action type in add_punishment: {action_type}")


def revoke_punishment(platform, main_user_id, revoked_by_id, reason, action_type):
    revoker_internal_id = create_user(discord_id=revoked_by_id)
    user_internal_id = get_user_internal_id(platform, main_user_id)
    if not user_internal_id:
        return False

    active_punishment = get_active_punishment(user_internal_id, action_type)
    if active_punishment:
        return revoke_action(active_punishment['id'], revoker_internal_id, reason)

    return False


def update_punishment_log_id(punishment_id, log_message_id):
    if not punishment_id or not log_message_id:
        return False
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE user_actions SET log_message_id = ? WHERE id = ?",
                (str(log_message_id), punishment_id)
            )
            conn.commit()
            logger.info(f"Updated log_message_id for punishment {punishment_id} to {log_message_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to update log_message_id for punishment {punishment_id}: {e}")
        return False