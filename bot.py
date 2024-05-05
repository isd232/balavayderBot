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
DECISION = 4

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
    user_id = update.effective_user.id
    saved_channel_id = get_saved_channel_id(user_id)
    if saved_channel_id:
        context.user_data['channel'] = saved_channel_id
        update.message.reply_text(f"Using your saved channel ID: {saved_channel_id}. Please enter your message:")
        return MESSAGE
    else:
        update.message.reply_text("Please enter the channel ID where you want to schedule a message:")
        return CHANNEL


def save_channel_id(user_id, channel_id):
    with open('channel_ids.txt', 'a') as f:
        f.write(f"{user_id}:{channel_id}\n")


def receive_channel(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    channel_id = update.message.text
    context.user_data['channel'] = channel_id
    save_channel_id(user_id, channel_id)
    update.message.reply_text("Channel ID saved. Please enter your message:")
    return MESSAGE


def get_saved_channel_id(user_id):
    try:
        with open('channel_ids.txt', 'r') as f:
            lines = f.readlines()
            for line in lines:
                uid, cid = line.strip().split(':')
                if int(uid) == user_id:
                    return cid
    except FileNotFoundError:
        return None


def receive_message(update: Update, context: CallbackContext):
    context.user_data['message'] = update.message.text
    update.message.reply_text("Please enter the date and time for the message (DD/MM/YYYY HH:MM):")
    return CONFIRM


def confirm(update: Update, context: CallbackContext):
    try:
        date_time_str = update.message.text
        naive_time = datetime.strptime(date_time_str, '%d/%m/%Y %H:%M')
        local_tz = timezone('Europe/Warsaw')
        scheduled_time = local_tz.localize(naive_time)

        # Add the job to the scheduler
        scheduler.add_job(
            send_message,
            'date',
            run_date=scheduled_time,
            args=[
                context.user_data['channel'],
                context.user_data['message'],
                update.effective_user.id
            ]
        )
        update.message.reply_text(f"Message scheduled for {scheduled_time} at {context.user_data['channel']}.")
        return ConversationHandler.END
    except ValueError:
        update.message.reply_text("Incorrect date format. Please use DD/MM/YYYY HH:MM format.")
        return CONFIRM


def handle_user_decision(update: Update, context: CallbackContext):
    decision = update.message.text.lower()
    if decision == 'yes':
        return schedule(update, context)
    elif decision == 'no':
        update.message.reply_text("Thank you for using the bot. Goodbye!")
        return ConversationHandler.END
    else:
        update.message.reply_text("Please reply with 'yes' to continue or 'no' to end.")
        return DECISION  # Assuming DECISION is the constant for this state


def send_message(channel_id, message_text, user_id):
    bot = Bot(config.TOKEN)
    # Send the scheduled message to the channel
    bot.send_message(chat_id=channel_id, text=message_text)
    # Send a follow-up message to the user who scheduled the message
    bot.send_message(chat_id=user_id, text="Message sent! Do you want to schedule another message? Reply with 'yes' to continue or 'no' to stop.")


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
            DECISION: [MessageHandler(Filters.text & ~Filters.command, handle_user_decision)]
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
