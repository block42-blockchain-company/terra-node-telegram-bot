from typing import Callable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LoginUrl
from terra_sdk.core.gov import MsgVote

from constants.constants import WEBSITE_URL, BLOCK42_TERRA_BOT_USERNAME, TERRA_FINDER_URL
from constants.env_variables import NETWORK
from constants.logger import logger
from constants.messages import NO_PROPOSALS_MSG, NETWORK_ERROR_MSG, YOU_WILL_BE_REDIRECTED_MSG, BACK_BUTTON_MSG
from helpers import try_message
from service.governance_service import get_active_proposals, get_proposal, proposal_to_text, get_vote, \
    get_governance_proposals
from service.vote_delegation_service import get_wallet_addr, vote_delegated


def on_show_governance_menu_clicked(context, chat_id, user_id):
    text = 'Click an option\n\n'

    user_wallet_addr = get_wallet_addr(user_id)
    context.user_data.setdefault('proposals_cache', {})['wallet'] = user_wallet_addr

    if user_wallet_addr is None:
        text += "You haven't authorized voting, but you can still" \
                " vote using Terra Station Extension on Chrome.\n" \
                "To vote directly from Telegram use *Delegate voting* feature."
    else:
        text += 'You authorized voting! 🎉\n' \
                'You can vote directly from Telegram.'

    keyboard = [
        [InlineKeyboardButton("🗳 ✅ Show active proposals and vote",
                              callback_data='proposals_show_active')],
        [InlineKeyboardButton("🗳 Show all proposals", callback_data='proposals_show_all')]]

    if user_wallet_addr is None:
        keyboard.append(
            [InlineKeyboardButton("📝 Authorize me and vote directly from Telegram!",
                                  callback_data='authorize_voting')])

    try_message(context=context, chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))


