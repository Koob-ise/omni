import json
import os
from datetime import datetime, timedelta
import pytz
from pathlib import Path

DB_PATH = '../database/database.json'


def load_data():
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "r", encoding="utf-8") as file:
                return json.load(file)
    except json.JSONDecodeError:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

    return {"discord": {}, "mindustry": {}, "id_mapping": {}}


def save_data(data):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def create_user(platform, user_id):
    if platform not in ["discord", "mindustry"]:
        raise ValueError("Неподдерживаемая платформа")

    data = load_data()
    user_id_str = str(user_id)

    if user_id_str not in data[platform]:
        data[platform][user_id_str] = {
            "created_at": datetime.now(pytz.timezone('GMT')).strftime('%Y-%m-%d %H:%M:%S'),
            "action": {"promotions": [], "demotions": [], "bans": [], "mutes": [], "warns": []},
            "promotions": [],
            "demotions": [],
            "return_date_to_position": "",
            "return_date_to_staff": "",
            "mutes": [],
            "bans": [],
            "warns": [],
            "unban_time": "",
            "unmute_time": ""
        }
        save_data(data)

    return data[platform][user_id_str]


def update_user_data(platform, user_id, user_data):
    data = load_data()
    data[platform][str(user_id)] = user_data
    save_data(data)


def map_ids(discord_id, mindustry_id):
    data = load_data()
    data["id_mapping"][str(discord_id)] = str(mindustry_id)
    save_data(data)


def get_related_id(user_id):
    data = load_data()
    user_id_str = str(user_id)

    if user_id_str in data["id_mapping"]:
        return "mindustry", data["id_mapping"][user_id_str]

    for discord_id, mind_id in data["id_mapping"].items():
        if mind_id == user_id_str:
            return "discord", discord_id

    return None, None


def get_full_user_data(platform, user_id):
    data = load_data()
    user_id_str = str(user_id)

    if platform not in data or user_id_str not in data[platform]:
        return None

    user_data = data[platform][user_id_str]
    result = {
        'platform': platform,
        'id': user_id_str,
        'created_at': user_data['created_at'],
        'profile_data': {
            'promotions': user_data['promotions'],
            'demotions': user_data['demotions'],
            'mutes': user_data['mutes'],
            'bans': user_data['bans'],
            'warns': user_data['warns'],
            'return_dates': {
                'to_position': user_data['return_date_to_position'],
                'to_staff': user_data['return_date_to_staff']
            },
            'active_restrictions': {
                'unban_time': user_data['unban_time'],
                'unmute_time': user_data['unmute_time']
            }
        },
        'actions_taken': user_data['action'],
        'linked_account': None
    }

    related_platform, related_id = get_related_id(user_id)
    if related_platform and related_id and related_id in data[related_platform]:
        result['linked_account'] = {
            'platform': related_platform,
            'id': related_id,
            'created_at': data[related_platform][related_id]['created_at'],
            'profile_data': {
                'promotions': data[related_platform][related_id]['promotions'],
                'demotions': data[related_platform][related_id]['demotions'],
                'mutes': data[related_platform][related_id]['mutes'],
                'bans': data[related_platform][related_id]['bans'],
                'warns': data[related_platform][related_id]['warns']
            }
        }

    return result


def promotion(platform, role_changed_by, main_user, role):
    user_data = create_user(platform, main_user)
    admin_data = create_user(platform, role_changed_by)
    date = datetime.now(pytz.timezone('GMT')).strftime('%Y-%m-%d %H:%M:%S')

    user_data["promotions"].append({
        "role_changed_by": role_changed_by,
        "date": date,
        "role": role
    })

    admin_data["action"]["promotions"].append({
        "target_user": main_user,
        "role": role,
        "time": date
    })

    update_user_data(platform, main_user, user_data)
    update_user_data(platform, role_changed_by, admin_data)


def demotion(platform, role_changed_by, main_user, role):
    user_data = create_user(platform, main_user)
    admin_data = create_user(platform, role_changed_by)
    date = datetime.now(pytz.timezone('GMT')).strftime('%Y-%m-%d %H:%M:%S')

    user_data["demotions"].append({
        "role_changed_by": role_changed_by,
        "date": date,
        "role": role
    })

    admin_data["action"]["demotions"].append({
        "target_user": main_user,
        "role": role,
        "time": date
    })

    update_user_data(platform, main_user, user_data)
    update_user_data(platform, role_changed_by, admin_data)


def set_return_date(platform, main_user, DAYS_TO_ADD):
    today = datetime.now(pytz.timezone('GMT'))
    return_date = today + timedelta(days=DAYS_TO_ADD)
    return_date_str = return_date.strftime('%Y-%m-%d %H:%M:%S')
    user_data = create_user(platform, main_user)
    user_data["return_date_to_position"] = return_date_str
    update_user_data(platform, main_user, user_data)


def set_staff_return_date(platform, main_user, DAYS_TO_ADD):
    today = datetime.now(pytz.timezone('GMT'))
    staff_return_date = today + timedelta(days=DAYS_TO_ADD)
    staff_return_date_str = staff_return_date.strftime('%Y-%m-%d %H:%M:%S')
    user_data = create_user(platform, main_user)
    user_data["return_date_to_staff"] = staff_return_date_str
    update_user_data(platform, main_user, user_data)


