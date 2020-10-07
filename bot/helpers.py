import json

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, TelegramError
from requests.exceptions import RequestException
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

    keyboard.append([InlineKeyboardButton('➕ ADD ALL', callback_data='confirm_add_all_nodes'),
                     InlineKeyboardButton('➕ ADD NODE', callback_data='add_node')])
    keyboard.append([InlineKeyboardButton('➖ REMOVE ALL', callback_data='confirm_delete_all_nodes'),
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


def show_confirmation_menu(update, text, keyboard):
    """
    "Are you sure?" - "YES" | "NO"
    """

    query = update.callback_query

    query.edit_message_text(text, parse_mode='markdown', reply_markup=InlineKeyboardMarkup(keyboard))


def send_message_to_all_platforms(context, chat_id, text, reply_markup=None):
    try_message(context=context, chat_id=chat_id, text=text, reply_markup=reply_markup)
    send_slack_message(text)


def send_slack_message(text):
    if SLACK_WEBHOOK:
        try:
            requests.post(SLACK_WEBHOOK, data=json.dumps({'text': text}), headers={'Content-Type': 'application/json'})
        except RequestException as e:
            logger.error(f"Slack Webhook post request failed with:\n{e}")


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
                if os.path.exists("./storage/session.data"):
                    os.remove("./storage/session.data")
            context.job.enabled = False
            context.job.schedule_removal()
        else:
            print("Got Error\n" + str(e) + "\nwith telegram user " + str(chat_id))


def add_node_to_user_data(user_data, address, node):
    """
    Add a node in the user specific dictionary
    """

    user_data['nodes'][address] = {}
    user_data['nodes'][address]['status'] = node['status']
    user_data['nodes'][address]['jailed'] = node['jailed']
    user_data['nodes'][address]['delegator_shares'] = node['delegator_shares']


def get_validators() -> dict:
    """
    Return json of all validator nodes
    """

    if DEBUG:
        # Get local validator file
        response = requests.get(VALIDATORS_ENDPOINT)
        if response.status_code != 200:
            logger.info("ConnectionError while requesting " + VALIDATORS_ENDPOINT)
            raise ConnectionError
        nodes = response.json()
        return nodes['result']
    else:
        response = requests.get(VALIDATORS_ENDPOINT)
        if response.status_code != 200:
            if not is_lcd_reachable():
                logger.info("ConnectionError while requesting " + NODE_INFO_ENDPOINT)
                raise ConnectionError
            else:
                return None

        nodes = response.json()
        return nodes['result']


def get_validator(address) -> dict:
    """
    Return json of desired validator node
    """

    if DEBUG:
        nodes = get_validators()
        # Get the right node
        node = next(filter(lambda node: node['operator_address'] == address, nodes), None)
        return node
    else:
        response = requests.get(VALIDATORS_ENDPOINT + "/" + address)
        if response.status_code != 200:
            if not is_lcd_reachable():
                logger.info("ConnectionError while requesting " + NODE_INFO_ENDPOINT)
                raise ConnectionError
            else:
                return None

        node = response.json()
        return node['result']


def is_node_catching_up():
    response = requests.get(url=NODE_STATUS_ENDPOINT)
    if response.status_code != 200:
        logger.info("ConnectionError while requesting " + NODE_STATUS_ENDPOINT)
        raise ConnectionError

    status = response.json()
    return status['result']['sync_info']['catching_up']


def is_lcd_reachable():
    """
    Check whether the public Lite Client Daemon (LCD) is reachable
    """

    response = requests.get(NODE_INFO_ENDPOINT)
    return True if response.status_code == 200 else False


def get_node_block_height():
    """
    Return block height of your Terra Node
    """

    response = requests.get(url=NODE_STATUS_ENDPOINT)
    if response.status_code != 200:
        logger.info("ConnectionError while requesting " + NODE_STATUS_ENDPOINT)
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

    response = requests.get(url=GOVERNANCE_PROPOSAL_ENDPOINT)
    if response.status_code != 200:
        logger.info("ConnectionError while requesting " + GOVERNANCE_PROPOSAL_ENDPOINT)
        raise ConnectionError

    governance_proposals = response.json()
    return governance_proposals['result']
