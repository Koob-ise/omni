from datetime import datetime, timedelta
import pytz
from .core import _add_action, create_user


def _resolve_user_ids(platform, main_user_id, performer_id):
    user_params = {'discord_id': main_user_id} if platform == 'discord' else {'mindustry_id': main_user_id}
    main_user_internal_id = create_user(**user_params)
    performer_internal_id = create_user(discord_id=performer_id)
    return main_user_internal_id, performer_internal_id


def promotion(platform, role_changed_by_id, main_user_id, role, reason=None, duration_days=None):
    main_user_internal_id, performer_internal_id = _resolve_user_ids(platform, main_user_id, role_changed_by_id)

    gmt = pytz.timezone('GMT')
    expires_at = None
    duration_seconds = None
    if duration_days:
        duration_seconds = duration_days * 86400
        end_time = datetime.now(gmt) + timedelta(days=duration_days)
        expires_at = end_time.strftime('%Y-%m-%d %H:%M:%S')

    _add_action(
        user_id=main_user_internal_id,
        performed_by_id=performer_internal_id,
        action_type="promotion",
        role=role,
        reason=reason,
        duration_seconds=duration_seconds,
        expires_at=expires_at
    )


def demotion(platform, role_changed_by_id, main_user_id, role, reason=None, duration_days=None):
    main_user_internal_id, performer_internal_id = _resolve_user_ids(platform, main_user_id, role_changed_by_id)

    gmt = pytz.timezone('GMT')
    expires_at = None
    duration_seconds = None
    if duration_days:
        duration_seconds = duration_days * 86400
        end_time = datetime.now(gmt) + timedelta(days=duration_days)
        expires_at = end_time.strftime('%Y-%m-%d %H:%M:%S')

    _add_action(
        user_id=main_user_internal_id,
        performed_by_id=performer_internal_id,
        action_type="demotion",
        role=role,
        reason=reason,
        duration_seconds=duration_seconds,
        expires_at=expires_at
    )


def set_return_date_to_position(platform, main_user_id, performed_by_id, role, reason, days_to_add):
    demotion(
        platform=platform,
        role_changed_by_id=performed_by_id,
        main_user_id=main_user_id,
        role=role,
        reason=reason,
        duration_days=days_to_add
    )


def set_return_date_to_staff(platform, main_user_id, performed_by_id, role, reason, days_to_add):
    promotion(
        platform=platform,
        role_changed_by_id=performed_by_id,
        main_user_id=main_user_id,
        role=role,
        reason=reason,
        duration_days=days_to_add
    )