import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, TelegramError

from constants import *

"""
######################################################################################################################################################
Helpers
######################################################################################################################################################
"""


def show_home_menu_new_msg(context, chat_id):
    """
    Send a new message with the home menu
    """

    keyboard = get_home_menu_buttons()
    text = 'I am your Terra Node Bot. 🤖\nClick *MY NODES* to get information about the Terra Nodes you monitor!'
    try_message(context=context, chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))


def show_my_nodes_menu_new_msg(context, chat_id):
    """
    Show My Nodes Menu
    """

    user_data = context.user_data if context.user_data else context.job.context['user_data']

    keyboard = get_my_nodes_menu_buttons(user_data=user_data)
    text = 'Click an address from the list below or add a node:' if len(keyboard) > 2 else 'You do not monitor any ' \
                                                                                        'Terra Nodes yet.\nAdd a Node!'

    try_message(context=context, chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))


def get_home_menu_buttons():
    """
    Return Keyboard buttons for the My Nodes menu
    """

    keyboard = [[InlineKeyboardButton('📡 MY NODES', callback_data='my_nodes')]]

    return keyboard


def get_my_nodes_menu_buttons(user_data):
    """
    Return Keyboard buttons for the My Nodes menu
    """

    keyboard = [[]]

    for address in user_data['nodes'].keys():
        keyboard.append([InlineKeyboardButton("📡 " + address, callback_data='node_details-' + address)])

    keyboard.append([InlineKeyboardButton('➕ ADD NODE', callback_data='add_node'),
                     InlineKeyboardButton('⬅️ BACK', callback_data='home')])

    return keyboard


def show_detail_menu(update, context):
    """
    Show detail buttons for selected address
    """

    query = update.callback_query
    address = context.user_data['selected_node_address']

    text = 'Node: *' + address + '*\n' + \
           'Status: *' + NODE_STATUSES[context.user_data['nodes'][address]['status']] + '*\n' + \
           'Jailed: *' + str(context.user_data['nodes'][address]['jailed']) + '*\n' + \
           'Delegator Shares: *' + str(int(float(context.user_data['nodes'][address]['delegator_shares']))) + '*\n\n'

    text += "What do you want to do with that Node?"

    keyboard = [[
        InlineKeyboardButton('➖ DELETE NODE', callback_data='confirm_node_deletion'),
        InlineKeyboardButton('⬅️ BACK', callback_data='my_nodes')
        ]]

    # Modify message
    query.edit_message_text(text, parse_mode='markdown', reply_markup=InlineKeyboardMarkup(keyboard))


def try_message(context, chat_id, text, reply_markup=None):
    """
    Send a message to a user.
    """

    if context.job and not context.job.enabled:
        return

    try:
        context.bot.send_message(chat_id, text, parse_mode='markdown', reply_markup=reply_markup)
    except TelegramError as e:
        if 'bot was blocked by the user' in e.message:
            print("Telegram user " + str(chat_id) + " blocked me; removing him from the user list")
            del context.dispatcher.user_data[chat_id]
            del context.dispatcher.chat_data[chat_id]
            del context.dispatcher.persistence.user_data[chat_id]
            del context.dispatcher.persistence.chat_data[chat_id]

            # Somehow session.data does not get updated if all users block the bot.
            # That makes problems on bot restart. That's why we delete the file ourselves.
            if len(context.dispatcher.persistence.user_data) == 0:
                if os.path.exists("storage/session.data"):
                    os.remove("storage/session.data")
            context.job.enabled = False
            context.job.schedule_removal()
        else:
            print("Got Error\n" + str(e) + "\nwith telegram user " + str(chat_id))


def get_validator(address):
    """
    Return json of desired validator node
    """

    if DEBUG:
        # Get local validator file
        response = requests.get(get_validators_endpoint())
        if response.status_code != 200:
            logger.info("ConnectionError while requesting " + get_validators_endpoint())
            raise ConnectionError
        nodes = response.json()
        # Get the right node
        node = next(filter(lambda node: node['operator_address'] == address, nodes['result']), None)
        return node
    else:
        response = requests.get(get_validators_endpoint() + "/" + address)
        if response.status_code != 200:
            if not is_lcd_reachable:
                logger.info("ConnectionError while requesting " + get_node_info_endpoint())
                raise ConnectionError
            else:
                return None

        node = response.json()
        return node['result']


def is_node_catching_up():
    url = get_node_status_endpoint()
    response = requests.get(url=url)
    if response.status_code != 200:
        logger.info("ConnectionError while requesting " + url)
        raise ConnectionError

    status = response.json()
    return status['result']['sync_info']['catching_up']


def is_lcd_reachable():
    """
    Check whether the public Lite Client Daemon (LCD) is reachable
    """

    response = requests.get(get_node_info_endpoint())
    return True if response.status_code == 200 else False


def get_node_block_height():
    """
    Return block height of your Terra Node
    """

    url = get_node_status_endpoint()
    response = requests.get(url=url)
    if response.status_code != 200:
        logger.info("ConnectionError while requesting " + url)
        raise ConnectionError

    status = response.json()
    return status['result']['sync_info']['latest_block_height']


def is_price_feed_healthy(address):
    """
    Check whether price feed is working properly
    """

    try:
        prevotes = get_price_feed_prevotes(address)
    except ConnectionError:
        raise

    for prevote in prevotes['result']:
        if int(prevote['submit_block']) < int(prevotes['height']) - 10:
            return False

    return True


def get_price_feed_prevotes(address):
    """
    Return the current prevotes oracle json
    """

    if DEBUG:
        # Get local prevotes file
        response = requests.get('http://localhost:8000/prevotes.json')
        if response.status_code != 200:
            logger.info("ConnectionError while requesting http://localhost:8000/prevotes.json")
            raise ConnectionError
        return response.json()
    else:
        response = requests.get('https://lcd.terra.dev/oracle/voters/' + address + '/prevotes')
        if response.status_code != 200:
            logger.info("ConnectionError while requesting https://lcd.terra.dev/oracle/voters/" + address + "/prevotes")
            raise ConnectionError
        return response.json()


def get_governance_proposals():
    """
    Return all governance proposals
    """

    response = requests.get(url=get_governance_proposal_endpoint())
    if response.status_code != 200:
        logger.info("ConnectionError while requesting " + get_governance_proposal_endpoint())
        raise ConnectionError

    governance_proposals = response.json()
    return governance_proposals['result']


def get_validators_endpoint():
    """
    Return the endpoint for the validator nodes
    """

    return 'http://localhost:8000/validators.json' if DEBUG else 'https://lcd.terra.dev/staking/validators'


def get_node_status_endpoint():
    """
    Return the endpoint for block height checks
    """

    return 'http://localhost:8000/status.json' if DEBUG else 'http://' + NODE_IP + ':26657/status'


def get_governance_proposal_endpoint():
    """
    Return the endpoint of governance proposals
    """

    return 'http://localhost:8000/governance_proposals.json' if DEBUG else 'https://lcd.terra.dev/gov/proposals'


def get_node_info_endpoint():
    """
    Return the endpoint of the node info
    """

    return 'https://lcd.terra.dev/node_info'

