from datetime import datetime

import requests

from constants import GOVERNANCE_PROPOSAL_ENDPOINT, logger
from messages import NETWORK_ERROR_MSG


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


def get_all_proposals_as_messages() -> [str]:
    try:
        proposals = get_governance_proposals()
    except ConnectionError:
        return [NETWORK_ERROR_MSG]

    message = []

    for proposal in proposals:
        message.append(proposal_to_text(proposal))

    return message


def proposal_to_text(proposal) -> str:
    voting_start_time = datetime.strptime(proposal['voting_start_time'][:-4], "%Y-%m-%dT%H:%M:%S.%f")
    voting_end_time = datetime.strptime(proposal['voting_end_time'][:-4], "%Y-%m-%dT%H:%M:%S.%f")

    text = f"*Title:*\n{proposal['content']['value']['title']}\n" + \
           f"*Type:*\n{proposal['content']['type']}\n" + \
           f"*Description:*\n{proposal['content']['value']['description']}\n\n" + \
           f"*Voting Start Time:* {voting_start_time.strftime('%A %B %d, %H:%M')} UTC\n" + \
           f"*Voting End Time:* {voting_end_time.strftime('%A %B %d, %H:%M')} UTC\n\n"
    if proposal['proposal_status'] == "Rejected" or proposal['proposal_status'] == "Passed":
        text += f"Result: *{proposal['proposal_status']}*\n\n"
    else:
        text += f"Make sure to vote on this governance proposal until *{voting_end_time.strftime('%A %B %d, %H:%M')} UTC*!"

    return text
