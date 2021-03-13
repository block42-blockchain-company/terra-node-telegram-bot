from typing import Optional

import requests
from terra_sdk.core.gov import MsgVote

from constants.constants import BACKEND_URL


def get_wallet_addr(telegram_user_id: str) -> Optional[str]:
    response = requests.get(f'{BACKEND_URL}msgauth/user/{telegram_user_id}')

    if not response.ok:
        return None

    result = response.json()['result']

    if result is None:
        return None
    else:
        return result.get('walletAddress', None)


def vote_delegated(proposal_id, vote, telegram_user_id):
    msg_vote = MsgVote(
        proposal_id, "FILL_ME", vote
    )

    response = requests.post(f'{BACKEND_URL}msgauth/vote/{telegram_user_id}', json=msg_vote.to_data())

    if not response.ok:
        raise ConnectionError()

    json = response.json()

    return json
