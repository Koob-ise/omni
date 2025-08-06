import sqlite3
from datetime import datetime, timedelta
import pytz
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

DB_PATH = '../database/database.db'

ALLOWED_UPDATE_FIELDS = {
    'return_date_to_position',
    'return_date_to_staff',
    'unban_time',
    'unmute_time'
}


@contextmanager
def db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL CHECK(platform IN ('discord', 'mindustry')),
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            return_date_to_position TEXT,
            return_date_to_staff TEXT,
            unban_time TEXT,
            unmute_time TEXT,
            UNIQUE(platform, user_id)
        )''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL CHECK(action_type IN ('promotion', 'demotion', 'mute', 'ban', 'warn', 'kick')),
            performed_by TEXT,
            role TEXT,
            reason TEXT,
            time TEXT NOT NULL,
            duration_days INTEGER,
            unwarn_time TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS id_mapping (
            discord_id TEXT NOT NULL,
            mindustry_id TEXT NOT NULL,
            PRIMARY KEY (discord_id, mindustry_id)
        )''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_user_id TEXT NOT NULL,
            ticket_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (discord_user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_platform_id ON users(platform, user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_actions_user ON user_actions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mapping_discord ON id_mapping(discord_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mapping_mindustry ON id_mapping(mindustry_id)')

        conn.commit()


def create_user(platform, user_id):
    if platform not in ["discord", "mindustry"]:
        raise ValueError("Неподдерживаемая платформа")

    gmt = pytz.timezone('GMT')
    current_time = datetime.now(gmt).strftime('%Y-%m-%d %H:%M:%S')

    with db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, created_at FROM users WHERE platform = ? AND user_id = ?",
            (platform, str(user_id)))

        existing_user = cursor.fetchone()
        if existing_user is None:
            cursor.execute(
                '''INSERT INTO users (platform, user_id, created_at) 
                VALUES (?, ?, ?)''',
                (platform, str(user_id), current_time))

            logger.info(f"Created new {platform} user: {user_id}")
            conn.commit()
            return cursor.lastrowid
        else:
            logger.debug(f"User {platform}/{user_id} already exists")
            return existing_user['id']


def update_user_data(platform, user_id, update_data):
    update_data = {
        k: v for k, v in update_data.items()
        if k in ALLOWED_UPDATE_FIELDS
    }

    if not update_data:
        logger.debug("No valid fields to update")
        return

    user_id_str = str(user_id)
    with db_connection() as conn:
        cursor = conn.cursor()

        user_db_id = create_user(platform, user_id)
        if user_db_id is None:
            logger.error(f"User {platform}/{user_id} not found and creation failed")
            return

        set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
        values = list(update_data.values())
        values.append(user_db_id)

        cursor.execute(
            f"UPDATE users SET {set_clause} WHERE id = ?",
            values)

        conn.commit()
        logger.debug(f"Updated user {platform}/{user_id}: {update_data}")


def map_ids(discord_id, mindustry_id):
    with db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''INSERT INTO id_mapping (discord_id, mindustry_id) 
                VALUES (?, ?)''',
                (str(discord_id), str(mindustry_id)))
            conn.commit()
            logger.info(f"Mapped Discord:{discord_id} to Mindustry:{mindustry_id}")
        except sqlite3.IntegrityError:
            logger.warning(f"Mapping already exists: Discord:{discord_id} to Mindustry:{mindustry_id}")


def create_ticket(discord_user_id, ticket_id):
    user_id_str = str(discord_user_id)
    gmt = pytz.timezone('GMT')
    current_time = datetime.now(gmt).strftime('%Y-%m-%d %H:%M:%S')

    with db_connection() as conn:
        cursor = conn.cursor()

        create_user("discord", discord_user_id)

        cursor.execute(
            '''INSERT INTO tickets (discord_user_id, ticket_id, created_at) 
            VALUES (?, ?, ?)''',
            (user_id_str, ticket_id, current_time))

        conn.commit()
        logger.info(f"Created ticket {ticket_id} for Discord user {discord_user_id}")


def get_related_id(user_id):
    user_id_str = str(user_id)
    with db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT mindustry_id FROM id_mapping WHERE discord_id = ?",
            (user_id_str,))
        result = cursor.fetchone()
        if result:
            return "mindustry", result[0]

        cursor.execute(
            "SELECT discord_id FROM id_mapping WHERE mindustry_id = ?",
            (user_id_str,))
        result = cursor.fetchone()
        if result:
            return "discord", result[0]

        return None, None


def get_full_user_data(platform, user_id):
    user_id_str = str(user_id)
    result = {
        'platform': platform,
        'id': user_id_str,
        'created_at': None,
        'profile_data': {
            'promotions': [],
            'demotions': [],
            'mutes': [],
            'bans': [],
            'warns': [],
            'kicks': [],  # Добавлено для киков
            'return_dates': {
                'to_position': None,
                'to_staff': None
            },
            'active_restrictions': {
                'unban_time': None,
                'unmute_time': None
            }
        },
        'actions_taken': {
            'promotions': [],
            'demotions': [],
            'bans': [],
            'mutes': [],
            'warns': [],
            'kicks': []  # Добавлено для киков
        },
        'linked_account': None
    }

    with db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            '''SELECT created_at, return_date_to_position, return_date_to_staff, 
                   unban_time, unmute_time 
            FROM users 
            WHERE platform = ? AND user_id = ?''',
            (platform, user_id_str))

        user_data = cursor.fetchone()
        if not user_data:
            return None

        result['created_at'] = user_data['created_at']
        result['profile_data']['return_dates']['to_position'] = user_data['return_date_to_position']
        result['profile_data']['return_dates']['to_staff'] = user_data['return_date_to_staff']
        result['profile_data']['active_restrictions']['unban_time'] = user_data['unban_time']
        result['profile_data']['active_restrictions']['unmute_time'] = user_data['unmute_time']

        cursor.execute(
            '''SELECT ua.action_type, ua.performed_by, ua.role, ua.reason, 
                   ua.time, ua.duration_days, ua.unwarn_time 
            FROM user_actions ua
            JOIN users u ON ua.user_id = u.id
            WHERE u.platform = ? AND u.user_id = ?''',
            (platform, user_id_str))

        for action in cursor.fetchall():
            action_data = {
                'performed_by': action['performed_by'],
                'role': action['role'],
                'reason': action['reason'],
                'time': action['time'],
                'duration_days': action['duration_days'],
                'unwarn_time': action['unwarn_time']
            }

            action_data = {k: v for k, v in action_data.items() if v is not None}

            action_type = action['action_type']
            result['profile_data'][f"{action_type}s"].append(action_data)

        cursor.execute(
            '''SELECT ua.action_type, u.user_id AS target_user, ua.role, ua.reason, 
                   ua.time, ua.duration_days, ua.unwarn_time 
            FROM user_actions ua
            JOIN users u ON ua.user_id = u.id
            WHERE ua.performed_by = ?''',
            (user_id_str,))

        for action in cursor.fetchall():
            action_data = {
                'target_user': action['target_user'],
                'role': action['role'],
                'reason': action['reason'],
                'time': action['time'],
                'duration_days': action['duration_days'],
                'unwarn_time': action['unwarn_time']
            }

            action_data = {k: v for k, v in action_data.items() if v is not None}

            action_type = action['action_type']
            result['actions_taken'][f"{action_type}s"].append(action_data)

        related_platform, related_id = get_related_id(user_id)
        if related_platform and related_id:
            result['linked_account'] = {
                'platform': related_platform,
                'id': related_id
            }

            cursor.execute(
                '''SELECT created_at, return_date_to_position, return_date_to_staff, 
                       unban_time, unmute_time 
                FROM users 
                WHERE platform = ? AND user_id = ?''',
                (related_platform, related_id))

            linked_user_data = cursor.fetchone()
            if linked_user_data:
                result['linked_account']['created_at'] = linked_user_data['created_at']
                result['linked_account']['profile_data'] = {
                    'promotions': [],
                    'demotions': [],
                    'mutes': [],
                    'bans': [],
                    'warns': [],
                    'kicks': []  # Добавлено для киков
                }

                cursor.execute(
                    '''SELECT ua.action_type, ua.performed_by, ua.role, ua.reason, 
                           ua.time, ua.duration_days, ua.unwarn_time 
                    FROM user_actions ua
                    JOIN users u ON ua.user_id = u.id
                    WHERE u.platform = ? AND u.user_id = ?''',
                    (related_platform, related_id))

                for action in cursor.fetchall():
                    action_data = {
                        'performed_by': action['performed_by'],
                        'role': action['role'],
                        'reason': action['reason'],
                        'time': action['time'],
                        'duration_days': action['duration_days'],
                        'unwarn_time': action['unwarn_time']
                    }

                    action_data = {k: v for k, v in action_data.items() if v is not None}

                    action_type = action['action_type']
                    result['linked_account']['profile_data'][f"{action_type}s"].append(action_data)

    return result


def _add_action(action_type, platform, main_user, performed_by, role=None, reason=None, duration_days=None,
                unwarn_time=None):
    user_id_str = str(main_user)
    performer_id_str = str(performed_by)
    gmt = pytz.timezone('GMT')
    current_time = datetime.now(gmt).strftime('%Y-%m-%d %H:%M:%S')

    main_user_id = create_user(platform, main_user)
    performer_user_id = create_user("discord", performed_by)

    if main_user_id is None or performer_user_id is None:
        logger.error(f"Failed to create users for action {action_type}")
        return

    with db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            '''INSERT INTO user_actions 
            (user_id, action_type, performed_by, role, reason, time, duration_days, unwarn_time) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (main_user_id, action_type, performer_id_str, role, reason, current_time, duration_days, unwarn_time))

        conn.commit()
        logger.info(f"Added {action_type} for {platform}/{user_id_str} by {performer_id_str}")


def promotion(platform, role_changed_by, main_user, role):
    _add_action(
        action_type="promotion",
        platform=platform,
        main_user=main_user,
        performed_by=role_changed_by,
        role=role
    )


def demotion(platform, role_changed_by, main_user, role):
    _add_action(
        action_type="demotion",
        platform=platform,
        main_user=main_user,
        performed_by=role_changed_by,
        role=role
    )


def set_return_date(platform, main_user, DAYS_TO_ADD):
    gmt = pytz.timezone('GMT')
    return_date = datetime.now(gmt) + timedelta(days=DAYS_TO_ADD)
    return_date_str = return_date.strftime('%Y-%m-%d %H:%M:%S')
    update_user_data(platform, main_user, {"return_date_to_position": return_date_str})


def set_staff_return_date(platform, main_user, DAYS_TO_ADD):
    gmt = pytz.timezone('GMT')
    staff_return_date = datetime.now(gmt) + timedelta(days=DAYS_TO_ADD)
    staff_return_date_str = staff_return_date.strftime('%Y-%m-%d %H:%M:%S')
    update_user_data(platform, main_user, {"return_date_to_staff": staff_return_date_str})


def add_mute(platform, main_user, muted_by, reason, mute_days):
    gmt = pytz.timezone('GMT')

    new_unmute = datetime.now(gmt) + timedelta(days=mute_days)
    new_unmute_str = new_unmute.strftime('%Y-%m-%d %H:%M:%S')

    current_unmute = None
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT unmute_time FROM users WHERE platform = ? AND user_id = ?",
            (platform, str(main_user)))
        row = cursor.fetchone()
        if row and row['unmute_time']:
            naive = datetime.strptime(row['unmute_time'], '%Y-%m-%d %H:%M:%S')
            current_unmute = gmt.localize(naive)

    if current_unmute and current_unmute > new_unmute:
        unmute_to_set = current_unmute.strftime('%Y-%m-%d %H:%M:%S')
    else:
        unmute_to_set = new_unmute_str

    _add_action(
        action_type="mute",
        platform=platform,
        main_user=main_user,
        performed_by=muted_by,
        reason=reason,
        duration_days=mute_days
    )
    update_user_data(platform, main_user, {"unmute_time": unmute_to_set})


