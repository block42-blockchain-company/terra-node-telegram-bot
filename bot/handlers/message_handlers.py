from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest

from constants.constants import JOB_INTERVAL_IN_SECONDS
from constants.messages import HELLO_MSG
from handlers.governance_handlers import on_authorize_voting_clicked, on_show_governance_menu_clicked, \
    on_vote_option_clicked, \
    on_proposal_clicked, on_show_active_proposals_clicked, on_show_all_proposals_clicked, \
    on_vote_send_clicked
from helpers import try_message_with_home_menu, show_my_nodes_paginated, show_detail_menu, get_home_menu_buttons, \
    get_validator, add_node_to_user_data, show_confirmation_menu, get_validators
from jobs.jobs import node_checks


def start(update, context):
    """
    Send start message and display action buttons.
    """

    context.user_data['expected'] = None

    # Start job for user
    if 'job_started' not in context.user_data:
        context.job_queue.run_repeating(node_checks,
                                        interval=JOB_INTERVAL_IN_SECONDS,
                                        context={
                                            'chat_id': update.message.chat.id,
                                            'user_data': context.user_data
                                        })
        context.user_data['job_started'] = True
        context.user_data['nodes'] = {}

    text = HELLO_MSG

    # Send message
    try_message_with_home_menu(context=context, chat_id=update.effective_chat.id, text=text)


def cancel(update, context):
    """
    Go back to home menu
    """

    context.user_data['expected'] = None
    show_my_nodes_paginated(context=context, chat_id=update.effective_chat.id)


def dispatch_query(update, context):
    query = update.callback_query
    query.answer()
    data = query.data

    context.user_data['expected'] = None
    edit = True
    call = None

    if data == 'home':
        call = show_home_menu_edit_msg
    elif data == 'my_nodes':
        def show_nodes_from_back_button(update, context):
            show_my_nodes_paginated(context=context, chat_id=update.effective_chat.id)

        call = show_nodes_from_back_button
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
    elif data.startswith('node_details'):
        call = node_details
    elif data == 'confirm_node_deletion':
        call = confirm_node_deletion
    elif data == 'delete_node':
        call = delete_node
    elif data == 'show_detail_menu':
        call = show_detail_menu
    elif data == 'show_governance_menu':
        def show_gov_menu(update, context):
            on_show_governance_menu_clicked(context=context, chat_id=update.effective_chat.id,
                                            user_id=update.effective_user['id'])

        call = show_gov_menu
    elif data == 'proposals_show_all':
        call = on_show_all_proposals_clicked
    elif data == 'proposals_show_active':
        call = on_show_active_proposals_clicked
    elif data == 'authorize_voting':
        call = on_authorize_voting_clicked
    elif data.startswith('proposal-'):
        call = on_proposal_clicked
    elif data.startswith('vote-'):
        call = on_vote_option_clicked
    elif data.startswith('votesend-'):
        call = on_vote_send_clicked
    else:
        edit = False

    # Catch any 'Message is not modified' error by removing the keyboard
    if edit:
        try:
            context.bot.edit_message_reply_markup(reply_markup=None,
                                                  chat_id=update.callback_query.message.chat_id,
                                                  message_id=update.callback_query.message.message_id)
        except BadRequest as e:
            if 'Message is not modified' not in e.message:
                raise

    if call:
        return call(update, context)


def plain_input(update, context):
    """
    Handle if the users sends a message
    """

    message = update.message.text
    expected = context.user_data['expected'] if 'expected' in context.user_data else None
    if message == '📡 My Nodes':
        return show_my_nodes_paginated(context=context, chat_id=update.effective_chat.id)
    elif message == '🗳 Governance':
        return on_show_governance_menu_clicked(context=context, chat_id=update.effective_chat.id,
                                               user_id=update.message.from_user['id'])
    elif expected == 'add_node':
        context.user_data['expected'] = None
        return handle_add_node(update, context)


def show_home_menu_edit_msg(update, context):
    """
    Edit current message with the home menu
    """

    keyboard = get_home_menu_buttons()
    text = 'I am your Terra Node Bot. 🤖\nClick *MY NODES* to get information about the Terra Nodes you monitor!'
    query = update.callback_query
    query.edit_message_text(text,
                            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
                            parse_mode='markdown')


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
        return show_my_nodes_paginated(context=context, chat_id=update.effective_chat.id)

    if node is None:
        context.user_data['expected'] = 'add_node'
        return update.message.reply_text('⛔️ I have not found a Node with this address! ⛔\n'
                                         'Please try another one. (enter /cancel to return to the menu)')

    add_node_to_user_data(context.user_data, address, node)
    context.bot.send_message(update.effective_chat.id, 'Got it! 👌')
    return show_my_nodes_paginated(context=context, chat_id=update.effective_chat.id)


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


def confirm_delete_all_nodes(update, _):
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

    nodes = get_validators()

    for node in nodes:
        address = node['operator_address']
        if address not in context.user_data['nodes']:
            add_node_to_user_data(context.user_data, address, node)

    # Send message
    query.edit_message_text('Added all Terra Nodes! 👌')
    show_my_nodes_paginated(context, chat_id=update.effective_chat.id)


def delete_all_nodes(update, context):
    """
    Delete all node addresses from users monitoring list
    """

    query = update.callback_query

    context.user_data['nodes'].clear()

    text = '❌ Deleted all Terra Nodes! ❌'
    # Send message
    query.edit_message_text(text)

    show_my_nodes_paginated(context, chat_id=update.effective_chat.id)


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
    show_my_nodes_paginated(context=context, chat_id=update.effective_chat.id)
