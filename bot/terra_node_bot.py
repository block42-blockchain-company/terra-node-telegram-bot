import atexit
import re
import subprocess
from helpers import *
from constants import *
from jobs import *

from telegram.error import BadRequest
from telegram.ext import Updater, PicklePersistence, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, \
    run_async

"""
######################################################################################################################################################
Debug Processes
######################################################################################################################################################
"""

if DEBUG:
    mock_api_process = subprocess.Popen(['python3', '-m', 'http.server', '8000', '--bind', '127.0.0.1'], cwd="test/")

    current_dir = os.path.dirname(os.path.realpath(__file__))
    test_dir = os.sep.join([current_dir, os.path.pardir, "test"])
    increase_block_height_path = os.sep.join([test_dir, "increase_block_height.py"])
    update_local_price_feed_path = os.sep.join([test_dir, "update_price_feed.py"])

    increase_block_height_process = subprocess.Popen(['python3', increase_block_height_path], cwd=test_dir)
    update_local_price_feed = subprocess.Popen(['python3', update_local_price_feed_path], cwd="test/")


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
            dispatcher.job_queue.run_repeating(node_checks, interval=JOB_INTERVAL_IN_SECONDS, context={
                'chat_id': chat_id, 'user_data': dispatcher.user_data[chat_id]
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
        context.job_queue.run_repeating(node_checks, interval=JOB_INTERVAL_IN_SECONDS, context={
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
    elif data == 'confirm_add_all_nodes':
        call = confirm_add_all_nodes
    elif data == 'add_all_nodes':
        call = add_all_nodes
    elif data == 'confirm_delete_all_nodes':
        call = confirm_delete_all_nodes
    elif data == 'delete_all_nodes':
        call = delete_all_nodes
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
    try:
        node = get_validator(address=address)
    except ConnectionError:
        context.user_data['expected'] = None
        update.message.reply_text('⛔️ I cannot reach the LCD server!⛔\nPlease try again later.')
        return show_my_nodes_menu_new_msg(context=context, chat_id=update.effective_chat.id)

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


def confirm_add_all_nodes(update, context):
    """
    Ask user if he really wants to add all available nodes
    """

    keyboard = [[
        InlineKeyboardButton('YES ✅', callback_data='add_all_nodes'),
        InlineKeyboardButton('NO ❌', callback_data='my_nodes')
    ]]
    text = '⚠️ Do you really want to *add all* available Terra Nodes to your monitoring list? ⚠️'

    return show_confirmation_menu(update=update, text=text, keyboard=keyboard)


def confirm_delete_all_nodes(update, context):
    """
    Ask user if he really wants to delete all available nodes
    """

    keyboard = [[
        InlineKeyboardButton('YES ✅', callback_data='delete_all_nodes'),
        InlineKeyboardButton('NO ❌', callback_data='my_nodes')
    ]]
    text = '⚠️ Do you really want to *remove all* Terra Nodes from your monitoring list? ⚠️'

    return show_confirmation_menu(update=update, text=text, keyboard=keyboard)


def add_all_nodes(update, context):
    """
    Add all available node addresses to users monitoring list
    """

    query = update.callback_query

    nodes = get_node_accounts()

    for node in nodes:
        address = node['node_address']
        if address not in context.user_data['nodes']:
            add_node_to_user_data(context.user_data, address, node)

    # Send message
    query.edit_message_text('Added all Terra Nodes! 👌')
    show_node_menu_new_msg(update, context)


def delete_all_nodes(update, context):
    """
    Delete all node addresses from users monitoring list
    """

    query = update.callback_query

    addresses = []
    for address in context.user_data['nodes']:
        addresses.append(address)

    for address in addresses:
        del context.user_data['nodes'][address]

    text = '❌ Deleted all Terra Nodes! ❌'
    # Send message
    query.edit_message_text(text)

    show_node_menu_new_msg(update, context)


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
    bot = Updater(TELEGRAM_BOT_TOKEN, persistence=PicklePersistence(filename=session_data_path), use_context=True)
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
    logger.info('Terra Node Bot is running ...')

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    bot.idle()


if __name__ == '__main__':
    main()
