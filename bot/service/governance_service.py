from datetime import datetime
from typing import List

import dateutil.parser
import requests
from telegram.utils.helpers import escape_markdown

from constants.constants import LCD_ENDPOINT
from constants.messages import NETWORK_ERROR_MSG


def get_governance_proposals(params=None) -> List:
    response = requests.get(f'{LCD_ENDPOINT}gov/proposals', params=params)

    if not response.ok:
        raise ConnectionError

    return response.json()['result']


def get_all_proposals_as_messages() -> List[str]:
    try:
        proposals = get_governance_proposals()
    except ConnectionError:
        return [NETWORK_ERROR_MSG]

    message = []

    for proposal in proposals:
        message.append(proposal_to_text(proposal))

    return message


def get_active_proposals() -> List:
    return get_governance_proposals({"status": 'VotingPeriod'})


def get_proposal(proposal_id: int) -> dict:
    response = requests.get(f'{LCD_ENDPOINT}gov/proposals/{proposal_id}')

    if not response.ok:
        raise ConnectionError

    return response.json()['result']


def proposal_to_text(proposal: dict) -> str:
    status = proposal['proposal_status']

    text = f"*Title:*\n{escape_markdown(proposal['content']['value']['title'])}\n" + \
           f"*Type:*\n{escape_markdown(proposal['content']['type'])}\n" + \
           f"*Description:*\n{escape_markdown(proposal['content']['value']['description'])}\n\n" + \
           f"*Voting Start Time:" \
           f"* {terra_timestamp_to_datetime(proposal['voting_start_time']).strftime('%A %B %d, %H:%M')} UTC\n" + \
           f"*Voting End Time:" \
           f"* {terra_timestamp_to_datetime(proposal['voting_end_time']).strftime('%A %B %d, %H:%M')} UTC\n\n"
    if status == "Rejected" or status == "Passed":
        text += f"Result: *{status}*\n\n"
    else:
        text += f"Make sure to vote on this governance proposal until" \
                f" *{terra_timestamp_to_datetime(proposal['voting_end_time']).strftime('%A %B %d, %H:%M')} UTC*!"

    return text


def terra_timestamp_to_datetime(timestamp: str) -> datetime:
    return dateutil.parser.parse(timestamp)


def get_vote(wallet_addr, proposal_id) -> str:
    response = requests.get(f'{LCD_ENDPOINT}/gov/proposals/{proposal_id}/votes/{wallet_addr}')

    if not response.ok:
        return None

    return response.json()['result'].get('option', None)
