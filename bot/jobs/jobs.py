import copy

import requests

from constants.constants import NODE_STATUS_ENDPOINT, NODE_STATUSES
from constants.env_variables import NODE_IP
from constants.logger import logger
from helpers import is_lcd_reachable, try_message_to_all_platforms, get_validator, is_price_feed_healthy, \
    is_node_catching_up, get_node_block_height, try_message
from service.governance_service import get_governance_proposals, proposal_to_text

"""
######################################################################################################################################################
Jobs
######################################################################################################################################################
"""


def node_checks(context):
    """
    Periodic checks of various node stats
    """

    if check_lcd_reachable(context):
        check_node_status(context)
        check_price_feeder(context)
        check_governance_proposals(context)
    if NODE_IP and check_node_reachable(context):
        check_node_catch_up_status(context)
        check_node_block_height(context)


def check_lcd_reachable(context):
    """
    Returns whether the public Lite Client Daemon (LCD) is reachable and informs user
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    if 'is_lcd_reachable' not in user_data:
        user_data['is_lcd_reachable'] = True

    is_lcd_currently_reachable = is_lcd_reachable()

    if user_data['is_lcd_reachable'] == True and not is_lcd_currently_reachable:
        user_data['is_lcd_reachable'] = False
        text = 'The public Lite Client Daemon (LCD) cannot be reached! 💀' + '\n' + \
               'Node monitoring will be restricted to node specific attributes until it is reachable again.'
        try_message_to_all_platforms(context=context, chat_id=chat_id, text=text)
    elif user_data['is_lcd_reachable'] == False and is_lcd_currently_reachable:
        user_data['is_lcd_reachable'] = True
        text = 'The public Lite Client Daemon (LCD) is reachable again! 👌' + '\n' + \
               'Monitoring of publicly available node attributes resumes.'
        try_message_to_all_platforms(context=context, chat_id=chat_id, text=text)

    return is_lcd_currently_reachable


def check_node_reachable(context):
    """
    Returns whether the specified node IP is reachable and informs user
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    if 'is_node_reachable' not in user_data:
        user_data['is_node_reachable'] = True

    response = requests.get(NODE_STATUS_ENDPOINT)
    if response.status_code == 200:
        is_node_currently_reachable = True
    else:
        is_node_currently_reachable = False

    if user_data['is_node_reachable'] == True and not is_node_currently_reachable:
        user_data['is_node_reachable'] = False
        text = 'The specified Node cannot be reached! 💀' + '\n' + \
               'IP: ' + NODE_IP + '\n' + \
               'Node monitoring will be restricted to publicly available node attributes until it is reachable again.' + '\n\n' + \
               'Please check your Terra Node immediately!'
        try_message_to_all_platforms(context=context, chat_id=chat_id, text=text)
    elif user_data['is_node_reachable'] == False and is_node_currently_reachable:
        user_data['is_node_reachable'] = True
        text = 'The specified Node is reachable again! 👌' + '\n' + \
               'Monitoring of node specific attributes resumes.'
        try_message_to_all_platforms(context=context, chat_id=chat_id, text=text)

    return is_node_currently_reachable


def check_node_status(context):
    """
    Check all added Terra Nodes for any changes.
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    # List to delete entries after loop
    delete_addresses = []

    # Iterate through all keys
    for address in user_data.get('nodes', {}).keys():
        try:
            remote_node = get_validator(address=address)
        except ConnectionError:
            continue

        local_node = user_data['nodes'][address]

        if remote_node is None:
            text = 'Node is not active anymore! 💀' + '\n' + \
                   'Address: ' + address + '\n\n' + \
                   'Please enter another Node address.'

            delete_addresses.append(address)

            # Send message
            try_message_to_all_platforms(context=context, chat_id=chat_id, text=text)
            continue

        # Check which node fields have changed
        changed_fields = [
            field for field in ['status', 'jailed', 'delegator_shares'] if local_node[field] != remote_node[field]
        ]

        # Check if there are any changes
        if len(changed_fields) > 0:
            text = f'Node: *{address}*\n' \
                   f'Status: *{NODE_STATUSES[local_node["status"]]}*'
            if 'status' in changed_fields:
                text += f' ➡️ *{NODE_STATUSES[remote_node["status"]]}*'
            text += f'\nJailed: *{local_node["jailed"]}*'
            if 'jailed' in changed_fields:
                text += f' ➡️ *{remote_node["jailed"]}*'
            local_delegator_shares = int(float(local_node["delegator_shares"]))
            text += f'\nDelegator Shares: *{local_delegator_shares}*'
            if 'delegator_shares' in changed_fields:
                remote_delegator_shares = int(float(remote_node['delegator_shares']))
                delta = remote_delegator_shares - local_delegator_shares
                delta = str(delta) if (delta < 0) else f"+{delta}"
                text += f' ➡️ *{remote_delegator_shares}* (*Δ* {delta})'

            # Update data
            local_node['status'] = remote_node['status']
            local_node['jailed'] = remote_node['jailed']
            local_node['delegator_shares'] = remote_node['delegator_shares']

            # Send message
            try_message_to_all_platforms(context=context, chat_id=chat_id, text=text)

    for address in delete_addresses:
        del user_data['nodes'][address]


def check_price_feeder(context):
    """
    Check Prevotes to make sure Price Feeder still works
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    for address in user_data.get('nodes', {}).keys():
        if 'is_price_feed_healthy' not in user_data:
            user_data['is_price_feed_healthy'] = True

        try:
            is_price_feed_currently_healthy = is_price_feed_healthy(address)
        except ConnectionError:
            continue

        if user_data['is_price_feed_healthy'] == True and not is_price_feed_currently_healthy:
            user_data['is_price_feed_healthy'] = False
            text = 'Price feed is not healthy anymore! 💀' + '\n' + \
                   'Address: ' + address
            try_message_to_all_platforms(context=context, chat_id=chat_id, text=text)
        elif user_data['is_price_feed_healthy'] == False and is_price_feed_currently_healthy:
            user_data['is_price_feed_healthy'] = True
            text = 'Price feed is healthy again! 👌' + '\n' + \
                   'Address: ' + address + '\n'
            try_message_to_all_platforms(context=context, chat_id=chat_id, text=text)


