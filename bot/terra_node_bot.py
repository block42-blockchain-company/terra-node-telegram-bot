import atexit
import subprocess

from jobs import *

from telegram.ext import Updater, PicklePersistence, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

from message_handlers import start, cancel, dispatch_query, plain_input, log_error

"""
######################################################################################################################################################
Debug Processes
######################################################################################################################################################
"""

if DEBUG:
    current_dir = os.path.dirname(os.path.realpath(__file__))
    test_dir = os.sep.join([current_dir, os.path.pardir, "test"])
    mock_api_process = subprocess.Popen(['python3', '-m', 'http.server', '8000', '--bind', '127.0.0.1'], cwd=test_dir)
    increase_block_height_path = os.sep.join([test_dir, "increase_block_height.py"])
    update_local_price_feed_path = os.sep.join([test_dir, "update_price_feed.py"])

    increase_block_height_process = subprocess.Popen(['python3', increase_block_height_path], cwd=test_dir)
    update_local_price_feed = subprocess.Popen(['python3', update_local_price_feed_path], cwd=test_dir)


    def cleanup():
        mock_api_process.terminate()
        increase_block_height_process.terminate()
        update_local_price_feed.terminate()


    atexit.register(cleanup)

"""
######################################################################################################################################################
BOT RESTART SETUP
######################################################################################################################################################
"""


def setup_existing_user(dispatcher):
    """
    Tasks to ensure smooth user experience for existing users upon Bot restart
    """

    chat_ids = dispatcher.user_data.keys()
    delete_chat_ids = []
    for chat_id in chat_ids:
        restart_message = 'Hello there!\n' \
                          'Me, your Node Bot of Terra, just got restarted on the server! 🤖\n' \
                          'To make sure you have the latest features, please start ' \
                          'a fresh chat with me by typing /start.'
        try:
            dispatcher.bot.send_message(chat_id, restart_message)
            dispatcher.job_queue.run_repeating(node_checks,
                                               interval=JOB_INTERVAL_IN_SECONDS,
                                               context={
                                                   'chat_id': chat_id,
                                                   'user_data': dispatcher.user_data[chat_id]
                                               })
        except TelegramError as e:
            if 'bot was blocked by the user' in e.message:
                delete_chat_ids.append(chat_id)
                continue
            else:
                print("Got Error\n" + str(e) + "\nwith telegram user " + str(chat_id))

    for chat_id in delete_chat_ids:
        print("Telegram user " + str(chat_id) + " blocked me; removing him from the user list")
        del dispatcher.user_data[chat_id]
        del dispatcher.chat_data[chat_id]
        del dispatcher.persistence.user_data[chat_id]
        del dispatcher.persistence.chat_data[chat_id]

        # Somehow session.data does not get updated if all users block the bot.
        # That's why we delete the file ourselves.
        if len(dispatcher.persistence.user_data) == 0:
            if os.path.exists(session_data_path):
                os.remove(session_data_path)


def main():
    """
    Init telegram bot, attach handlers and wait for incoming requests.
    """

    # Init telegram bot
    bot = Updater(TELEGRAM_BOT_TOKEN, persistence=PicklePersistence(filename=session_data_path), use_context=True)
    dispatcher = bot.dispatcher

    setup_existing_user(dispatcher=dispatcher)

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('cancel', cancel))
    dispatcher.add_handler(CallbackQueryHandler(dispatch_query))
    dispatcher.add_handler(MessageHandler(Filters.text, plain_input))

    # log all errors
    dispatcher.add_error_handler(log_error)

    # Start the bot
    bot.start_polling()
    logger.info('Terra Node Bot is running ...')

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    bot.idle()


if __name__ == '__main__':
    main()
