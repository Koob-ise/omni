from datetime import datetime
import pytz
from .core import db_connection, create_user, logger


def log_ticket_open(opener_discord_id, channel_id, ticket_type, offender_identifier=None):
    gmt = pytz.timezone('GMT')
    current_time = datetime.now(gmt).strftime('%Y-%m-%d %H:%M:%S')

    internal_user_id = create_user(discord_id=opener_discord_id)

    with db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''INSERT INTO tickets 
                   (user_id, channel_id, status, created_at, ticket_type, offender_identifier) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (internal_user_id, str(channel_id), 'OPEN', current_time, ticket_type, offender_identifier)
            )
            conn.commit()
            logger.info(
                f"Logged new OPEN ticket for channel {channel_id}, type: {ticket_type}, offender_identifier: {offender_identifier}")
        except Exception as e:
            logger.error(f"Failed to log open ticket for channel {channel_id}: {e}")


def log_ticket_close(channel_id_or_db_id, log_message_url):
    with db_connection() as conn:
        cursor = conn.cursor()
        try:
            log_message_id = log_message_url.split('/')[-1]

            identifier_column = 'id' if isinstance(channel_id_or_db_id, int) else 'channel_id'

            cursor.execute(
                f'UPDATE tickets SET status = ?, log_message_id = ? WHERE {identifier_column} = ?',
                ('CLOSED', log_message_id, str(channel_id_or_db_id))
            )
            conn.commit()
            logger.info(
                f"Logged CLOSED ticket for {identifier_column} {channel_id_or_db_id} with log message {log_message_id}")
        except Exception as e:
            logger.error(f"Failed to log closed ticket for {channel_id_or_db_id}: {e}")


def get_ticket_db_id_by_channel(channel_id):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tickets WHERE channel_id = ?", (str(channel_id),))
        result = cursor.fetchone()
        return result['id'] if result else None


def get_punishment_log_id_for_ticket(ticket_db_id):
    if not ticket_db_id:
        return None
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT log_message_id FROM user_actions
                   WHERE ticket_id = ? AND log_message_id IS NOT NULL
                   ORDER BY time DESC LIMIT 1""",
                (ticket_db_id,)
            )
            result = cursor.fetchone()
            return result['log_message_id'] if result else None
    except Exception as e:
        logger.error(f"Failed to get punishment log_message_id for ticket {ticket_db_id}: {e}")
        return None