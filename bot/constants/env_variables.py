import os

from constants.logger import logger

DEBUG = bool(os.environ.get('DEBUG') == "True")
TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK')
LCD_ENDPOINT = f"{os.environ['LCD_ENDPOINT']}:1317" if os.environ.get('LCD_ENDPOINT') else "lcd.terra.dev"

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
