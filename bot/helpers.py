import json

import requests
from jigu.core.msg import MsgVote
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, TelegramError, KeyboardButton, ReplyKeyboardMarkup
from requests.exceptions import RequestException

from constants import *
from messages import NETWORK_ERROR_MSG
from service.governance_service import get_all_proposals_as_messages, get_active_proposals, get_proposal_by_id, \
    jigu_proposal_to_text, get_my_vote, vote_on_proposal, is_wallet_provided

"""
######################################################################################################################################################
Helpers
######################################################################################################################################################
"""


def try_message_with_home_menu(context, chat_id, text):
    keyboard = get_home_menu_buttons()
    try_message(context=context,
                chat_id=chat_id,
                text=text,
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))


def show_my_nodes_menu_new_msg(context, chat_id):
    """
    Show My Nodes Menu
    """

    user_data = context.user_data if context.user_data else context.job.context['user_data']

    keyboard = get_my_nodes_menu_buttons(user_data=user_data)
    text = 'Click an address from the list below or add a node:' if len(keyboard) > 2 else 'You do not monitor any ' \
                                                                                           'Terra Nodes yet.\nAdd a Node!'

    try_message(context=context, chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))


def show_governance_menu(context, chat_id):
    text = 'Click an option'

    keyboard = [[InlineKeyboardButton("🗳 Show all proposals", callback_data='governance_all')],
                [InlineKeyboardButton("🗳 ✅ Show active proposals and vote", callback_data='governance_active')]]

    try_message(context=context, chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))


def get_home_menu_buttons():
    """
    Return Keyboard buttons for the My Nodes menu
    """

    keyboard = [[KeyboardButton('📡 My Nodes'), KeyboardButton('🗳 Governance')]]

    return keyboard


def get_my_nodes_menu_buttons(user_data):
    """
    Return Keyboard buttons for the My Nodes menu
    """

    keyboard = [[]]

    for address in user_data['nodes'].keys():
        keyboard.append([InlineKeyboardButton("📡 " + address, callback_data='node_details-' + address)])

    keyboard.append([InlineKeyboardButton('1️⃣ ADD NODE', callback_data='add_node')])
    keyboard.append([
        InlineKeyboardButton('➕ ADD ALL', callback_data='confirm_add_all_nodes'),
        InlineKeyboardButton('➖ REMOVE ALL', callback_data='confirm_delete_all_nodes')
    ])

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


def on_show_all_proposals_clicked(update, context):
    query = update.callback_query

    messages = get_all_proposals_as_messages()
    query.edit_message_text("All proposals")

    for message in messages:
        try_message(context, query['message']['chat']['id'], message, reply_markup=None)


def on_show_active_proposals_clicked(update, context):
    query = update.callback_query

    try:
        active_proposals = get_active_proposals()
    except Exception as e:
        logger.error(e, exc_info=True)
        try_message(context=context, chat_id=query['message']['chat']['id'], text=NETWORK_ERROR_MSG)
        return

    text = '🗳 ✅ **Active proposals**🗳 ✅ \n' \
           'Click on any of the proposals to see details and vote options.\n\n'

    keyboard = [[]]

    if not active_proposals:
        text += "No active proposals at the moment."
    else:
        for proposal in active_proposals:
            button = InlineKeyboardButton(str(proposal.content.title), callback_data=f'proposal-{proposal.id}')
            keyboard.append([button])

    try_message(context=context,
                chat_id=query['message']['chat']['id'],
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard))


def vote_on_proposal_details(update, context):
    query = update.callback_query
    proposal_id = query.data.split("-")[-1]
    user_id = query.from_user['id']

    try:
        proposal = get_proposal_by_id(proposal_id)
        context.user_data.setdefault('proposals_cache', {})[proposal_id] = {'title': proposal.content.title}
    except Exception as e:
        logger.error(e)
        query.edit_message_text(NETWORK_ERROR_MSG)
        return

    keyboard = [[InlineKeyboardButton('⬅️ BACK', callback_data='governance_active')]]
    message = ''

    if not is_wallet_provided():
        message = f"😢 *You can't vote, no MNEMONIC key provided.* 😢"
    elif user_id not in ALLOWED_USER_IDS:
        message = f'😢 *You are not allowed to vote because your id ({user_id}) is not whitelisted!* 😢'
    else:
        try:
            my_vote = get_my_vote(proposal_id)
        except Exception as e:
            logger.error(e, exc_info=True)
            query.edit_message_text(NETWORK_ERROR_MSG)
            return

        if my_vote:
            message = f'🎉 You voted *{my_vote}* 🎉'
        else:
            keyboard = [
                [
                    InlineKeyboardButton('✅ Yes', callback_data=f'vote-{proposal_id}-{MsgVote.YES}'),
                    InlineKeyboardButton('❌ No', callback_data=f'vote-{proposal_id}-{MsgVote.NO}'),
                ],
                [
                    InlineKeyboardButton('❌❌ No with veto',
                                         callback_data=f'vote-{proposal_id}-{MsgVote.NO_WITH_VETO}'),
                    InlineKeyboardButton('🤷 Abstain', callback_data=f'vote-{proposal_id}-{MsgVote.ABSTAIN}'),
                ],
                [InlineKeyboardButton('⬅️ BACK', callback_data='governance_active')]
            ]

    message += f"\n\n\n{jigu_proposal_to_text(proposal)}"

    query.edit_message_text(message, parse_mode='markdown', reply_markup=InlineKeyboardMarkup(keyboard))


def on_vote_clicked(update, context):
    query = update.callback_query
    _, proposal_id, vote = query.data.split("-")
    proposal_title = context.user_data['proposals_cache'][proposal_id]['title']

    keyboard = [[
        InlineKeyboardButton('YES ✅', callback_data=f'vote_confirmed-{proposal_id}-{vote}'),
        InlineKeyboardButton('NO ❌', callback_data=f'proposal-{proposal_id}')
    ]]
    text = f'⚠️ Do you really want to vote *{vote}* on proposal *{proposal_title}*? ⚠️'

    query.edit_message_text(text, parse_mode='markdown', reply_markup=InlineKeyboardMarkup(keyboard))


def vote_accept(update, _):
    query = update.callback_query
    _, proposal_id, vote = query.data.split("-")
    keyboard = [[InlineKeyboardButton('⬅️ BACK', callback_data=f'proposal-{proposal_id}')]]

    try:
        vote_result = vote_on_proposal(proposal_id=proposal_id, vote_option=vote)
        logger.info(f"Voted successfully. Transaction result:\n{vote_result}")
    except Exception as e:
        logger.error(e)
        message = NETWORK_ERROR_MSG
        if hasattr(e, 'doc'):
            message = "😱 There was an error while voting 😱.\n Error details:\n\n"
            message += e.doc

        query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    query.edit_message_text(f"Successfully voted *{vote}* on proposal with id *{proposal_id}*",
                            parse_mode='markdown',
                            reply_markup=InlineKeyboardMarkup(keyboard))


def show_confirmation_menu(update, text, keyboard):
    """
    "Are you sure?" - "YES" | "NO"
    """

    query = update.callback_query

    query.edit_message_text(text, parse_mode='markdown', reply_markup=InlineKeyboardMarkup(keyboard))


def send_message_to_all_platforms(context, chat_id, text):
    try_message_with_home_menu(context=context, chat_id=chat_id, text=text)
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
            logger.info("ConnectionError while requesting https://lcd.terra.dev/oracle/voters/" + address +
                        "/prevotes")
            raise ConnectionError
        return response.json()
