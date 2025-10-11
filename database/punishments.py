from datetime import datetime, timedelta
import pytz
from .core import (
    _add_action, create_user, get_active_punishment, deactivate_action,
    revoke_action, get_user_internal_id, logger
)


def _resolve_user_ids(platform, main_user_id, performer_id):
    user_params = {'discord_id': main_user_id} if platform == 'discord' else {'mindustry_id': main_user_id}
    main_user_internal_id = create_user(**user_params)
    performer_internal_id = create_user(discord_id=performer_id)
    return main_user_internal_id, performer_internal_id


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


def add_mute(platform, main_user_id, muted_by_id, reason, duration_seconds, ticket_id=None):
    main_user_internal_id, performer_internal_id = _resolve_user_ids(platform, main_user_id, muted_by_id)
    gmt = pytz.timezone('GMT')
    end_time_dt = datetime.now(gmt) + timedelta(seconds=duration_seconds)

    if _handle_punishment_stacking(main_user_internal_id, "mute", end_time_dt):
        _add_action(main_user_internal_id, performer_internal_id, "mute", reason=reason,
                    duration_seconds=duration_seconds, expires_at=end_time_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    ticket_id=ticket_id)
        return 'ADDED'
    return 'SKIPPED'


def add_ban(platform, main_user_id, banned_by_id, reason, duration_seconds, ticket_id=None):
    main_user_internal_id, performer_internal_id = _resolve_user_ids(platform, main_user_id, banned_by_id)
    gmt = pytz.timezone('GMT')
    end_time_dt = datetime.now(gmt) + timedelta(seconds=duration_seconds)

    if _handle_punishment_stacking(main_user_internal_id, "ban", end_time_dt):
        _add_action(main_user_internal_id, performer_internal_id, "ban", reason=reason,
                    duration_seconds=duration_seconds, expires_at=end_time_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    ticket_id=ticket_id)
        return 'ADDED'
    return 'SKIPPED'


def add_warn(platform, main_user_id, warned_by_id, reason, duration_seconds, ticket_id=None):
    main_user_internal_id, performer_internal_id = _resolve_user_ids(platform, main_user_id, warned_by_id)
    gmt = pytz.timezone('GMT')
    end_time_dt = datetime.now(gmt) + timedelta(seconds=duration_seconds)
    _add_action(main_user_internal_id, performer_internal_id, "warn", reason=reason, duration_seconds=duration_seconds,
                expires_at=end_time_dt.strftime('%Y-%m-%d %H:%M:%S'), ticket_id=ticket_id)
    return 'ADDED'


def add_kick(platform, main_user_id, kicked_by_id, reason, ticket_id=None):
    main_user_internal_id, performer_internal_id = _resolve_user_ids(platform, main_user_id, kicked_by_id)
    _add_action(main_user_internal_id, performer_internal_id, "kick", reason=reason, ticket_id=ticket_id)
    return 'ADDED'


def blacklist(platform, main_user_id, blacklisted_by_id, reason, duration_seconds, ticket_id=None):
    main_user_internal_id, performer_internal_id = _resolve_user_ids(platform, main_user_id, blacklisted_by_id)
    gmt = pytz.timezone('GMT')
    end_time_dt = datetime.now(gmt) + timedelta(seconds=duration_seconds)

    if _handle_punishment_stacking(main_user_internal_id, "blacklist", end_time_dt):
        _add_action(main_user_internal_id, performer_internal_id, "blacklist", reason=reason,
                    duration_seconds=duration_seconds, expires_at=end_time_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    ticket_id=ticket_id)
        return 'ADDED'
    return 'SKIPPED'


def add_voice_mute(platform, main_user_id, muted_by_id, reason, duration_seconds, ticket_id=None):
    main_user_internal_id, performer_internal_id = _resolve_user_ids(platform, main_user_id, muted_by_id)
    gmt = pytz.timezone('GMT')
    end_time_dt = datetime.now(gmt) + timedelta(seconds=duration_seconds)

    if _handle_punishment_stacking(main_user_internal_id, "voice_mute", end_time_dt):
        _add_action(main_user_internal_id, performer_internal_id, "voice_mute", reason=reason,
                    duration_seconds=duration_seconds, expires_at=end_time_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    ticket_id=ticket_id)
        return 'ADDED'
    return 'SKIPPED'



def revoke_mute(platform, main_user_id, revoked_by_id, reason):
    revoker_internal_id = create_user(discord_id=revoked_by_id)
    user_internal_id = get_user_internal_id(platform, main_user_id)
    if not user_internal_id: return False
    active_punishment = get_active_punishment(user_internal_id, "mute")
    if active_punishment:
        return revoke_action(active_punishment['id'], revoker_internal_id, reason)
    return False


def revoke_ban(platform, main_user_id, revoked_by_id, reason):
    revoker_internal_id = create_user(discord_id=revoked_by_id)
    user_internal_id = get_user_internal_id(platform, main_user_id)
    if not user_internal_id: return False
    active_punishment = get_active_punishment(user_internal_id, "ban")
    if active_punishment:
        return revoke_action(active_punishment['id'], revoker_internal_id, reason)
    return False


def revoke_blacklist(platform, main_user_id, revoked_by_id, reason):
    revoker_internal_id = create_user(discord_id=revoked_by_id)
    user_internal_id = get_user_internal_id(platform, main_user_id)
    if not user_internal_id: return False
    active_punishment = get_active_punishment(user_internal_id, "blacklist")
    if active_punishment:
        return revoke_action(active_punishment['id'], revoker_internal_id, reason)
    return False


def revoke_voice_mute(platform, main_user_id, revoked_by_id, reason):
    revoker_internal_id = create_user(discord_id=revoked_by_id)
    user_internal_id = get_user_internal_id(platform, main_user_id)
    if not user_internal_id: return False
    active_punishment = get_active_punishment(user_internal_id, "voice_mute")
    if active_punishment:
        return revoke_action(active_punishment['id'], revoker_internal_id, reason)
    return False


def revoke_warn(platform, main_user_id, revoked_by_id, reason):
    revoker_internal_id = create_user(discord_id=revoked_by_id)
    user_internal_id = get_user_internal_id(platform, main_user_id)
    if not user_internal_id: return False
    active_punishment = get_active_punishment(user_internal_id, "warn")
    if active_punishment:
        return revoke_action(active_punishment['id'], revoker_internal_id, reason)
    return False