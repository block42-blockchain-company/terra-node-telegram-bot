import os

import re

from helpers import parse_url_from_env


def read_list_from_env(name, required_type):
    return list(
        map(lambda element: required_type(element),
            filter(lambda element: element, re.split("[,;]", os.getenv(name, '')))))


def get_lcd_url(network_mode: str, debug: bool) -> str:
    if os.environ.get('LCD_ENDPOINT', ''):
        return parse_url_from_env(os.environ['LCD_ENDPOINT'])
    else:
        if debug:
            return 'http://0.0.0.0:1317/'  # Localterra
        else:
            if network_mode == 'mainnet':
                return 'https://lcd.terra.dev/'
            else:
                return 'https://tequila-lcd.terra.dev/'


def get_node_ip(debug: bool) -> [str, None]:
    # Set NODE_IP depending on mode (if None, certain node health jobs are not executed)
    if debug:
        return 'localhost'
    else:
        return os.environ.get('NODE_IP') if os.environ.get('NODE_IP') else None


DEBUG = bool(os.environ.get('DEBUG') == "True")
NETWORK = os.environ.get('NETWORK', ('testnet' if DEBUG else 'mainnet'))  # TODO: document me!
TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK')
SENTRY_NODES = read_list_from_env('SENTRY_NODES', str)
LCD_ENDPOINT = get_lcd_url(network_mode=NETWORK, debug=DEBUG)
NODE_IP = get_node_ip(debug=DEBUG)
