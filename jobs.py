from datetime import datetime, timedelta

from constants import *
from helpers import *

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
    check_governance_proposals(context)
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
            try_message(context=context, chat_id=chat_id, text=text)
            message_sent = True
            continue

        # Check which node fields have changed
        changed_fields = [field for field in ['status', 'jailed', 'delegator_shares'] if
                          local_node[field] != remote_node[field]]

        # Check if there are any changes
        if len(changed_fields) > 0:
            text = 'Node: *' + address + '*\n' + \
                   'Status: *' + NODE_STATUSES[local_node['status']]
            if 'status' in changed_fields:
                text += '* ➡️ *' + NODE_STATUSES[remote_node['status']]
            text += '*\nJailed: *' + str(local_node['jailed'])
            if 'jailed' in changed_fields:
                text += '* ➡️ *' + str(remote_node['jailed'])
            text += '*\nDelegator Shares: *' + str(int(float(local_node['delegator_shares'])))
            if 'delegator_shares' in changed_fields:
                text += '* ➡️ *' + str(int(float(remote_node['delegator_shares'])))
            text += '*'

            # Update data
            local_node['status'] = remote_node['status']
            local_node['jailed'] = remote_node['jailed']
            local_node['delegator_shares'] = remote_node['delegator_shares']

            # Send message
            try_message(context=context, chat_id=chat_id, text=text)
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
            try_message(context=context, chat_id=chat_id, text=text)
            show_home_menu_new_msg(context, chat_id=chat_id)
        elif user_data['is_price_feed_healthy'] == False and is_price_feed_currently_healthy:
            user_data['is_price_feed_healthy'] = True
            text = 'Price feed is healthy again! 👌' + '\n' + \
                   'Address: ' + address + '\n'
            try_message(context=context, chat_id=chat_id, text=text)
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
        try_message(context=context, chat_id=chat_id, text=text)
        show_home_menu_new_msg(context=context, chat_id=chat_id)
    elif user_data['is_catching_up'] == True and not is_currently_catching_up:
        user_data['is_catching_up'] = False
        text = 'The node caught up to the latest block height again! 👌' + '\n' + \
               'IP: ' + NODE_IP + '\n' + \
               'Current block height: ' + get_node_block_height()
        try_message(context=context, chat_id=chat_id, text=text)
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
            try_message(context=context, chat_id=chat_id, text=text)
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
        try_message(context=context, chat_id=chat_id, text=text)

    # Show buttons if there were changes or block height just got (un)stuck
    # Stuck count:
    # 0 == everthings alright
    # 1 == just got stuck
    # -1 == just got unstuck
    # > 1 == still stuck

    if user_data['block_height_stuck_count'] == 1 or user_data['block_height_stuck_count'] == -1:
        show_home_menu_new_msg(context=context, chat_id=chat_id)


def check_governance_proposals(context):
    """
    Monitoring related to governance proposals
    """

    check_new_goverance_proposal(context)


def check_new_goverance_proposal(context):
    """
    Notify the user if there's a new governance proposals
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    governance_proposals = get_governance_proposals()
    governance_proposals_count = len(governance_proposals)

    if 'governance_proposals_count' not in user_data:
        user_data['governance_proposals_count'] = governance_proposals_count

    new_proposals_count = governance_proposals_count - user_data['governance_proposals_count']
    for i in range(new_proposals_count):
        current_proposal = governance_proposals[user_data['governance_proposals_count'] + i]

        voting_start_time = datetime.strptime(current_proposal['voting_start_time'][:-4], "%Y-%m-%dT%H:%M:%S.%f")
        voting_end_time = datetime.strptime(current_proposal['voting_end_time'][:-4], "%Y-%m-%dT%H:%M:%S.%f")

        text = 'A new governance proposal got submitted! 📣\n\n' + \
               '*Title:*\n' + current_proposal['content']['value']['title'] + '\n' + \
               '*Type:*\n' + current_proposal['content']['type'] + '\n' + \
               '*Description:*\n' + current_proposal['content']['value']['description'] + '\n\n' + \
               '*Voting Start Time:* ' + voting_start_time.strftime("%A %B %d, %H:%M") + ' UTC\n' + \
               '*Voting End Time:* ' + voting_end_time.strftime("%A %B %d, %H:%M") + ' UTC\n\n' + \
               'Make sure to vote on this governance proposal until *' + voting_end_time.strftime(
            "%A %B %d, %H:%M") + ' UTC*!'

        try_message(context=context, chat_id=chat_id, text=text)

    user_data['governance_proposals_count'] = governance_proposals_count

    if new_proposals_count:
        show_home_menu_new_msg(context=context, chat_id=chat_id)
