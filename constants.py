import os
import logging

"""
######################################################################################################################################################
Static & environment variables
######################################################################################################################################################
"""

DEBUG = bool(os.environ['DEBUG'] == 'True') if 'DEBUG' in os.environ else False
TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
LCD_ENDPOINT = os.environ['LCD_ENDPOINT'] if 'LCD_ENDPOINT' in os.environ and os.environ['LCD_ENDPOINT'] \
    else "lcd.terra.dev"

# Set NODE_IP depending on mode (if None, certain node health jobs are not executed)
if DEBUG:
    NODE_IP = 'localhost'
elif 'NODE_IP' in os.environ and os.environ['NODE_IP']:
    NODE_IP = os.environ['NODE_IP']
else:
    NODE_IP = None

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

NODE_STATUSES = ["Unbonded", "Unbonding", "Bonded"]

# Endpoints
VALIDATORS_ENDPOINT = 'http://localhost:8000/validators.json' if DEBUG else f'https://{LCD_ENDPOINT}/staking/validators'
NODE_STATUS_ENDPOINT = 'http://localhost:8000/status.json' if DEBUG else f'http://{(NODE_IP)}:26657/status'
GOVERNANCE_PROPOSAL_ENDPOINT = 'http://localhost:8000/governance_proposals.json' if DEBUG else f'https://{LCD_ENDPOINT}/gov/proposals'
NODE_INFO_ENDPOINT = 'http://localhost:8000/node_info.json' if DEBUG else f'https://{LCD_ENDPOINT}/node_info'

# Paths
storage_path = os.sep.join([os.path.dirname(os.path.realpath(__file__)), os.path.pardir, 'storage'])
session_data_path = os.sep.join([storage_path, 'session.data'])

JOB_INTERVAL_IN_SECONDS = 15
