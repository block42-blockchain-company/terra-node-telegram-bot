import json
import os
import time


def increase_block_height():
    """
    Only executed in Debug mode
    To artificially increase the block height status.json is modified
    """

    print("Increasing local Block Height ...")
    while True:
        # In the test cases we change the filename, but we still need to increase the block height in the renamed file.
        file = 'status.json' if os.path.exists('status.json') else 'status_renamed.json'
        with open(file) as json_read_file:
            node_data = json.load(json_read_file)

        block_height = node_data['result']['sync_info']['latest_block_height']
        new_block_height = int(block_height) + 1
        node_data['result']['sync_info']['latest_block_height'] = str(new_block_height)

        with open(file, 'w') as json_write_file:
            json.dump(node_data, json_write_file)
        time.sleep(7)


if __name__ == '__main__':
    increase_block_height()
