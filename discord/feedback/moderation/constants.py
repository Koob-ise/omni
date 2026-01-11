MINUTE = 60
HOUR = 3600
DAY = 86400

DEFAULT_WARN_DURATION_DAYS = 730
DEFAULT_BAN_DAYS = 7
DEFAULT_MUTE_DAYS = 1
DEFAULT_VOICE_MUTE_DAYS = 1
DEFAULT_BLACKLIST_DAYS = 600

DEFAULT_WARN_DURATION_SECONDS = DEFAULT_WARN_DURATION_DAYS * DAY
DEFAULT_BAN_SECONDS = DEFAULT_BAN_DAYS * DAY
DEFAULT_MUTE_SECONDS = DEFAULT_MUTE_DAYS * DAY
DEFAULT_VOICE_MUTE_SECONDS = DEFAULT_VOICE_MUTE_DAYS * DAY
DEFAULT_BLACKLIST_SECONDS = DEFAULT_BLACKLIST_DAYS * DAY

# Format: { warn_count: {"action": "action_name", "duration": seconds} }
WARN_THRESHOLDS = {
    3: {"action": "mute", "duration": 5 * MINUTE},
    4: {"action": "mute", "duration": 15 * MINUTE},
    5: {"action": "mute", "duration": 30 * MINUTE},
    6: {"action": "mute", "duration": 1 * HOUR},
    7: {"action": "mute", "duration": 3 * HOUR},
    8: {"action": "mute", "duration": 6 * HOUR},
    9: {"action": "mute", "duration": 6 * HOUR},
    10: {"action": "mute", "duration": 12 * HOUR},
    11: {"action": "mute", "duration": 1 * DAY},
    12: {"action": "mute", "duration": 3 * DAY},
    13: {"action": "mute", "duration": 7 * DAY},
    14: {"action": "mute", "duration": 14 * DAY},
    15: {"action": "ban", "duration": 14 * DAY},
    16: {"action": "ban", "duration": 30 * DAY},
    17: {"action": "ban", "duration": 60 * DAY},
    18: {"action": "ban", "duration": 90 * DAY},
    19: {"action": "ban", "duration": 180 * DAY},
    20: {"action": "ban", "duration": 365 * DAY},
    21: {"action": "ban", "duration": 365 * DAY},
    22: {"action": "ban", "duration": 365 * DAY},
    23: {"action": "ban", "duration": 365 * DAY},
    24: {"action": "ban", "duration": 365 * DAY},
    25: {"action": "blacklist", "duration": 3650 * DAY}
}