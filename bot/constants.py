import os
import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

DEBUG = bool(os.environ.get('DEBUG') == "True")
TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK')
adjustLCD_ENDPOINT = f"{os.environ['LCD_ENDPOINT']}:1317" if os.environ.get('LCD_ENDPOINT') else "lcd.terra.dev"

# Set NODE_IP depending on mode (if None, certain node health jobs are not executed)
if DEBUG:
    NODE_IP = 'localhost'
else:
    NODE_IP = os.environ.get('NODE_IP') if os.environ.get('NODE_IP') else None

MNEMONIC = os.environ.get('MNEMONIC', '')

if MNEMONIC:
    ALLOWED_USER_IDS = list(
        map(lambda uid: int(uid), filter(lambda uid: uid,
                                         os.getenv('ALLOWED_USER_IDS', '').split(","))))
    if not ALLOWED_USER_IDS:
        logger.warning("You set your mnemonic key but didn't set whitelisted telegram users!"
                       " No one will be able to invoke protected operations!")
    else:
        logger.warning(f"Users allowed to invoke protected operations: {str(ALLOWED_USER_IDS)}")

NODE_STATUSES = ["Unbonded", "Unbonding", "Bonded"]

# Endpoints
VALIDATORS_ENDPOINT = 'http://localhost:8000/validators.json' if DEBUG else f'http://{LCD_ENDPOINT}/staking/validators'
NODE_STATUS_ENDPOINT = 'http://localhost:8000/status.json' if DEBUG else 'http://' + str(NODE_IP) + ':26657/status'
NODE_INFO_ENDPOINT = 'http://localhost:8000/node_info.json' if DEBUG else f'http://{LCD_ENDPOINT}/node_info'

# Paths
storage_path = os.sep.join([os.path.dirname(os.path.realpath(__file__)), os.path.pardir, 'storage'])
session_data_path = os.sep.join([storage_path, 'session.data'])

JOB_INTERVAL_IN_SECONDS = 15
