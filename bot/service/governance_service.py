from datetime import datetime
from typing import List

import dateutil.parser
import requests
from telegram.utils.helpers import escape_markdown

from constants.constants import LCD_URL
from constants.messages import NETWORK_ERROR_MSG


def get_governance_proposals(params=None) -> List:
    """
    Return all governance proposals
    """

    response = requests.get(f'{LCD_URL}gov/proposals', params=params)

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


def get_proposal_by_id(proposal_id: int) -> dict:
    response = requests.get(f'{LCD_URL}gov/proposals/{proposal_id}')

    if not response.ok:
        raise ConnectionError

    return response.json()['result']


def get_my_vote(proposal_id: str):
    # TODO: Implement me when backend ready!
    return None


def vote_on_proposal(proposal_id: int, vote_option: str) -> (bool, None):
    # TODO: Implement me when backend ready!
    pass


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
