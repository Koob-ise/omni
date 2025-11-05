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
            discord_id TEXT UNIQUE,
            mindustry_id TEXT UNIQUE,
            created_at TEXT NOT NULL
        )''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            channel_id TEXT NOT NULL UNIQUE,
            log_message_id TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            ticket_type TEXT,
            offender_identifier TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL CHECK(action_type IN (
                'promotion', 'demotion', 'mute', 'ban', 
                'warn', 'kick', 'voice_mute', 'blacklist'
            )),
            performed_by INTEGER NOT NULL,
            ticket_id INTEGER,
            log_message_id TEXT,
            role TEXT,
            reason TEXT,
            time TEXT NOT NULL,
            duration_seconds INTEGER,
            expires_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            revoked_by INTEGER,
            revocation_reason TEXT,
            revocation_time TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (performed_by) REFERENCES users (id) ON DELETE SET NULL,
            FOREIGN KEY (revoked_by) REFERENCES users (id) ON DELETE SET NULL,
            FOREIGN KEY (ticket_id) REFERENCES tickets (id) ON DELETE SET NULL
        )''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_mindustry_id ON users(mindustry_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_actions_user_id ON user_actions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_channel_id ON tickets(channel_id)')
        conn.commit()
        logger.info("Database initialized successfully.")


def create_user(discord_id=None, mindustry_id=None):
    if not discord_id and not mindustry_id:
        raise ValueError("At least one ID (discord_id or mindustry_id) must be provided.")

    with db_connection() as conn:
        cursor = conn.cursor()

        query = "SELECT id FROM users WHERE "
        params = []
        if discord_id:
            query += "discord_id = ?"
            params.append(str(discord_id))
        if mindustry_id:
            if discord_id: query += " OR "
            query += "mindustry_id = ?"
            params.append(str(mindustry_id))

        cursor.execute(query, params)
        existing_user = cursor.fetchone()

        if existing_user:
            return existing_user['id']
        else:
            gmt = pytz.timezone('GMT')
            current_time = datetime.now(gmt).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                'INSERT INTO users (discord_id, mindustry_id, created_at) VALUES (?, ?, ?)',
                (str(discord_id) if discord_id else None, str(mindustry_id) if mindustry_id else None, current_time)
            )
            conn.commit()
            logger.info(f"Created new user: discord_id={discord_id}, mindustry_id={mindustry_id}")
            return cursor.lastrowid


def resolve_user_ids(platform, main_user_id, performer_id):
    user_params = {'discord_id': main_user_id} if platform == 'discord' else {'mindustry_id': main_user_id}
    main_user_internal_id = create_user(**user_params)
    performer_internal_id = create_user(discord_id=performer_id)
    return main_user_internal_id, performer_internal_id


def _add_action(user_id, performed_by_id, action_type, ticket_id=None, role=None, reason=None, duration_seconds=None,
                expires_at=None):
    gmt = pytz.timezone('GMT')
    current_time = datetime.now(gmt).strftime('%Y-%m-%d %H:%M:%S')

    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO user_actions 
            (user_id, performed_by, action_type, ticket_id, role, reason, time, duration_seconds, expires_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, performed_by_id, action_type, ticket_id, role, reason, current_time, duration_seconds, expires_at)
        )
        conn.commit()
        logger.info(f"Added {action_type} for user_id {user_id} by user_id {performed_by_id}")
        return cursor.lastrowid


def get_active_punishment(user_internal_id, action_type):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, expires_at FROM user_actions
               WHERE user_id = ? AND action_type = ? AND is_active = 1
               ORDER BY time DESC LIMIT 1""",
            (user_internal_id, action_type)
        )
        return cursor.fetchone()


def deactivate_action(action_id):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE user_actions SET is_active = 0 WHERE id = ?",
            (action_id,)
        )
        conn.commit()
        logger.info(f"Silently deactivated action_id {action_id} due to being superseded.")


def count_active_warns(user_internal_id):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT COUNT(*) as warn_count
               FROM user_actions
               WHERE user_id = ? AND action_type = 'warn' AND is_active = 1""",
            (user_internal_id,)
        )
        result = cursor.fetchone()
        return result['warn_count'] if result else 0


def deactivate_all_warns(user_internal_id):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE user_actions SET is_active = 0 WHERE user_id = ? AND action_type = 'warn' AND is_active = 1",
            (user_internal_id,)
        )
        conn.commit()
        logger.info(f"Deactivated all active warnings for user_id {user_internal_id} due to reaching the warn limit.")


