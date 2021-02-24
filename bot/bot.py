from telegram.ext import Updater, PicklePersistence, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram import TelegramError

from constants.constants import *
from constants.messages import BOT_STARTUP_LOG, BOT_RESTARTED
from jobs.sentry_jobs import setup_sentry_jobs
from jobs.jobs import node_checks
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
        try:
            dispatcher.bot.send_message(chat_id, BOT_RESTARTED)
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
                logger.error("Got Error\n" + str(e) + "\nwith telegram user " + str(chat_id))

    for chat_id in delete_chat_ids:
        logger.info("Telegram user " + str(chat_id) + " blocked me; removing him from the user list")
        del dispatcher.user_data[chat_id]
        del dispatcher.chat_data[chat_id]
        del dispatcher.persistence.user_data[chat_id]
        del dispatcher.persistence.chat_data[chat_id]

        # Somehow session.data does not get updated if all users block the bot.
        # That's why we delete the file ourselves.
        if len(dispatcher.persistence.user_data) == 0 and os.path.exists(session_data_path):
            os.remove(session_data_path)


def main():
    """
    Init telegram bot, attach handlers and wait for incoming requests.
    """

    # Init telegram bot
    bot = Updater(TELEGRAM_BOT_TOKEN, persistence=PicklePersistence(filename=session_data_path), use_context=True)
    dispatcher = bot.dispatcher

    setup_existing_user(dispatcher=dispatcher)
    setup_sentry_jobs(dispatcher=dispatcher)

    dispatcher.add_handler(CommandHandler('start', start, run_async=True))
    dispatcher.add_handler(CommandHandler('cancel', cancel, run_async=True))
    dispatcher.add_handler(CallbackQueryHandler(dispatch_query, run_async=True))
    dispatcher.add_handler(MessageHandler(Filters.text, plain_input, run_async=True))

    # log all errors
    dispatcher.add_error_handler(log_error, run_async=True)

    # Start the bot
    bot.start_polling()
    logger.info(BOT_STARTUP_LOG)
    logger.info(f"""
    ==========================================================================
    ==========================================================================
    Debug: {DEBUG}
    Telegram bot token: {"SET" if TELEGRAM_BOT_TOKEN else "MISSING!"}
    Slack webhook: {SLACK_WEBHOOK}
    LCD endpoint: {LCD_ENDPOINT}
    Sentry nodes: {SENTRY_NODES}
    Node IP: {NODE_IP}
    MNEMONIC: {"SET" if MNEMONIC else "NOT SET"}
    ==========================================================================
    ==========================================================================
    """)
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    bot.idle()


if __name__ == '__main__':
    main()