def add_mute(platform, main_user, muted_by, reason, mute_days):
    user_data = create_user(platform, main_user)
    admin_data = create_user(platform, muted_by)
    date = datetime.now(pytz.timezone('GMT')).strftime('%Y-%m-%d %H:%M:%S')
    new_unmute_time = (datetime.now(pytz.timezone('GMT')) + timedelta(days=mute_days)).strftime('%Y-%m-%d %H:%M:%S')

    user_data["mutes"].append({
        "muted_by": muted_by,
        "reason": reason,
        "time": date
    })

    current_unmute_time = user_data.get("unmute_time", "")
    if current_unmute_time:
        current_unmute_dt = datetime.strptime(current_unmute_time, '%Y-%m-%d %H:%M:%S')
        new_unmute_dt = datetime.strptime(new_unmute_time, '%Y-%m-%d %H:%M:%S')
        if new_unmute_dt > current_unmute_dt:
            user_data["unmute_time"] = new_unmute_time
    else:
        user_data["unmute_time"] = new_unmute_time

    admin_data["action"]["mutes"].append({
        "target_user": main_user,
        "reason": reason,
        "time": date
    })

    update_user_data(platform, main_user, user_data)
    update_user_data(platform, muted_by, admin_data)


def add_ban(platform, main_user, banned_by, reason, ban_days):
    user_data = create_user(platform, main_user)
    admin_data = create_user(platform, banned_by)
    date = datetime.now(pytz.timezone('GMT')).strftime('%Y-%m-%d %H:%M:%S')
    new_unban_time = (datetime.now(pytz.timezone('GMT')) + timedelta(days=ban_days)).strftime('%Y-%m-%d %H:%M:%S')

    user_data["bans"].append({
        "banned_by": banned_by,
        "reason": reason,
        "time": date
    })

    current_unban_time = user_data.get("unban_time", "")
    if current_unban_time:
        current_unban_dt = datetime.strptime(current_unban_time, '%Y-%m-%d %H:%M:%S')
        new_unban_dt = datetime.strptime(new_unban_time, '%Y-%m-%d %H:%M:%S')
        if new_unban_dt > current_unban_dt:
            user_data["unban_time"] = new_unban_time
    else:
        user_data["unban_time"] = new_unban_time

    admin_data["action"]["bans"].append({
        "target_user": main_user,
        "reason": reason,
        "time": date
    })

    update_user_data(platform, main_user, user_data)
    update_user_data(platform, banned_by, admin_data)


def add_warn(platform, main_user, warned_by, reason, warn_days):
    user_data = create_user(platform, main_user)
    admin_data = create_user(platform, warned_by)
    date = datetime.now(pytz.timezone('GMT')).strftime('%Y-%m-%d %H:%M:%S')
    unwarn_time = (datetime.now(pytz.timezone('GMT')) + timedelta(days=warn_days)).strftime('%Y-%m-%d %H:%M:%S')

    user_data["warns"].append({
        "warned_by": warned_by,
        "reason": reason,
        "time": date,
        "unwarn_time": unwarn_time
    })

    admin_data["action"]["warns"].append({
        "target_user": main_user,
        "reason": reason,
        "time": date,
        "unwarn_time": unwarn_time
    })

    update_user_data(platform, main_user, user_data)
    update_user_data(platform, warned_by, admin_data)
'''
# 1
discord_user1 = create_user('discord', 1001)
discord_user2 = create_user('discord', 1002)
mindustry_user1 = create_user('mindustry', 2001)
mindustry_user2 = create_user('mindustry', 2002)

# 2
map_ids(1001, 2001)  # Связываем Discord ID 1001 с Mindustry ID 2001
map_ids(1002, 2002)  # Связываем Discord ID 1002 с Mindustry ID 2002

# 3
promotion('discord', 1001, 1002, "Модератор")

demotion('discord', 1001, 1002, "Пользователь")

add_mute('discord', 1002, 1001, "Оскорбления", 3)

add_ban('mindustry', 2002, 2001, "Читы", 30)

add_warn('mindustry', 2001, 2002, "Спам", 7)

set_return_date('discord', 1002, 14)
set_staff_return_date('discord', 1002, 30)

# 4
discord_data = get_full_user_data('discord', 1001)
print(f"Данные Discord пользователя 1001:\n{discord_data}")

mindustry_data = get_full_user_data('mindustry', 2002)
print(f"\nДанные Mindustry пользователя 2002:\n{mindustry_data}")

# 5
related_platform, related_id = get_related_id(1001)
print(f"\nСвязанный ID для Discord 1001: {related_platform} {related_id}")

related_platform, related_id = get_related_id(2002)
print(f"Связанный ID для Mindustry 2002: {related_platform} {related_id}")

# 6
full_data = load_data()
print("\nПолное содержимое базы данных:")
print(json.dumps(full_data, indent=2, ensure_ascii=False))
'''