def revoke_action(action_id, revoked_by_internal_id, reason):
    gmt = pytz.timezone('GMT')
    revocation_time = datetime.now(gmt).strftime('%Y-%m-%d %H:%M:%S')

    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM user_actions WHERE id = ?", (action_id,))
        action_data = cursor.fetchone()

        if not action_data:
            logger.error(f"Attempted to revoke non-existent action with ID: {action_id}")
            return False

        cursor.execute(
            """UPDATE user_actions
               SET is_active = 0, revoked_by = ?, revocation_reason = ?, revocation_time = ?
               WHERE id = ?""",
            (revoked_by_internal_id, reason, revocation_time, action_id)
        )
        conn.commit()
        logger.info(f"Revoked action ID {action_id} for user_id {action_data['user_id']} by {revoked_by_internal_id}")
        return True


def check_ticket_has_punishment(ticket_db_id):
    if not ticket_db_id:
        return False
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM user_actions WHERE ticket_id = ? LIMIT 1",
            (ticket_db_id,)
        )
        result = cursor.fetchone()
        return result is not None


def get_user_internal_id(platform, platform_id):
    with db_connection() as conn:
        cursor = conn.cursor()
        column = "discord_id" if platform == "discord" else "mindustry_id"
        cursor.execute(f"SELECT id FROM users WHERE {column} = ?", (str(platform_id),))
        result = cursor.fetchone()
        return result['id'] if result else None


def get_full_user_data(platform, platform_id):
    internal_id = get_user_internal_id(platform, platform_id)
    if not internal_id:
        return None

    with db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE id = ?', (internal_id,))
        user_data = cursor.fetchone()
        if not user_data:
            return None

        result = {
            'internal_id': user_data['id'],
            'discord_id': user_data['discord_id'],
            'mindustry_id': user_data['mindustry_id'],
            'created_at': user_data['created_at'],
            'profile_data': {
                'promotions': [], 'demotions': [], 'mutes': [], 'bans': [],
                'warns': [], 'kicks': [], 'voice_mutes': [], 'blacklists': []
            },
            'actions_taken': []
        }

        cursor.execute(
            '''SELECT ua.id, ua.action_type, p_user.discord_id as performed_by_discord_id, 
                   ua.ticket_id, ua.role, ua.reason, ua.time, ua.duration_seconds, ua.expires_at, 
                   ua.is_active, r_user.discord_id as revoked_by_discord_id, ua.revocation_reason, 
                   ua.revocation_time
            FROM user_actions ua
            LEFT JOIN users p_user ON ua.performed_by = p_user.id
            LEFT JOIN users r_user ON ua.revoked_by = r_user.id
            WHERE ua.user_id = ?''',
            (internal_id,))
        for action in cursor.fetchall():
            action_data = {k: v for k, v in dict(action).items() if v is not None}
            action_type_plural = f"{action['action_type']}s"
            if action_type_plural in result['profile_data']:
                result['profile_data'][action_type_plural].append(action_data)

        cursor.execute(
            '''SELECT ua.action_type, t_user.discord_id as target_discord_id, 
                   t_user.mindustry_id as target_mindustry_id,
                   ua.role, ua.reason, ua.time, ua.duration_seconds
            FROM user_actions ua
            JOIN users t_user ON ua.user_id = t_user.id
            WHERE ua.performed_by = ?''',
            (internal_id,))
        result['actions_taken'] = [dict(row) for row in cursor.fetchall()]

    return result


def get_info_for_all_active_punishments(user_internal_id):
    if not user_internal_id:
        return []
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT ua.action_type, t.log_message_id, t.channel_id
               FROM user_actions AS ua
               INNER JOIN tickets AS t ON ua.ticket_id = t.id
               WHERE ua.user_id = ? 
                 AND ua.is_active = 1
               ORDER BY ua.time DESC""",
            (user_internal_id,)
        )
        results = [dict(row) for row in cursor.fetchall()]
        return results


def get_info_for_active_discord_complaints(user_internal_id):
    if not user_internal_id:
        return []
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT ua.action_type, t.log_message_id, t.channel_id
               FROM user_actions AS ua
               INNER JOIN tickets AS t ON ua.ticket_id = t.id
               WHERE ua.user_id = ? 
                 AND ua.is_active = 1
                 AND t.ticket_type = 'Discord-Complaint'
               ORDER BY ua.time DESC""",
            (user_internal_id,)
        )
        results = [dict(row) for row in cursor.fetchall()]
        return results


def find_mindustry_complaints_by_nickname(nickname):
    if not nickname:
        return []
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT log_message_id FROM tickets
               WHERE ticket_type = 'Mindustry-Complaint'
                 AND offender_identifier = ?
                 AND status = 'CLOSED'
                 AND log_message_id IS NOT NULL""",
            (nickname,)
        )
        results = [dict(row) for row in cursor.fetchall()]
        return results