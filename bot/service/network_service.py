import requests


def is_syncing(node_ip):
    response = requests.get(f'{node_ip}/syncing')

    if not response.ok:
        raise ConnectionError

    syncing = response.json().get('syncing', False)

    if syncing is bool and syncing:
        return True
    else:
        return False
