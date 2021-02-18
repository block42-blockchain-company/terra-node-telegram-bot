from datetime import datetime
from typing import List

import dateutil.parser
import requests
from jigu import Terra
from jigu.core import Proposal, AccAddress, StdFee
from jigu.core.msg import MsgVote
from jigu.key.mnemonic import MnemonicKey
from telegram.utils.helpers import escape_markdown

from constants.constants import DEBUG, MNEMONIC
from constants.messages import NETWORK_ERROR_MSG
from constants.logger import logger

# TODO: migrate to new Terra python SDK
if DEBUG:
    lcd_url = 'http://0.0.0.0:1317/'

else:
    lcd_url = 'https://lcd.terra.dev/'

try:
    terra = Terra(None, lcd_url)
    if not terra.is_connected():
        raise Exception()
except Exception as e:
    raise Exception(f"I can't connect to the local Terra API! Is LocalTerra running?")

wallet = terra.wallet(MnemonicKey(MNEMONIC)) if MNEMONIC else None


def get_governance_proposals():
    """
    Return all governance proposals
    """
    try:
        proposals = terra.gov.proposals()
    except Exception as e:
        logger.error(e, exc_info=True)
        raise ConnectionError

    return proposals


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

    # TODO remove this when bug in jigu Terra.estimate_fee() function is fixed
    fee = estimate_vote_fee(proposal_id, wallet.address, vote_option)
    gas = fee['result']['gas']
    uluna_fee = int(next(filter(lambda d: d['denom'] == 'uluna', fee['result']['fees']))['amount']) * 10

    tx = wallet.create_and_sign_tx(
        vote_message,
        fee=StdFee.make(gas=gas, uluna=uluna_fee),
    )

    # TODO change mode to 'block' when jigu bug fixed (throws error "SUCCESS" even when broadcasted successfully)
    return terra.broadcast(tx, mode="sync")


def proposal_to_text(proposal: Proposal) -> str:
    status = proposal.proposal_status

    text = f"*Title:*\n{escape_markdown(proposal.content.title)}\n" + \
           f"*Type:*\n{escape_markdown(proposal.content.type)}\n" + \
           f"*Description:*\n{escape_markdown(proposal.content.description)}\n\n" + \
           f"*Voting Start Time:* {proposal.voting_start_time.strftime('%A %B %d, %H:%M')} UTC\n" + \
           f"*Voting End Time:* {proposal.voting_end_time.strftime('%A %B %d, %H:%M')} UTC\n\n"
    if status == "Rejected" or status == "Passed":
        text += f"Result: *{status}*\n\n"
    else:
        text += f"Make sure to vote on this governance proposal until" \
                f" *{proposal.voting_end_time.strftime('%A %B %d, %H:%M')} UTC*!"

    return text


def terra_timestamp_to_datetime(timestamp: str) -> datetime:
    return dateutil.parser.parse(timestamp)


# TODO remove this when bug in jigu Terra.estimate_fee() function is fixed
def estimate_vote_fee(proposal_id, voter_address, option):
    json = {
        "tx": {
            "type":
                "core/StdTx",
            "fee": {
                "gas": "0"
            },
            "msg": [{
                "type": "gov/MsgVote",
                "value": {
                    "proposal_id": proposal_id,
                    "voter": voter_address,
                    "option": option
                }
            }]
        },
        "gas_adjustment": terra.gas_adjustment,
        "gas_prices": [{
            "denom": "uluna",
            "amount": "0.015000000000000000"
        }]
    }

    repsonse = requests.post(f"{lcd_url}txs/estimate_fee", json=json)

    if not repsonse.ok:
        error = repsonse.json()['error']
        if 'unknown address' in error:
            raise BadMnemonicException()
        else:
            raise Exception(error)

    return repsonse.json()


class BadMnemonicException(Exception):
    pass