def add_ban(platform, main_user, banned_by, reason, ban_days):
    gmt = pytz.timezone('GMT')

    new_unban = datetime.now(gmt) + timedelta(days=ban_days)
    new_unban_str = new_unban.strftime('%Y-%m-%d %H:%M:%S')

    current_unban = None
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT unban_time FROM users WHERE platform = ? AND user_id = ?",
            (platform, str(main_user)))
        row = cursor.fetchone()
        if row and row['unban_time']:
            naive = datetime.strptime(row['unban_time'], '%Y-%m-%d %H:%M:%S')
            current_unban = gmt.localize(naive)

    if current_unban and current_unban > new_unban:
        unban_to_set = current_unban.strftime('%Y-%m-%d %H:%M:%S')
    else:
        unban_to_set = new_unban_str

    _add_action(
        action_type="ban",
        platform=platform,
        main_user=main_user,
        performed_by=banned_by,
        reason=reason,
        duration_days=ban_days
    )
    update_user_data(platform, main_user, {"unban_time": unban_to_set})


def add_warn(platform, main_user, warned_by, reason, warn_days):
    gmt = pytz.timezone('GMT')
    unwarn_time = datetime.now(gmt) + timedelta(days=warn_days)
    unwarn_time_str = unwarn_time.strftime('%Y-%m-%d %H:%M:%S')

    _add_action(
        action_type="warn",
        platform=platform,
        main_user=main_user,
        performed_by=warned_by,
        reason=reason,
        duration_days=warn_days,
        unwarn_time=unwarn_time_str
    )


