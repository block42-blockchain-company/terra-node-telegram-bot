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
                      expected_response2="Choose an address from the list below or add one:")

    def test_assert_add_node_invalid_address(self):
        self.assert_add_node(address="terravaloper_invalid_address",
                      expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                      expected_response2="⛔️ I have not found a Node with this address! ⛔\nPlease try another one. "
                                         "(enter /cancel to return to the menu)")

    def test_assert_add_node_valid_address(self):
        valid_address = json.load(open('validators.json'))['result'][0]['operator_address']
        self.assert_add_node(address=valid_address,
                      expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                      expected_response2="Got it! 👌")

    def test_node_detail_menu(self):
        valid_address = json.load(open('validators.json'))['result'][0]['operator_address']
        self.assert_add_node(address=valid_address,
                      expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                      expected_response2="Got it! 👌")

        with self.telegram:
            self.click_button(valid_address)

            response = next(self.telegram.iter_history(self.BOT_ID))
            self.assertNotEqual(response.text.find("Node: " + valid_address), -1, "Click on Address does not show Node detail menu")

    def test_back_button_node_detail_menu(self):
        valid_address = json.load(open('validators.json'))['result'][0]['operator_address']
        self.assert_add_node(address=valid_address,
                             expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                             expected_response2="Got it! 👌")

        with self.telegram:
            response = next(self.telegram.iter_history(self.BOT_ID))
            self.click_button(valid_address)
            self.assert_back_button(response.text)

    def test_delete_node_confirm_true(self):
        self.assert_delete_address(confirm=True)

    def test_delete_node_confirm_false(self):
        self.assert_delete_address(confirm=False)

    def test_node_change_notification_address(self):
        with open('validators.json') as json_read_file:
            node_data_original = json.load(json_read_file)
            node_data_new = copy.deepcopy(node_data_original)

        node_data_new['result'][0]['operator_address'] = "terravaloper" + str(random.randrange(0, 100000))

        with open('validators.json', 'w') as json_write_file:
            json.dump(node_data_new, json_write_file)

        time.sleep(20)
        first_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
        second_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

        expected_response = 'Node is not active anymore! 💀' + '\n' + \
                            'Address: ' + node_data_original[0]['node_address'] + '\n\n' + \
                            'Please enter another Node address.'

        assert first_response.text.find(expected_response) != -1, \
            "Expected '" + expected_response + "' but got '" + first_response.text + "'"
        assert second_response.text == "Choose an address from the list below or add one:", \
            "Choose an address from the list below or add one: - not visible after node address change notification."

    def test_node_change_notification_status(self):
        with open('validators.json') as json_read_file:
            node_data_original = json.load(json_read_file)
            node_data_new = copy.deepcopy(node_data_original)

        node_data_new['result'][0]['status'] = random.randrange(0, 3)

        with open('validators.json', 'w') as json_write_file:
            json.dump(node_data_new, json_write_file)

        time.sleep(20)
        first_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
        second_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

        expected_response = 'Node: ' + node_data_original[0]['node_address'] + '\n' + \
                            'Status: ' + NODE_STATUSES[node_data_original['result'][0]['status']] + \
                            ' ➡️ ' + NODE_STATUSES[node_data_new['result'][0]['status']] + \
                            '\nJailed: ' + str(node_data_original['result'][0]['jailed'])

        assert first_response.text.find(expected_response) != -1, \
            "Expected '" + expected_response + "' but got '" + first_response.text + "'"
        assert second_response.text == "Choose an address from the list below or add one:", \
            "Choose an address from the list below or add one: - not visible after node address change notification."

    def test_node_change_notification_jailed(self):
        with open('validators.json') as json_read_file:
            node_data_original = json.load(json_read_file)
            node_data_new = copy.deepcopy(node_data_original)

        node_data_new['result'][0]['jailed'] = not node_data_new['result'][0]['jailed']

        with open('validators.json', 'w') as json_write_file:
            json.dump(node_data_new, json_write_file)

        time.sleep(20)
        first_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
        second_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

        expected_response = 'Node: ' + node_data_original[0]['node_address'] + '\n' + \
                            'Status: ' + NODE_STATUSES[node_data_original['result'][0]['status']] + \
                            '\nJailed: ' + str(node_data_original['result'][0]['jailed']) + \
                            ' ➡️ ' + str(node_data_new['result'][0]['status']['jailed'])

        assert first_response.text.find(expected_response) != -1, \
            "Expected '" + expected_response + "' but got '" + first_response.text + "'"
        assert second_response.text == "Choose an address from the list below or add one:", \
            "Choose an address from the list below or add one: - not visible after node address change notification."

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

            self.assertEqual(first_response.text, '⚠️ Do you really want to remove the address from your monitoring list? ⚠️\n' + valid_address, \
                "Delete Node button doesn't work!")

            if confirm:
                self.click_button("YES ✅")
                time.sleep(3)
                second_response_1 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
                second_response_2 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))
                self.assertEqual(second_response_1.text, "❌ Node address got deleted! ❌\n" + valid_address, \
                    "YES button on deletion confirmation does not yield deletion statement")
                self.assertEqual(second_response_2.text, "Choose an address from the list below or add one:", \
                    "YES button on deletion confirmation does not go back to nodes menu")
            else:
                self.click_button("NO ❌")
                time.sleep(3)
                second_response = next(self.telegram.iter_history(self.BOT_ID))
                self.assertNotEqual(second_response.text.find("Node: " + valid_address), -1, \
                    "NO button on single address deletion confirmation does not go back to Node details")

    """
    --------------------------------------------------------------------------------------------------------
    UTILS
    --------------------------------------------------------------------------------------------------------
    """

    def click_button(self, button):
        """
        Click a button and wait
        """

        response = next(self.telegram.iter_history(self.BOT_ID))
        response.click(button)
        time.sleep(3)


if __name__ == '__main__':
    unittest.main()

