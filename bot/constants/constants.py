import os

from constants.env_variables import DEBUG, LCD_ENDPOINT, NETWORK, NODE_IP

VALIDATORS_ENDPOINT = 'http://localhost:8000/validators.json' if DEBUG else f'{LCD_ENDPOINT}staking/validators'
NODE_STATUS_ENDPOINT = 'http://localhost:8000/status.json' if DEBUG else 'http://' + str(NODE_IP) + ':26657/status'
NODE_INFO_ENDPOINT = 'http://localhost:8000/node_info.json' if DEBUG else f'{LCD_ENDPOINT}node_info'
BLOCK42_TERRA_BOT_USERNAME = '@terranode_bot'
WEBSITE_URL = 'https://terra-bot.b42.tech/'
BACKEND_URL = f'{WEBSITE_URL}api/{NETWORK}/'
TERRA_FINDER_URL = f'https://finder.terra.money/{"tequila-0004" if NETWORK == "testnet" else "columbus-4"}/'
TERRA_STATION_URL = 'https://station.terra.money/'

storage_path = os.sep.join([os.path.dirname(os.path.realpath(__file__)), os.path.pardir, os.path.pardir, 'storage'])
session_data_path = os.sep.join([storage_path, 'session.data'])

NODE_STATUSES = ["Unbonded", "Unbonding", "Bonded"]

JOB_INTERVAL_IN_SECONDS = 15
SENTRY_JOB_INTERVAL_IN_SECONDS = 30
