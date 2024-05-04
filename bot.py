from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import datetime
import json
from apscheduler.schedulers.background import BackgroundScheduler
import config
import pytz

CHANNEL, TIME = range(2)  # State definitions for the conversation

# Load or initialize data
def load_schedule():
    try:
        with open('schedule.json', 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_schedule(schedule):
    with open('schedule.json', 'w') as file:
        json.dump(schedule, file)

def start(update: Update, context: CallbackContext):
    update.message.reply_text('Please send me the channel ID where you want to post your message.')
    return CHANNEL

def receive_channel(update: Update, context: CallbackContext):
    user_data = context.user_data
    user_data['channel'] = update.message.text
    update.message.reply_text('Now send me your message followed by the time (HH:MM) you want it to be posted.')
    return TIME

def receive_time_and_message(update: Update, context: CallbackContext):
    text = update.message.text
    try:
        # Assuming the last 16 characters are date and time in 'DD/MM/YYYY HH:MM' format
        date_time_str = text[-16:]
        message_text = text[:-17]  # Remove last 17 characters (16 for datetime and 1 space)

        # Convert string to datetime object
        scheduled_datetime = datetime.datetime.strptime(date_time_str, '%d/%m/%Y %H:%M')

        # Store the scheduled message in the JSON file or database
        schedule = load_schedule()
        schedule_key = f"{update.message.chat_id}_{scheduled_datetime.strftime('%d/%m/%Y %H:%M')}"
        schedule[schedule_key] = {
            'channel': context.user_data['channel'],
            'message': message_text,
            'datetime': scheduled_datetime.isoformat()
        }
        save_schedule(schedule)

        update.message.reply_text(f"Message scheduled for {date_time_str} UTC to be posted on the channel {context.user_data['channel']}.")
        return ConversationHandler.END
    except ValueError:
        update.message.reply_text('Please ensure the date and time are in DD/MM/YYYY HH:MM format.')
        return TIME

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text('Operation cancelled.')
    return ConversationHandler.END

def send_scheduled_messages():
    now = datetime.datetime.utcnow()
    schedule = load_schedule()
    bot = Bot(config.TOKEN)
    for key, info in list(schedule.items()):
        scheduled_datetime = datetime.datetime.fromisoformat(info['datetime'])
        if now >= scheduled_datetime:
            bot.send_message(chat_id=info['channel'], text=info['message'])
            del schedule[key]  # Remove the message after sending
    save_schedule(schedule)


def main():
    updater = Updater(config.TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHANNEL: [MessageHandler(Filters.text & ~Filters.command, receive_channel)],
            TIME: [MessageHandler(Filters.text & ~Filters.command, receive_time_and_message)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    ))

    # Job scheduler and polling
    scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/Warsaw'))
    scheduler.add_job(send_scheduled_messages, 'cron', minute='*')
    scheduler.start()

    updater.start_polling()
    updater.idle()


def help_command(update: Update, context: CallbackContext):
    help_text = (
        "Here's how to use this bot:\n"
        "1. Start by sending /start to initiate the bot.\n"
        "2. The bot will ask for the channel ID where you want messages to be posted.\n"
        "   Respond with the channel ID (e.g., @your_channel_name or a numeric ID).\n"
        "3. Next, send your message followed by the date and time in 'DD/MM/YYYY HH:MM' format.\n"
        "   Example: 'Happy Birthday! 25/12/2024 18:30' - This will schedule your message on 25th December 2024 at 18:30.\n"
        "4. If you need to cancel the operation at any time, just send /cancel.\n"
        "5. To see this message again, type /help.\n"
    )
    update.message.reply_text(help_text)




if __name__ == '__main__':
    main()
