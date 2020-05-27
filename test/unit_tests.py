import itertools
import os
import unittest
import time
from subprocess import Popen

from pyrogram import Client as TelegramClient

VALID_ADDRESS = "terravaloperXYZ"

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

    def test_add_node_cancel(self):
        self.add_node(address="/cancel",
                      expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                      expected_response2="Choose an address from the list below or add one:")

    def test_add_node_valid_address(self):
        self.add_node(address=VALID_ADDRESS,
                      expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                      expected_response2="Got it! 👌")

    def test_node_detail_menu(self):
        self.add_node(address=VALID_ADDRESS,
                      expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                      expected_response2="Got it! 👌")

        with self.telegram:
            self.click_button(VALID_ADDRESS)

            response = next(self.telegram.iter_history(self.BOT_ID))
            self.assertNotEqual(response.text.find("Node: " + VALID_ADDRESS), -1, "Click on Address does not show Node detail menu")

    def test_back_button_node_detail_menu(self):
        self.add_node(address=VALID_ADDRESS,
                      expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                      expected_response2="Got it! 👌")

        with self.telegram:
            response = next(self.telegram.iter_history(self.BOT_ID))
            self.click_button(VALID_ADDRESS)
            self.assert_back_button(response.text)

    def test_delete_node_confirm_true(self):
        self.delete_address(confirm=True)

    def test_delete_node_confirm_false(self):
        self.delete_address(confirm=False)

    """
    --------------------------------------------------------------------------------------------------------
    GENERIC METHODS
    --------------------------------------------------------------------------------------------------------
    """

    def add_node(self, address, expected_response1, expected_response2):
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

    def delete_address(self, confirm):
        self.add_node(address=VALID_ADDRESS,
                      expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                      expected_response2="Got it! 👌")

        with self.telegram:
            self. telegram.send_message(self.BOT_ID, "/start")
            time.sleep(3)

            self.click_button(VALID_ADDRESS)

            self.click_button("Delete Node")

            first_response = next(self.telegram.iter_history(self.BOT_ID))

            self.assertEqual(first_response.text, '⚠️ Do you really want to remove the address from your monitoring list? ⚠️\n' + VALID_ADDRESS, \
                "Delete Node button doesn't work!")

            if confirm:
                self.click_button("YES ✅")
                time.sleep(3)
                second_response_1 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
                second_response_2 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))
                self.assertEqual(second_response_1.text, "❌ Node address got deleted! ❌\n" + VALID_ADDRESS, \
                    "YES button on deletion confirmation does not yield deletion statement")
                self.assertEqual(second_response_2.text, "Choose an address from the list below or add one:", \
                    "YES button on deletion confirmation does not go back to nodes menu")
            else:
                self.click_button("NO ❌")
                time.sleep(3)
                second_response = next(self.telegram.iter_history(self.BOT_ID))
                self.assertNotEqual(second_response.text.find("Node: " + VALID_ADDRESS), -1, \
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

