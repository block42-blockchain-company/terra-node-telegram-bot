import os
import logging

"""
######################################################################################################################################################
Static & environment variables
######################################################################################################################################################
"""

DEBUG = bool(os.environ.get('DEBUG') == "True")
TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK')


# Set NODE_IP depending on mode (if None, certain node health jobs are not executed)
if DEBUG:
    NODE_IP = 'localhost'
else:
    NODE_IP = os.environ.get('NODE_IP') if os.environ.get('NODE_IP') else None


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

NODE_STATUSES = ["Unbonded", "Unbonding", "Bonded"]

# Endpoints
VALIDATORS_ENDPOINT = 'http://localhost:8000/validators.json' if DEBUG else 'https://lcd.terra.dev/staking/validators'
NODE_STATUS_ENDPOINT = 'http://localhost:8000/status.json' if DEBUG else 'http://' + str(NODE_IP) + ':26657/status'
GOVERNANCE_PROPOSAL_ENDPOINT = 'http://localhost:8000/governance_proposals.json' if DEBUG else 'https://lcd.terra.dev/gov/proposals'
NODE_INFO_ENDPOINT = 'http://localhost:8000/node_info.json' if DEBUG else 'https://lcd.terra.dev/node_info'

# Paths
storage_path = os.sep.join([os.path.dirname(os.path.realpath(__file__)), os.path.pardir, 'storage'])
session_data_path = os.sep.join([storage_path, 'session.data'])

JOB_INTERVAL_IN_SECONDS = 30
