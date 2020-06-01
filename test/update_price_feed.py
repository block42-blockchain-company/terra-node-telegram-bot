import json
import time


def update_price_feed():
    """
    Only executed in Debug mode
    To artificially update the price feed we modify prevotes.json
    """

    print("Update local Price Feed ...")

    i = 0
    while True:
        with open('prevotes.json') as json_read_file:
            prevotes = json.load(json_read_file)

        block_height = prevotes['height']
        new_block_height = int(block_height) + 1
        prevotes['height'] = str(new_block_height)

        if i == 0:
            for prevote in prevotes['result']:
                prevote['submit_block'] = prevotes['height']

        with open('prevotes.json', 'w') as json_write_file:
            json.dump(prevotes, json_write_file)

        i += 1
        if i == 5:
            i = 0
        time.sleep(7)


if __name__ == '__main__':
    update_price_feed()