def check_node_catch_up_status(context):
    """
    Check if node is some blocks behind with catch up status
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    if 'is_catching_up' not in user_data:
        user_data['is_catching_up'] = False

    try:
        is_currently_catching_up = is_node_catching_up()
        block_height = get_node_block_height()
    except ConnectionError:
        return

    if user_data['is_catching_up'] == False and is_currently_catching_up:
        user_data['is_catching_up'] = True
        text = 'The Node is behind the latest block height and catching up! 💀 ' + '\n' + \
               'IP: ' + NODE_IP + '\n' + \
               'Current block height: ' + block_height + '\n\n' + \
               'Please check your Terra Node immediately!'
        try_message_to_all_platforms(context=context, chat_id=chat_id, text=text)
    elif user_data['is_catching_up'] == True and not is_currently_catching_up:
        user_data['is_catching_up'] = False
        text = 'The node caught up to the latest block height again! 👌' + '\n' + \
               'IP: ' + NODE_IP + '\n' + \
               'Current block height: ' + block_height
        try_message_to_all_platforms(context=context, chat_id=chat_id, text=text)


def check_node_block_height(context):
    """
    Make sure the block height increases
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    try:
        block_height = get_node_block_height()
    except ConnectionError:
        return

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
            try_message_to_all_platforms(context=context, chat_id=chat_id, text=text)
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
        try_message_to_all_platforms(context=context, chat_id=chat_id, text=text)

    # Show buttons if there were changes or block height just got (un)stuck
    # Stuck count:
    # 0 == everthings alright
    # 1 == just got stuck
    # -1 == just got unstuck
    # > 1 == still stuck


def check_governance_proposals(context):
    """
    Monitoring related to governance proposals
    """

    try:
        governance_proposals = get_governance_proposals()
    except ConnectionError as e:
        logger.error(e)
        return

    check_new_goverance_proposal(context, governance_proposals)
    check_results_of_proposals(context, governance_proposals)


def check_new_goverance_proposal(context, governance_proposals):
    """
    Notify the user if there's a new governance proposals
    """

    chat_id = context.job.context['chat_id']
    user_data = context.job.context['user_data']

    governance_proposals_count = len(governance_proposals)

    if 'governance_proposals_count' not in user_data:
        user_data['governance_proposals_count'] = governance_proposals_count

    new_proposals_count = governance_proposals_count - user_data['governance_proposals_count']
    for i in range(new_proposals_count):
        current_proposal = governance_proposals[user_data['governance_proposals_count'] + i]

        text = 'A new governance proposal got submitted! 📣\n\n'
        text += proposal_to_text(current_proposal)

        try_message_to_all_platforms(context=context, chat_id=chat_id, text=text)

    user_data['governance_proposals_count'] = governance_proposals_count


def check_results_of_proposals(context, governance_proposals):
    user_data = context.job.context['user_data']

    active_proposals = list(filter(lambda p: p['proposal_status'] == 'VotingPeriod', governance_proposals))
    monitored_active_proposals = copy.deepcopy(user_data.setdefault('monitored_active_proposals', []))

    # save new proposals
    for proposal in active_proposals:
        if proposal['id'] not in monitored_active_proposals:
            user_data['monitored_active_proposals'].append(proposal['id'])

    # send notifications
    for proposal_id in monitored_active_proposals:
        is_past = proposal_id not in map(lambda p: p['id'], active_proposals)

        if is_past:
            past_proposal = next(filter(lambda p: p['id'] == proposal_id, governance_proposals), None)
            user_data['monitored_active_proposals'].remove(proposal_id)
            results = past_proposal['final_tally_result']

            message = "* ‼️ This proposal has ended ‼️*\n\n" \
                      f"{proposal_to_text(past_proposal)}\n\n" \
                      "*Results:*\n\n" \
                      f"*✅ Yes*: {results['yes']}\n" \
                      f"*❌ No*: {results['no']}\n" \
                      f"*❌❌ No with veto*: {results['no_with_veto']}\n" \
                      f"*🤷 Abstain*: {results['abstain']}\n"

            try_message(context=context, chat_id=context.job.context['chat_id'], text=message)