def add_kick(platform, main_user, kicked_by, reason):
    _add_action(
        action_type="kick",
        platform=platform,
        main_user=main_user,
        performed_by=kicked_by,
        reason=reason
    )


if __name__ == "__main__":
    init_db()

    create_user("discord", "123456789")
    create_user("mindustry", "player123")

    update_user_data("discord", "123456789", {"return_date_to_position": "2023-01-01"})

    map_ids("987654321", "mindustry_player456")

    create_ticket("1122334455", "TICKET-001")

    platform, related_id = get_related_id("987654321")
    print(f"Related ID: {platform} - {related_id}")

    user_profile = get_full_user_data("discord", "123456789")
    print("User Profile:")
    if user_profile:
        for key, value in user_profile.items():
            print(f"{key}: {value}")
    else:
        print("User not found")

    promotion("discord", "admin001", "user002", "Moderator")
    demotion("discord", "admin001", "user002", "Moderator")

    set_return_date("discord", "user003", 30)
    set_staff_return_date("discord", "user004", 60)

    add_mute("mindustry", "player789", "admin002", "Spamming", 3)
    add_ban("discord", "user005", "admin003", "Cheating", 7)
    add_kick("discord", "user006", "admin004", "Нарушение правил чата")  # Пример использования add_kick

    user_profile = get_full_user_data("discord", "admin001")
    print("\nAdmin001 Profile:")
    if user_profile:
        for key, value in user_profile.items():
            print(f"{key}: {value}")
    else:
        print("User admin001 not found")