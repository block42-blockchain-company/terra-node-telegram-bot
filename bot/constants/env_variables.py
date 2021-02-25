import os

from constants.logger import logger
import re


def read_list_from_env(name, required_type):
    return list(
        map(lambda element: required_type(element),
            filter(lambda element: element, re.split(",|;", os.getenv(name, '')))))


DEBUG = bool(os.environ.get('DEBUG') == "True")
TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK')
LCD_ENDPOINT = f"{os.environ['LCD_ENDPOINT']}:1317" if os.environ.get('LCD_ENDPOINT') else "lcd.terra.dev"
SENTRY_NODES = read_list_from_env('SENTRY_NODES', str)

# Set NODE_IP depending on mode (if None, certain node health jobs are not executed)
if DEBUG:
    NODE_IP = 'localhost'
else:
    NODE_IP = os.environ.get('NODE_IP') if os.environ.get('NODE_IP') else None

ALLOWED_USER_IDS = read_list_from_env('ALLOWED_USER_IDS', int)
if not ALLOWED_USER_IDS:
    logger.warning("You didn't set whitelisted telegram users!"
                   " No one will be able to invoke protected operations!")
