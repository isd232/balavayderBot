import logging
from datetime import datetime, timedelta
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
# Import token
import config

# Define states for conversation
CHANNEL, MESSAGE, CONFIRM = range(3)

# Set up basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Error handler function
def error(update, context):
    """Log Errors caused by Updates."""
    logger.error('Update caused error:', exc_info=context.error)
    try:
        update.message.reply_text('An error occurred: {}'.format(context.error))
    except Exception as e:
        logger.error('Error while handling the previous error: %s', e)


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hello! Welcome to the Scheduler Bot. Type /help for instructions.")


def help_command(update: Update, context: CallbackContext):
    help_text = (
        "To schedule a message:\n"
        "- Start with /schedule.\n"
        "- Enter the channel ID (e.g., @your_channel).\n"
        "- Enter your message.\n"
        "- Enter the date and time in 'DD/MM/YYYY HH:MM' format (24-hour clock)."
    )
    update.message.reply_text(help_text)


def schedule(update: Update, context: CallbackContext):
    update.message.reply_text("Please enter the channel ID where you want to schedule a message:")
    return CHANNEL


def receive_channel(update: Update, context: CallbackContext):
    context.user_data['channel'] = update.message.text
    update.message.reply_text("Please enter your message:")
    return MESSAGE


def receive_message(update: Update, context: CallbackContext):
    context.user_data['message'] = update.message.text
    update.message.reply_text("Please enter the date and time for the message (DD/MM/YYYY HH:MM):")
    return CONFIRM


def confirm(update: Update, context: CallbackContext):
    try:
        date_time_str = update.message.text
        # Parse the string into a datetime object assuming it's in local time format
        naive_time = datetime.strptime(date_time_str, '%d/%m/%Y %H:%M')

        # Define the timezone you are working with
        warsaw_tz = timezone('Europe/Warsaw')

        # Localize the naive datetime object with the specified timezone
        local_time = warsaw_tz.localize(naive_time)

        # Debug log to check the datetime object
        logging.debug("Scheduled time (timezone-aware): %s", local_time)

        # Adding job to scheduler
        scheduler.add_job(send_message, 'date', run_date=local_time,
                          args=[context.user_data['channel'], context.user_data['message']])
        update.message.reply_text(f"Message scheduled for {local_time} at {context.user_data['channel']}.")
        return ConversationHandler.END
    except ValueError:
        update.message.reply_text("Incorrect date format. Please use DD/MM/YYYY HH:MM format.")
        return CONFIRM
    except Exception as e:
        logging.error("Failed to schedule message: %s", e)
        update.message.reply_text(f"An error occurred: {e}")
        return ConversationHandler.END


def send_message(channel_id, text):
    bot = Bot(config.TOKEN)
    bot.send_message(chat_id=channel_id, text=text)


def cancel(update: Update, context: CallbackContext):
    update.message.reply_text('Scheduling cancelled.')
    return ConversationHandler.END


def main():
    updater = Updater(config.TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Job scheduler
    global scheduler
    scheduler = BackgroundScheduler(timezone=pytz.utc)
    scheduler.start()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('schedule', schedule)],
        states={
            CHANNEL: [MessageHandler(Filters.text & ~Filters.command, receive_channel)],
            MESSAGE: [MessageHandler(Filters.text & ~Filters.command, receive_message)],
            CONFIRM: [MessageHandler(Filters.text & ~Filters.command, confirm)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(conv_handler)
    dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
