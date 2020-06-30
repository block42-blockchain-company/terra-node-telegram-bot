import atexit
import re
import subprocess

from telegram.error import BadRequest
from telegram.ext import Updater, PicklePersistence, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, \
    run_async

from constants import *
from helpers import *
from jobs import *

"""
######################################################################################################################################################
Debug Processes
######################################################################################################################################################
"""

if DEBUG:
    mock_api_process = subprocess.Popen(['python3', '-m', 'http.server', '8000', '--bind', '127.0.0.1'], cwd="test/")
    increase_block_height_process = subprocess.Popen(['python3', 'increase_block_height.py'], cwd="test/")
    update_local_price_feed = subprocess.Popen(['python3', 'update_price_feed.py'], cwd="test/")

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
    for chat_id in chat_ids:
        dispatcher.job_queue.run_repeating(node_checks, interval=15, context={
            'chat_id': chat_id, 'user_data': dispatcher.user_data[chat_id]
        })
        restart_message = 'Hello there!\n' \
                          'Me, your Node Bot of Terra, just got restarted on the server! 🤖\n' \
                          'To make sure you have the latest features, please start ' \
                          'a fresh chat with me by typing /start.'
        dispatcher.bot.send_message(chat_id, restart_message)


"""
######################################################################################################################################################
Handlers
######################################################################################################################################################
"""


@run_async
def start(update, context):
    """
    Send start message and display action buttons.
    """

    context.user_data['expected'] = None

    # Start job for user
    if 'job_started' not in context.user_data:
        context.job_queue.run_repeating(node_checks, interval=15, context={
            'chat_id': update.message.chat.id,
            'user_data': context.user_data
        })
        context.user_data['job_started'] = True
        context.user_data['nodes'] = {}

    text = 'Hello there! I am your Node Monitoring Bot of the Terra network. 🤖\n' \
           'I will notify you about changes of your node\'s *Jailed*, *Unbonded* or *Delegator Shares*, ' \
           'if your *Block Height* gets stuck and if your *Price Feed* gets unhealthy!\n' \
           'Moreover, I will notify you about new governance proposals!'

    # Send message
    update.message.reply_text(text, parse_mode='markdown')
    show_home_menu_new_msg(context=context, chat_id=update.effective_chat.id)


@run_async
def cancel(update, context):
    """
    Go back to home menu
    """

    context.user_data['expected'] = None
    show_my_nodes_menu_new_msg(context=context, chat_id=update.effective_chat.id)


@run_async
def dispatch_query(update, context):
    """
    Call right function depending on the button clicked
    """

    query = update.callback_query
    query.answer()
    data = query.data

    context.user_data['expected'] = None
    edit = True
    call = None

    if data == 'home':
        call = show_home_menu_edit_msg
    elif data == 'my_nodes':
        call = show_my_nodes_menu_edit_msg
    elif data == 'add_node':
        call = add_node
    elif re.match('node_details', data):
        call = node_details
    elif data == 'confirm_node_deletion':
        call = confirm_node_deletion
    elif data == 'delete_node':
        call = delete_node
    elif data == 'show_detail_menu':
        call = show_detail_menu
    else:
        edit = False

    # Catch any 'Message is not modified' error by removing the keyboard
    if edit:
        try:
            context.bot.edit_message_reply_markup(reply_markup=None,
                                                  chat_id=update.callback_query.message.chat_id,
                                                  message_id=update.callback_query.message.message_id)
        except BadRequest as e:
            if 'Message is not modified' in e.message:
                pass
            else:
                raise

    if call:
        return call(update, context)


@run_async
def plain_input(update, context):
    """
    Handle if the users sends a message
    """
    expected = context.user_data['expected'] if 'expected' in context.user_data else None
    if expected == 'add_node':
        context.user_data['expected'] = None
        return handle_add_node(update, context)


@run_async
def error(update, context):
    """
    Log error.
    """

    logger.warning('Update "%s" caused error: %s', update, context.error)


def show_home_menu_edit_msg(update, context):
    """
    Edit current message with the home menu
    """

    keyboard = get_home_menu_buttons()
    text = 'I am your Terra Node Bot. 🤖\nClick *MY NODES* to get information about the Terra Nodes you monitor!'
    query = update.callback_query
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='markdown')


def show_my_nodes_menu_edit_msg(update, context):
    """
    Show My Nodes Menu
    """

    keyboard = get_my_nodes_menu_buttons(user_data=context.user_data)
    text = 'Click an address from the list below or add a node:' if len(keyboard) > 2 else 'You do not monitor any ' \
                                                                                        'Terra Nodes yet.\nAdd a Node!'
    query = update.callback_query
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


def add_node(update, context):
    """
    Ask user to write a node address
    """

    query = update.callback_query

    context.user_data['expected'] = 'add_node'

    text = 'What\'s the address of your Node? (enter /cancel to return to the menu)'

    # Send message
    query.edit_message_text(text)


def handle_add_node(update, context):
    """
    Process what the user's input
    """

    address = update.message.text
    node = get_validator(address)

    if node is None:
        context.user_data['expected'] = 'add_node'
        return update.message.reply_text(
            '⛔️ I have not found a Node with this address! ⛔\nPlease try another one. (enter /cancel to return to the menu)')

    context.user_data['nodes'][address] = {}
    context.user_data['nodes'][address]['status'] = node['status']
    context.user_data['nodes'][address]['jailed'] = node['jailed']
    context.user_data['nodes'][address]['delegator_shares'] = node['delegator_shares']

    context.bot.send_message(update.effective_chat.id, 'Got it! 👌')
    return show_my_nodes_menu_new_msg(context=context, chat_id=update.effective_chat.id)


def node_details(update, context):
    """
    Show Detail Menu for the selected address
    """

    query = update.callback_query

    address = query.data.split("-")[1]
    context.user_data['selected_node_address'] = address

    return show_detail_menu(update=update, context=context)


def confirm_node_deletion(update, context):
    """
    Ask user if he is sure to remove the address
    """

    address = context.user_data['selected_node_address']

    keyboard = [[
        InlineKeyboardButton('YES ✅', callback_data='delete_node'),
        InlineKeyboardButton('NO ❌', callback_data='show_detail_menu')
    ]]
    text = '⚠️ Do you really want to remove the address from your monitoring list? ⚠️\n*' + address + '*'

    query = update.callback_query
    query.edit_message_text(text, parse_mode='markdown', reply_markup=InlineKeyboardMarkup(keyboard))


def delete_node(update, context):
    """
    Remove address vom the monitoring list
    """

    query = update.callback_query
    address = context.user_data['selected_node_address']

    del context.user_data['nodes'][address]

    text = "❌ Node address got deleted! ❌\n" + address
    query.answer(text)
    query.edit_message_text(text)
    show_my_nodes_menu_new_msg(context=context, chat_id=update.effective_chat.id)


"""
######################################################################################################################################################
Application
######################################################################################################################################################
"""


def main():
    """
    Init telegram bot, attach handlers and wait for incoming requests.
    """

    # Init telegram bot
    bot = Updater(TELEGRAM_BOT_TOKEN, persistence=PicklePersistence(filename='storage/session.data'), use_context=True)
    dispatcher = bot.dispatcher

    setup_existing_user(dispatcher=dispatcher)

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('cancel', cancel))
    dispatcher.add_handler(CallbackQueryHandler(dispatch_query))
    dispatcher.add_handler(MessageHandler(Filters.text, plain_input))

    # log all errors
    dispatcher.add_error_handler(error)

    # Start the bot
    bot.start_polling()
    logger.info('node Bot is running ...')

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    bot.idle()


if __name__ == '__main__':
    main()
