import atexit
import json
import os
import logging
import re
import subprocess

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import Updater, PicklePersistence, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, \
    CallbackContext, run_async

"""
######################################################################################################################################################
Static and Environment Variables
######################################################################################################################################################
"""

DEBUG = bool(os.environ['DEBUG'] == 'True') if 'DEBUG' in os.environ else False
TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']

# Set NODE_IP depending on mode (if None, certain node health jobs are not executed)
if DEBUG:
    NODE_IP = 'localhost'
elif 'NODE_IP' in os.environ and os.environ['NODE_IP']:
    NODE_IP = os.environ['NODE_IP']
else:
    NODE_IP = None

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

NODE_STATUSES = ["Unbonded", "Unbonding", "Bonded"]

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
           'I will notify you about changes of your node\'s *Jailed* or *Unbonded*, ' \
           'if your *Block Height* gets stuck and if your *Price Feed* gets unhealthy!\n' \

    # Send message
    update.message.reply_text(text, parse_mode='markdown')
    show_home_menu_new_msg(context=context, chat_id=update.effective_chat.id)


@run_async
def cancel(update, context):
    """
    Go back to home menu
    """

    context.user_data['expected'] = None
    show_home_menu_new_msg(context=context, chat_id=update.effective_chat.id)


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


def show_home_menu_new_msg(context, chat_id):
    """
    Send a new message with the home menu
    """

    user_data = context.user_data if context.user_data else context.job.context['user_data']

    keyboard = get_home_menu_buttons(user_data=user_data)
    text = 'I am your Terra Node Bot. 🤖\nChoose an address from the list below or add one:'
    context.bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))


def show_home_menu_edit_msg(update, context):
    """
    Edit current message with the home menu
    """

    keyboard = get_home_menu_buttons(user_data=context.user_data)
    text = 'I am your Terra Node Bot. 🤖\nChoose an address from the list below or add one:'
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

    context.bot.send_message(update.effective_chat.id, 'Got it! 👌')
    return show_home_menu_new_msg(context=context, chat_id=update.effective_chat.id)


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
    show_home_menu_new_msg(context=context, chat_id=update.effective_chat.id)


"""
######################################################################################################################################################
Helpers
######################################################################################################################################################
"""


def get_home_menu_buttons(user_data):
    """
    Return Keyboard buttons for the home menu
    """

    keyboard = [[]]

    for address in user_data['nodes'].keys():
        keyboard.append([InlineKeyboardButton(address, callback_data='node_details-' + address)])

    keyboard.append([InlineKeyboardButton('Add Node', callback_data='add_node')])

    return keyboard


def show_detail_menu(update, context):
    """
    Show detail buttons for selected address
    """

    query = update.callback_query
    address = context.user_data['selected_node_address']

    text = 'Node: *' + address + '*\n' + \
           'Status: *' + NODE_STATUSES[context.user_data['nodes'][address]['status']] + '*\n' + \
           'Jailed: *' + str(context.user_data['nodes'][address]['jailed']) + '*\n\n'

    text += "What do you want to do with that Node?"

    keyboard = [[
        InlineKeyboardButton('Delete Node', callback_data='confirm_node_deletion'),
        InlineKeyboardButton('<< Back', callback_data='home')
        ]]

    # Modify message
    query.edit_message_text(text, parse_mode='markdown', reply_markup=InlineKeyboardMarkup(keyboard))


def get_validator(address):
    """
    Return json of desired validator node
    """

    if DEBUG:
        # Get local validator file
        response = requests.get('http://localhost:8000/validators.json')
        nodes = response.json()
        # Get the right node
        node = next(filter(lambda node: node['operator_address'] == address, nodes['result']), None)
        return node
    else:
        response = requests.get('https://lcd.terra.dev/staking/validators/' + address)
        if response.status_code == 200:
            node = response.json()
            return node['result']
        else:
            return None


def is_node_catching_up():
    url = get_node_status_endpoint()
    response = requests.get(url=url)
    if response.status_code != 200:
        return True

    status = response.json()
    return status['result']['sync_info']['catching_up']


def get_node_block_height():
    """
    Return block height of your Terra Node
    """

    while True:
        response = requests.get(url=get_node_status_endpoint())
        if response.status_code == 200:
            break

    status = response.json()
    return status['result']['sync_info']['latest_block_height']


def is_price_feed_healthy(address):
    """
    Check whether price feed is working properly
    """

    prevotes = get_price_feed_prevotes(address)

    if prevotes is None:
        return False

    for prevote in prevotes['result']:
        if int(prevote['submit_block']) < int(prevotes['height']) - 5:
            return False

    return True