def on_show_all_proposals_clicked(update, context):
    query = update.callback_query
    _ = query.data.split("-")

    try:
        proposals = get_governance_proposals()
    except Exception as e:
        logger.error(e, exc_info=True)
        try_message(context=context, chat_id=query['message']['chat']['id'], text=NETWORK_ERROR_MSG)
        return

    title = '🗳 ✅ **All proposals**🗳 ✅ \n' \
            'Click on any of the proposals to see details.\n\n'

    def button_builder(proposal_title: str, proposal_id: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(proposal_title,
                                    callback_data=f'proposal-{proposal_id}-0')  # 0 - open read only view

    _display_proposals(proposals=proposals, query=query, title=title,
                       button_builder=button_builder)


def on_show_active_proposals_clicked(update, context):
    query = update.callback_query
    _ = query.data.split("-")

    try:
        active_proposals = get_active_proposals()
    except Exception as e:
        logger.error(e, exc_info=True)
        try_message(context=context, chat_id=query['message']['chat']['id'], text=NETWORK_ERROR_MSG)
        return

    title = '🗳 ✅ **Active proposals**🗳 ✅ \n' \
            'Click on any of the proposals to see details and vote options.\n\n'

    def button_builder(proposal_title: str, proposal_id: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(proposal_title,
                                    callback_data=f'proposal-{proposal_id}-1')  # 1 - open read and vote view

    _display_proposals(proposals=active_proposals, query=query, title=title,
                       button_builder=button_builder)


def _display_proposals(proposals: [], query, title: str,
                       button_builder: Callable[[str, str], InlineKeyboardButton]):
    keyboard = [[]]
    text = title

    if not proposals:
        text += NO_PROPOSALS_MSG
    else:
        for proposal in proposals:
            button = button_builder(proposal['content']['value']['title'], proposal["id"])
            keyboard.append([button])

    keyboard.append([InlineKeyboardButton(BACK_BUTTON_MSG, callback_data='show_governance_menu')])
    query.edit_message_text(text=text,
                            reply_markup=InlineKeyboardMarkup(keyboard))


def on_proposal_clicked(update, context):
    query = update.callback_query
    _, proposal_id, votable = query.data.split("-")
    votable = int(votable)
    previous_view = 'proposals_show_active' if votable else 'proposals_show_all'

    try:
        proposal = get_proposal(int(proposal_id))
        context.user_data.setdefault('proposals_cache', {})[proposal_id] = {
            'title': proposal['content']['value']['title']}
    except Exception as e:
        logger.error(e)
        query.edit_message_text(NETWORK_ERROR_MSG)
        return

    keyboard = [[InlineKeyboardButton(BACK_BUTTON_MSG, callback_data=previous_view)]]
    my_wallet = context.user_data['proposals_cache'].get('wallet', None)
    my_vote = None

    if my_wallet:
        my_vote = get_vote(wallet_addr=my_wallet, proposal_id=proposal_id)

    message = ''
    if my_wallet and my_vote:
        message += f'🎉 You voted *{my_vote}* 🎉'
    else:
        if votable:
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
                [InlineKeyboardButton(BACK_BUTTON_MSG, callback_data='proposals_show_active')]
            ]

    message += f"\n\n\n{proposal_to_text(proposal)}"

    query.edit_message_text(message, parse_mode='markdown', reply_markup=InlineKeyboardMarkup(keyboard))


def on_vote_option_clicked(update, context):
    query = update.callback_query
    _, proposal_id, vote = query.data.split("-")
    proposal_title = context.user_data['proposals_cache'][proposal_id]['title']
    wallet = context.user_data['proposals_cache']['wallet']
    text = f'⚠️ Do you really want to vote *{vote}* on proposal *{proposal_title}*? ⚠️\n'

    if wallet:
        text += f'Your voting address is *{wallet}*'
        yes_button = InlineKeyboardButton('YES ✅', callback_data=f'votesend-{proposal_id}-{vote}')
    else:
        text += YOU_WILL_BE_REDIRECTED_MSG
        yes_button = InlineKeyboardButton('YES ✅ (open website)', url=f'{WEBSITE_URL}vote?id={proposal_id}&vote={vote}')

    keyboard = [
        [yes_button,
         InlineKeyboardButton(BACK_BUTTON_MSG, callback_data=f'proposal-{proposal_id}-1')]]
    query.edit_message_text(text, parse_mode='markdown', reply_markup=InlineKeyboardMarkup(keyboard))


def on_authorize_voting_clicked(update, _):
    text = "You are going to grant me the authorization for voting.\n" \
           "I will *never* vote on your behalf except when you order me to do. 👮\n" \
           "If you confirm the authorization, you will be able to vote directly from any Telegram client" \
           " without accessing your wallet at all.\n\n"
    text += YOU_WILL_BE_REDIRECTED_MSG

    url = LoginUrl(url=f'{WEBSITE_URL}delegate?network={NETWORK}', bot_username=BLOCK42_TERRA_BOT_USERNAME)
    keyboard = [[
        InlineKeyboardButton('Go to website ✅', login_url=url),
        InlineKeyboardButton(BACK_BUTTON_MSG, callback_data='show_governance_menu')
    ]]

    update.callback_query.edit_message_text(text, parse_mode='markdown', reply_markup=InlineKeyboardMarkup(keyboard))


def on_vote_send_clicked(update, context):
    query = update.callback_query
    _, proposal_id, vote = query.data.split("-")
    proposal_title = context.user_data['proposals_cache'][proposal_id]['title']
    keyboard = [[InlineKeyboardButton(BACK_BUTTON_MSG, callback_data=f'proposal-{proposal_id}-1')]]

    try:
        vote_result = vote_delegated(proposal_id=proposal_id, vote=vote, telegram_user_id=query.from_user['id'])
        logger.info(f"Voted successfully. Transaction result:\n{vote_result}")
    except Exception as e:
        logger.exception(e)
        query.edit_message_text(NETWORK_ERROR_MSG, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    tx_hash = vote_result['result'].get('txhash', None)

    if tx_hash is None:
        text = f"Error while voting:\n{vote_result.get('result', None)}"
    else:
        text = f"Successfully voted *{vote}* on proposal *{proposal_title}*. 🎉\n" \
               f"See your vote here:\n" \
               f"{TERRA_FINDER_URL}tx/{tx_hash}"

    query.edit_message_text(text,
                            parse_mode='markdown',
                            reply_markup=InlineKeyboardMarkup(keyboard))
