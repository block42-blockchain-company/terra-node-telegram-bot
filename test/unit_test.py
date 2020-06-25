import copy
import itertools
import json
import os
import random
import unittest
import time
from subprocess import Popen

from pyrogram import Client as TelegramClient

NODE_STATUSES = ["Unbonded", "Unbonding", "Bonded"]

"""
######################################################################################################################################################
Test Cases
######################################################################################################################################################
"""


class TerraNodeBot(unittest.TestCase):
    terra_node_bot_process = {}
    telegram = {}
    BOT_ID = os.environ['TELEGRAM_BOT_ID']

    @classmethod
    def setUpClass(cls):
        # Delete previous sessions for clean testing
        if os.path.exists("../storage/session.data"):
            os.remove("../storage/session.data")

        # Authenticate Telegram Client of this testing suite
        cls.telegram = TelegramClient(
            open('telegram_session.string').read(),
            api_id=os.environ['TELEGRAM_API_ID'],
            api_hash=os.environ['TELEGRAM_API_HASH']
        )

        # Start the Telegram Terra Node Bot
        cls.terra_node_bot_process = Popen(['python3', 'terra_node_bot.py'], cwd="../")
        time.sleep(5)

        with cls.telegram:
            cls.telegram.send_message(cls.BOT_ID, "/start")
            time.sleep(3)


    @classmethod
    def tearDownClass(cls):
        cls.terra_node_bot_process.terminate()

    def test_start(self):
        with self.telegram:
            self.telegram.send_message(self.BOT_ID, "/start")
            time.sleep(3)

            response = next(self.telegram.iter_history(self.BOT_ID))
            len_buttons = len(response.reply_markup.inline_keyboard)
            self.assertEqual(response.reply_markup.inline_keyboard[len_buttons - 1][0].text,
                             "Add Node", "Add Node not visible after /start")

    def test_assert_add_node_cancel(self):
        self.assert_add_node(address="/cancel",
                      expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                      expected_response2="I am your Terra Node Bot. 🤖\nChoose an address from the list below or add one:")

    def test_assert_add_node_invalid_address(self):
        self.assert_add_node(address="terravaloper_invalid_address",
                      expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                      expected_response2="⛔️ I have not found a Node with this address! ⛔\nPlease try another one. "
                                         "(enter /cancel to return to the menu)")

    def test_assert_add_node_valid_address(self):
        self.add_valid_address()

    def test_node_detail_menu(self):
        valid_address = self.add_valid_address()

        with self.telegram:
            self.click_button(valid_address)

            response = next(self.telegram.iter_history(self.BOT_ID))
            self.assertNotEqual(response.text.find("Node: " + valid_address), -1, "Click on Address does not show Node detail menu")

    def test_back_button_node_detail_menu(self):
        valid_address = self.add_valid_address()

        with self.telegram:
            response = next(self.telegram.iter_history(self.BOT_ID))
            self.click_button(valid_address)
            self.assert_back_button(response.text)

    def test_delete_node_confirm_true(self):
        self.assert_delete_address(confirm=True)

    def test_delete_node_confirm_false(self):
        self.assert_delete_address(confirm=False)

    def test_node_change_notification_address(self):
        self.assert_node_change_notification("address")

    def test_node_change_notification_status(self):
        self.assert_node_change_notification("status")

    def test_node_change_notification_jailed(self):
        self.assert_node_change_notification("jailed")

    def test_node_change_notification_delegator_shares(self):
        self.assert_node_change_notification("delegator_shares")

    def test_price_feed_notification(self):
        self.add_valid_address()
        self.assert_height_related_notification(monitoring_type="price_feed")

    def test_block_height_notification(self):
        self.assert_height_related_notification(monitoring_type="block_height")

    def test_catch_up_notification_is_catching_up(self):
        self.assert_catch_up_notification(catching_up=True)

    def test_catch_up_notification_is_not_catching_up(self):
        self.assert_catch_up_notification(catching_up=False)


    """
    --------------------------------------------------------------------------------------------------------
    GENERIC METHODS
    --------------------------------------------------------------------------------------------------------
    """

    def assert_add_node(self, address, expected_response1, expected_response2):
        with self.telegram:
            self.telegram.send_message(self.BOT_ID, "/start")
            time.sleep(3)

            self.click_button("Add Node")

            first_response = next(self.telegram.iter_history(self.BOT_ID))
            self.telegram.send_message(self.BOT_ID, address)
            time.sleep(3)
            second_response_1 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
            second_response_2 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

            self.assertEqual(first_response.text, expected_response1, "Expected '" + expected_response1 + "' but got '" + first_response.text + "'")
            self.assertTrue(second_response_1.text == expected_response2 or second_response_2.text == expected_response2, \
                "Expected '" + expected_response2 + "' but got '" + second_response_1.text + "' and '" + second_response_2.text + "'")

    def assert_back_button(self, text):
        """
        Click back button and assert TG shows what was shown before
        """

        self.click_button("<< Back")

        response = next(self.telegram.iter_history(self.BOT_ID))

        self.assertEqual(response.text, text, "Back button not working.")

    def assert_delete_address(self, confirm):
        valid_address = json.load(open('validators.json'))['result'][0]['operator_address']
        self.assert_add_node(address=valid_address,
                      expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                      expected_response2="Got it! 👌")

        with self.telegram:
            self. telegram.send_message(self.BOT_ID, "/start")
            time.sleep(3)

            self.click_button(valid_address)

            self.click_button("Delete Node")

            first_response = next(self.telegram.iter_history(self.BOT_ID))

            self.assertEqual(first_response.text, '⚠️ Do you really want to remove the address from your monitoring '
                                                  'list? ⚠️\n' + valid_address, "Delete Node button doesn't work!")

            if confirm:
                self.click_button("YES ✅")
                time.sleep(3)
                second_response_1 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
                second_response_2 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))
                self.assertEqual(second_response_1.text, "❌ Node address got deleted! ❌\n" + valid_address, \
                    "YES button on deletion confirmation does not yield deletion statement")
                self.assertEqual(second_response_2.text, "I am your Terra Node Bot. 🤖\nChoose an address from the list "
                            "below or add one:", "YES button on deletion confirmation does not go back to nodes menu")
            else:
                self.click_button("NO ❌")
                time.sleep(3)
                second_response = next(self.telegram.iter_history(self.BOT_ID))
                self.assertNotEqual(second_response.text.find("Node: " + valid_address), -1, \
                    "NO button on single address deletion confirmation does not go back to Node details")

    def assert_node_change_notification(self, field):
        valid_address = json.load(open('validators.json'))['result'][0]['operator_address']
        self.assert_add_node(address=valid_address,
                             expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                             expected_response2="Got it! 👌")

        with open('validators.json') as json_read_file:
            node_data_original = json.load(json_read_file)
            node_data_new = copy.deepcopy(node_data_original)

        if field == "address":
            node_data_new['result'][0]['operator_address'] = "terravaloper" + str(random.randrange(0, 100000))
            expected_response = 'Node is not active anymore! 💀' + '\n' + \
                                'Address: ' + node_data_original['result'][0]['operator_address'] + '\n\n' + \
                                'Please enter another Node address.'
        elif field == "jailed":
            node_data_new['result'][0]['jailed'] = not node_data_new['result'][0]['jailed']
            expected_response = 'Node: ' + node_data_original['result'][0]['operator_address'] + '\n' + \
                                'Status: ' + NODE_STATUSES[node_data_original['result'][0]['status']] + \
                                '\nJailed: ' + str(node_data_original['result'][0]['jailed']) + \
                                ' ➡️ ' + str(node_data_new['result'][0]['jailed'])
        elif field == "status":
            current_status = node_data_original['result'][0]['status']
            while True:
                new_status = random.randrange(0, 3)
                if new_status != current_status:
                    break
            node_data_new['result'][0]['status'] = new_status
            expected_response = 'Node: ' + node_data_original['result'][0]['operator_address'] + '\n' + \
                                'Status: ' + NODE_STATUSES[node_data_original['result'][0]['status']] + \
                                ' ➡️ ' + NODE_STATUSES[node_data_new['result'][0]['status']] + \
                                '\nJailed: ' + str(node_data_original['result'][0]['jailed'])
        elif field == "delegator_shares":
            node_data_new['result'][0]['delegator_shares'] = float(node_data_original['result'][0]['delegator_shares']) + 1
            expected_response = 'Node: ' + node_data_original['result'][0]['operator_address'] + '\n' + \
                                'Status: ' + NODE_STATUSES[node_data_original['result'][0]['status']] + \
                                '\nJailed: ' + str(node_data_original['result'][0]['jailed']) + \
                                '\nDelegator Shares: ' + str(int(float(node_data_original['result'][0]['delegator_shares']))) + \
                                ' ➡️ ' + str(int(float(node_data_new['result'][0]['delegator_shares'])))
        else:
            self.assertTrue(False, "The argument" + field + "that you passed as 'field' to assert_node_change_notification is not defined")

        with open('validators.json', 'w') as json_write_file:
            json.dump(node_data_new, json_write_file)

        time.sleep(20)
        with self.telegram:
            first_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
            second_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

        self.assertNotEqual(first_response.text.find(expected_response), -1, \
                            "Expected '" + expected_response + "' but got '" + first_response.text + "'")
        self.assertEqual(second_response.text,
                         "I am your Terra Node Bot. 🤖\nChoose an address from the list below or add one:", \
                         "I am your Terra Node Bot. 🤖\nChoose an address from the list below or add one: - not visible after node address change notification.")

    def assert_height_related_notification(self, monitoring_type):
        file_name = ""
        expected_response1 = ""
        expected_response2 = ""
        if monitoring_type == "block_height":
            file_name = "status.json"
            expected_response1 = 'Block height is not increasing anymore!'
            expected_response2 = 'Block height is increasing again!'
        elif monitoring_type == "price_feed":
            file_name = "prevotes.json"
            expected_response1 = 'Price feed is not healthy anymore!'
            expected_response2 = 'Price feed is healthy again!'
        else:
            self.assertTrue(False, "Monitoring monitoring_type does not exist.")

        with open(file_name) as json_read_file:
            data = json.load(json_read_file)

        if monitoring_type == "block_height":
            block_height = data['result']['sync_info']['latest_block_height']
            new_block_height = int(block_height) - 200
            data['result']['sync_info']['latest_block_height'] = str(new_block_height)
            with open(file_name, 'w') as json_write_file:
                json.dump(data, json_write_file)
            time.sleep(15)
        elif monitoring_type == "price_feed":
            for x in range(20):
                block_height = data['height']
                new_block_height = int(block_height) + 20
                data['height'] = str(new_block_height)
                with open(file_name, 'w') as json_write_file:
                    json.dump(data, json_write_file)
                time.sleep(3)

        with self.telegram:
            first_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
            second_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

        self.assertNotEqual(first_response.text.find(expected_response1), -1, "Expected '" + expected_response1 + \
                                                                  "'\nbut got\n'" + first_response.text + "'")
        self.assertEqual(second_response.text, "I am your Terra Node Bot. 🤖\nChoose an address from the list "
                                 "below or add one:", "I am your Terra Node Bot. 🤖\nChoose an address from the "
                                 "list below or add one: - not visible after block height notification")

        time.sleep(35)
        with self.telegram:
            first_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
            second_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

        self.assertNotEqual(first_response.text.find(expected_response2), -1, "Expected '" + expected_response2 + \
                                                                  "'\nbut got\n'" + first_response.text + "'")
        self.assertEqual(second_response.text, "I am your Terra Node Bot. 🤖\nChoose an address from the list below or add one:", \
            "I am your Terra Node Bot. 🤖\nChoose an address from the list below or add one: - not visible after block height notification")

    def assert_catch_up_notification(self, catching_up):
        self.set_catch_up_status(catching_up=catching_up)

        with self.telegram:
            first_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
            second_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

        if catching_up:
            expected_response = 'The Node is behind the latest block height and catching up!'
        else:
            expected_response = 'The node caught up to the latest block height again!'

        self.assertNotEqual(first_response.text.find(expected_response), -1, "Expected '" + expected_response + \
                                                                  "'\nbut got\n'" + first_response.text + "'")
        self.assertEqual(second_response.text, "I am your Terra Node Bot. 🤖\nChoose an address from the list below or add one:", \
            "I am your Terra Node Bot. 🤖\nChoose an address from the list below or add one:" \
            " - not visible after catching_up=" + str(catching_up) + " notification")

    """
    --------------------------------------------------------------------------------------------------------
    UTILS
    --------------------------------------------------------------------------------------------------------
    """

    def set_catch_up_status(self, catching_up):
        with open('status.json') as json_read_file:
            node_data = json.load(json_read_file)

        node_data['result']['sync_info']['catching_up'] = not catching_up

        with open('status.json', 'w') as json_write_file:
            json.dump(node_data, json_write_file)
        time.sleep(20)

        with open('status.json') as json_read_file:
            node_data = json.load(json_read_file)

        node_data['result']['sync_info']['catching_up'] = catching_up

        with open('status.json', 'w') as json_write_file:
            json.dump(node_data, json_write_file)
        time.sleep(20)

    def click_button(self, button):
        response = next(self.telegram.iter_history(self.BOT_ID))
        response.click(button)
        time.sleep(3)

    def add_valid_address(self):
        valid_address = json.load(open('validators.json'))['result'][0]['operator_address']
        self.assert_add_node(address=valid_address,
                             expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                             expected_response2="Got it! 👌")
        return valid_address


if __name__ == '__main__':
    unittest.main()