def get_price_feed_prevotes(address):
    """
    Return the current prevotes oracle json
    """

    if DEBUG:
        # Get local prevotes file
        response = requests.get('http://localhost:8000/prevotes.json')
        return response.json()
    else:
        response = requests.get('https://lcd.terra.dev/oracle/voters/' + address + '/prevotes')
        if response.status_code == 200:
            return response.json()
        else:
            return None


def get_node_status_endpoint():
    """
    Return the endpoint for block height checks
    """

    return 'http://localhost:8000/status.json' if DEBUG else 'http://' + NODE_IP + ':26657/status'


"""
######################################################################################################################################################
Jobs
######################################################################################################################################################
"""


def node_checks(context):
    """
    Periodic checks of various node stats
    """

    check_node_status(context)
    check_price_feeder(context)
    if NODE_IP:
        check_node_catch_up_status(context)
        check_node_block_height(context)


def check_node_status(context):
    """
    Check all added Terra Nodes for any changes.
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    # Flag to show home buttons or not
    message_sent = False

    # List to delete entries after loop
    delete_addresses = []

    # Iterate through all keys
    for address in user_data['nodes'].keys():
        remote_node = get_validator(address=address)
        local_node = user_data['nodes'][address]

        if remote_node is None:
            text = 'Node is not active anymore! 💀' + '\n' + \
                   'Address: ' + address + '\n\n' + \
                   'Please enter another Node address.'

            delete_addresses.append(address)

            # Send message
            context.bot.send_message(chat_id, text)
            message_sent = True
            continue

        # Check which node fields have changed
        changed_fields = [field for field in ['status', 'jailed'] if
                          local_node[field] != remote_node[field]]

        # Check if there are any changes
        if len(changed_fields) > 0:
            text = 'Node: ' + address + '\n' + \
                   'Status: ' + NODE_STATUSES[local_node['status']]
            if 'status' in changed_fields:
                text += ' ➡️ ' + NODE_STATUSES[remote_node['status']]
            text += '\nJailed: ' + str(local_node['jailed'])
            if 'jailed' in changed_fields:
                text += ' ➡️ ' + str(remote_node['jailed'])

            # Update data
            local_node['status'] = remote_node['status']
            local_node['jailed'] = remote_node['jailed']

            # Send message
            context.bot.send_message(chat_id, text)
            message_sent = True

    for address in delete_addresses:
        del user_data['nodes'][address]

    if message_sent:
        show_home_menu_new_msg(context=context, chat_id=chat_id)


def check_price_feeder(context):
    """
    Check Prevotes to make sure Price Feeder still works
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    for address in user_data['nodes'].keys():
        if 'is_price_feed_healthy' not in user_data:
            user_data['is_price_feed_healthy'] = True

        is_price_feed_currently_healthy = is_price_feed_healthy(address)
        if user_data['is_price_feed_healthy'] == True and not is_price_feed_currently_healthy:
            user_data['is_price_feed_healthy'] = False
            text = 'Price feed is not healthy anymore! 💀' + '\n' + \
                   'Address: ' + address
            context.bot.send_message(chat_id, text)
            show_home_menu_new_msg(context, chat_id=chat_id)
        elif user_data['is_price_feed_healthy'] == False and is_price_feed_currently_healthy:
            user_data['is_price_feed_healthy'] = True
            text = 'Price feed is healthy again! 👌' + '\n' + \
                   'Address: ' + address + '\n'
            context.bot.send_message(chat_id, text)
            show_home_menu_new_msg(context, chat_id=chat_id)

        
