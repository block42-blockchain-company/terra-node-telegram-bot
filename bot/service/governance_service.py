from datetime import datetime
from typing import List

import requests
from jigu import Terra
from jigu.core import Proposal, AccAddress, StdFee
from jigu.core.msg import MsgVote
from jigu.key.mnemonic import MnemonicKey

from constants import GOVERNANCE_PROPOSAL_ENDPOINT, logger, MNEMONIC, NODE_IP, DEBUG
from messages import NETWORK_ERROR_MSG

if DEBUG and MNEMONIC:
    terra = Terra(None, 'http://0.0.0.0:1317/')

    if not terra.is_connected():
        raise Exception(f"I can't connect to the local Terra API! Is LocalTerra running?")
else:
    terra = Terra(None, 'https://lcd.terra.dev/')

    if not terra.is_connected():
        raise Exception(f"I can't connect to the Terra LCD API!")

wallet = terra.wallet(MnemonicKey(MNEMONIC)) if MNEMONIC else None


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


def get_all_proposals_as_messages() -> List[str]:
    try:
        proposals = get_governance_proposals()
    except ConnectionError:
        return [NETWORK_ERROR_MSG]

    message = []

    for proposal in proposals:
        message.append(proposal_to_text(proposal))

    return message


def get_active_proposals() -> List[Proposal]:
    proposals = terra.gov.proposals()

    return list(filter(lambda p: p.proposal_status == 'VotingPeriod', proposals))


def get_proposal_by_id(proposal_id) -> Proposal:
    return terra.gov.proposal(proposal_id)


def is_wallet_provided():
    if wallet:
        return True
    else:
        return False


def get_my_vote(proposal_id: str) -> (bool, None):
    if not wallet:
        raise Exception("No MNEMONIC provided.")

    votes = terra.gov.votes_for(proposal_id)

    return votes.get(wallet.address, None)


def vote_on_proposal(proposal_id: int, vote_option: str) -> (bool, None):
    if not wallet:
        raise Exception("No MNEMONIC provided.")

    vote_message = MsgVote(
        proposal_id=proposal_id,
        voter=AccAddress(wallet.address),
        option=vote_option,
    )

    tx = wallet.create_and_sign_tx(
        vote_message,
        fee=StdFee.make(gas=200_000, uluna=1_000_000)  # Fixme - why auto fee doesn't work?
    )

    return terra.broadcast(tx, mode="sync")


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


def jigu_proposal_to_text(proposal: Proposal) -> str:
    status = proposal.proposal_status

    text = f"*Title:*\n{proposal.content.title}\n" + \
           f"*Type:*\n{proposal.content.type}\n" + \
           f"*Description:*\n{proposal.content.description}\n\n" + \
           f"*Voting Start Time:* {proposal.voting_start_time.strftime('%A %B %d, %H:%M')} UTC\n" + \
           f"*Voting End Time:* {proposal.voting_end_time.strftime('%A %B %d, %H:%M')} UTC\n\n"
    if status == "Rejected" or status == "Passed":
        text += f"Result: *{status}*\n\n"
    else:
        text += f"Make sure to vote on this governance proposal until" \
                f" *{proposal.voting_end_time.strftime('%A %B %d, %H:%M')} UTC*!"

    return text
