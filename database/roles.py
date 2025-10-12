from datetime import datetime, timedelta
import pytz
from .core import _add_action, resolve_user_ids


def _add_role_change(platform, role_changed_by_id, main_user_id, role, action_type, reason=None, duration_days=None):
    main_user_internal_id, performer_internal_id = resolve_user_ids(platform, main_user_id, role_changed_by_id)
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
        action_type=action_type,
        role=role,
        reason=reason,
        duration_seconds=duration_seconds,
        expires_at=expires_at
    )


def promotion(platform, role_changed_by_id, main_user_id, role, reason=None, duration_days=None):
    _add_role_change(platform, role_changed_by_id, main_user_id, role, "promotion", reason, duration_days)


def demotion(platform, role_changed_by_id, main_user_id, role, reason=None, duration_days=None):
    _add_role_change(platform, role_changed_by_id, main_user_id, role, "demotion", reason, duration_days)


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