def check_node_catch_up_status(context):
    """
    Check if node is some blocks behind with catch up status
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    if 'is_catching_up' not in user_data:
        user_data['is_catching_up'] = False

    is_currently_catching_up = is_node_catching_up()
    if user_data['is_catching_up'] == False and is_currently_catching_up:
        user_data['is_catching_up'] = True
        text = 'The Node is behind the latest block height and catching up! 💀 ' + '\n' + \
               'IP: ' + NODE_IP + '\n' + \
               'Current block height: ' + get_node_block_height() + '\n\n' + \
               'Please check your Terra Node immediately!'
        context.bot.send_message(chat_id, text)
        show_home_menu_new_msg(context=context, chat_id=chat_id)
    elif user_data['is_catching_up'] == True and not is_currently_catching_up:
        user_data['is_catching_up'] = False
        text = 'The node caught up to the latest block height again! 👌' + '\n' + \
               'IP: ' + NODE_IP + '\n' + \
               'Current block height: ' + get_node_block_height()
        context.bot.send_message(chat_id, text)
        show_home_menu_new_msg(context=context, chat_id=chat_id)
        

def check_node_block_height(context):
    """
    Make sure the block height increases
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    block_height = get_node_block_height()

    # Check if block height got stuck
    if 'block_height' in user_data and block_height <= user_data['block_height']:
        # Increase stuck count to know if we already sent a notification
        user_data['block_height_stuck_count'] += 1
    else:
        # Check if we have to send a notification that the Height increases again
        if 'block_height_stuck_count' in user_data and user_data['block_height_stuck_count'] > 0:
            text = 'Block height is increasing again! 👌' + '\n' + \
                   'IP: ' + NODE_IP + '\n' + \
                   'Block height now at: ' + block_height + '\n'
            context.bot.send_message(chat_id, text)
            user_data['block_height_stuck_count'] = -1
        else:
            user_data['block_height_stuck_count'] = 0

    # Set current block height
    user_data['block_height'] = block_height

    # If it just got stuck send a message
    if user_data['block_height_stuck_count'] == 1:
        text = 'Block height is not increasing anymore! 💀' + '\n' + \
               'IP: ' + NODE_IP + '\n' + \
               'Block height stuck at: ' + block_height + '\n\n' + \
               'Please check your Terra Node immediately!'
        context.bot.send_message(chat_id, text)

    # Show buttons if there were changes or block height just got (un)stuck
    # Stuck count:
    # 0 == everthings alright
    # 1 == just got stuck
    # -1 == just got unstuck
    # > 1 == still stuck

    if user_data['block_height_stuck_count'] == 1 or user_data['block_height_stuck_count'] == -1:
        show_home_menu_new_msg(context=context, chat_id=chat_id)



def check_node_catch_up_status(context):
    """
    Check if node is some blocks behind with catch up status
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    if 'is_catching_up' not in user_data:
        user_data['is_catching_up'] = False

    is_currently_catching_up = is_node_catching_up()
    if user_data['is_catching_up'] == False and is_currently_catching_up:
        user_data['is_catching_up'] = True
        text = 'The Node is behind the latest block height and catching up! 💀 ' + '\n' + \
               'IP: ' + NODE_IP + '\n' + \
               'Current block height: ' + get_node_block_height() + '\n\n' + \
               'Please check your Terra Node immediately!'
        context.bot.send_message(chat_id, text)
        show_home_menu_new_msg(context=context, chat_id=chat_id)
    elif user_data['is_catching_up'] == True and not is_currently_catching_up:
        user_data['is_catching_up'] = False
        text = 'The node caught up to the latest block height again! 👌' + '\n' + \
               'IP: ' + NODE_IP + '\n' + \
               'Current block height: ' + get_node_block_height()
        context.bot.send_message(chat_id, text)
        show_home_menu_new_msg(context=context, chat_id=chat_id)


def check_node_block_height(context):
    """
    Make sure the block height increases
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    block_height = get_node_block_height()

    # Check if block height got stuck
    if 'block_height' in user_data and block_height <= user_data['block_height']:
        # Increase stuck count to know if we already sent a notification
        user_data['block_height_stuck_count'] += 1
    else:
        # Check if we have to send a notification that the Height increases again
        if 'block_height_stuck_count' in user_data and user_data['block_height_stuck_count'] > 0:
            text = 'Block height is increasing again! 👌' + '\n' + \
                   'IP: ' + NODE_IP + '\n' + \
                   'Block height now at: ' + block_height + '\n'
            context.bot.send_message(chat_id, text)
            user_data['block_height_stuck_count'] = -1
        else:
            user_data['block_height_stuck_count'] = 0

    # Set current block height
    user_data['block_height'] = block_height

    # If it just got stuck send a message
    if user_data['block_height_stuck_count'] == 1:
        text = 'Block height is not increasing anymore! 💀' + '\n' + \
               'IP: ' + NODE_IP + '\n' + \
               'Block height stuck at: ' + block_height + '\n\n' + \
               'Please check your Terra Node immediately!'
        context.bot.send_message(chat_id, text)

    # Show buttons if there were changes or block height just got (un)stuck
    # Stuck count:
    # 0 == everthings alright
    # 1 == just got stuck
    # -1 == just got unstuck
    # > 1 == still stuck

    if user_data['block_height_stuck_count'] == 1 or user_data['block_height_stuck_count'] == -1:
        show_home_menu_new_msg(context=context, chat_id=chat_id)


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
