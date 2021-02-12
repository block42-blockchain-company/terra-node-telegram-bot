from constants.env_variables import *

VALIDATORS_ENDPOINT = 'http://localhost:8000/validators.json' if DEBUG else f'http://{LCD_ENDPOINT}/staking/validators'
NODE_STATUS_ENDPOINT = 'http://localhost:8000/status.json' if DEBUG else 'http://' + str(NODE_IP) + ':26657/status'
NODE_INFO_ENDPOINT = 'http://localhost:8000/node_info.json' if DEBUG else f'http://{LCD_ENDPOINT}/node_info'

storage_path = os.sep.join([os.path.dirname(os.path.realpath(__file__)), os.path.pardir, os.path.pardir, 'storage'])
session_data_path = os.sep.join([storage_path, 'session.data'])

NODE_STATUSES = ["Unbonded", "Unbonding", "Bonded"]

JOB_INTERVAL_IN_SECONDS = 15
