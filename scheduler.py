import json
import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot


def send_scheduled_messages(bot):
    with open('schedule.json', 'r') as file:
        schedule = json.load(file)
    now = datetime.datetime.now(pytz.utc).time()
    for key, info in schedule.items():
        scheduled_time = datetime.datetime.strptime(info['time'], '%H:%M').time()
        if now.hour == scheduled_time.hour and now.minute == scheduled_time.minute:
            bot.send_message(chat_id=info['chat_id'], text=info['message'])


def start_scheduler(bot_token):
    bot = Bot(bot_token)
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_scheduled_messages, 'cron', minute='*', args=[bot])
    scheduler.start()
    return scheduler
