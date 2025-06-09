import discord
import database
from datetime import datetime
import time
from pytz import timezone

data=load_data()
gmt = timezone('GMT')
while True:
    now = datetime.now(gmt)
    for platform, users in data.items():
        for user, user_data in users.items():
            if user == 'action':
                continue
            if user_data.get('unban_time'):
                unban_time = datetime.strptime(user_data['unban_time'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=gmt)
                if unban_time <= now:
                    discord.unban(platform,user)

            if user_data.get('unmute_time'):
                unmute_time = datetime.strptime(user_data['unmute_time'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=gmt)
                if unmute_time <= now:
                    discord.unmute(platform,user)

            if user_data.get('return_date_to_staff'):
                return_staff_time = datetime.strptime(user_data['return_date_to_staff'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=gmt)
                if return_staff_time <= now:
                    discord.return_to_staff(platform,user)

            if user_data.get('return_date_to_position'):
                return_position_time = datetime.strptime(user_data['return_date_to_position'], "%Y-%m-%d %H:%M:%S").replace(tzinfo=gmt)
                if return_position_time <= now:
                    discord.return_to_position(platform,user)

    time.sleep(60)
