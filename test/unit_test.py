import copy
import itertools
import json
import os
import random
import re
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
        cls.terra_node_bot_process = Popen(['python3', 'bot/terra_node_bot.py'], cwd="../")
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
                             "📡 MY NODES", "📡 MY NODES not visible after /start")

    def test_my_nodes_menu(self):
        with self.telegram:
            self.telegram.send_message(self.BOT_ID, "/start")
            time.sleep(3)

            self.click_button("📡 MY NODES")

            time.sleep(3)
            response = next(self.telegram.iter_history(self.BOT_ID))
            len_buttons = len(response.reply_markup.inline_keyboard)
            self.assertEqual(response.reply_markup.inline_keyboard[len_buttons - 1][0].text,
                             "➖ REMOVE ALL", "➖ REMOVE ALL not visible after /start")

    def test_back_button_node_my_nodes_menu(self):
        with self.telegram:
            self.telegram.send_message(self.BOT_ID, "/start")
            time.sleep(3)
            response = next(self.telegram.iter_history(self.BOT_ID))

            self.click_button("📡 MY NODES")
            self.assert_back_button(response.text)

    def test_assert_add_node_cancel(self):
        self.assert_add_node(address="/cancel",
                      expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                      expected_response2="add a node")

    def test_assert_add_node_invalid_address(self):
        self.assert_add_node(address="terravaloper_invalid_address",
                      expected_response1="What's the address of your Node? (enter /cancel to return to the menu)",
                      expected_response2="⛔️ I have not found a Node with this address!")

    def test_assert_add_all_nodes_confirm_false(self):
        self.assert_add_all_nodes(confirm=False)

    def test_assert_add_all_nodes_confirm_true(self):
        self.assert_add_all_nodes(confirm=True)
        self.assert_delete_all_nodes(confirm=True)

    def test_assert_delete_all_nodes_confirm_false(self):
        self.assert_delete_all_nodes(confirm=False)

    def test_assert_delete_all_nodes_confirm_true(self):
        self.assert_delete_all_nodes(confirm=True)

    def test_assert_add_node_valid_address(self):
        self.add_valid_address()

    def test_node_detail_menu(self):
        valid_address = self.add_valid_address()

        with self.telegram:
            self.click_button("📡 " + valid_address)

            response = next(self.telegram.iter_history(self.BOT_ID))
            self.assertNotEqual(response.text.find("Node: " + valid_address), -1, "Click on Address does not show Node detail menu")

    def test_back_button_node_detail_menu(self):
        valid_address = self.add_valid_address()

        with self.telegram:
            response = next(self.telegram.iter_history(self.BOT_ID))
            self.click_button("📡 " + valid_address)
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

    def test_new_governance_proposal_notification(self):
        with open('governance_proposals.json') as json_read_file:
            governance_proposals = json.load(json_read_file)
            governance_proposals_new = copy.deepcopy(governance_proposals)

        new_proposal = governance_proposals['result'][random.randrange(0, 8)]
        governance_proposals_new['result'].append(new_proposal)

        time.sleep(20)
        with open('governance_proposals.json', 'w') as json_write_file:
            json.dump(governance_proposals_new, json_write_file)
        time.sleep(20)

        with self.telegram:
            first_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
            second_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

        self.assertNotEqual(first_response.text.find(new_proposal['content']['value']['title']), -1, \
                            "Expected '" + json.dumps(new_proposal) + "' but got '" + first_response.text + "'")
        self.assertTrue(re.search("I am your Terra Node Bot. 🤖", second_response.text, re.IGNORECASE),
                        "'I am your Terra Node Bot. 🤖' - not visible after node address change notification.")

    def test_lcd_unreachable_notification(self):
        self.assert_unreachable_notification(file_name="node_info",
                                             expected1="The public Lite Client Daemon (LCD) cannot be reached!",
                                             expected2="The public Lite Client Daemon (LCD) is reachable again!")

    def test_node_unreachable_notification(self):
        self.assert_unreachable_notification(file_name="status",
                                             expected1="The specified Node cannot be reached!",
                                             expected2="The specified Node is reachable again!")

    """
    --------------------------------------------------------------------------------------------------------
    GENERIC METHODS
    --------------------------------------------------------------------------------------------------------
    """

    def assert_add_node(self, address, expected_response1, expected_response2):
        with self.telegram:
            self.telegram.send_message(self.BOT_ID, "/start")
            time.sleep(3)
            self.click_button("📡 MY NODES")

            self.click_button("➕ ADD NODE")

            first_response = next(self.telegram.iter_history(self.BOT_ID))
            self.telegram.send_message(self.BOT_ID, address)
            time.sleep(3)
            second_response_1 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
            second_response_2 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

            self.assertEqual(first_response.text, expected_response1, "Expected '" + expected_response1 + "' but got '" + first_response.text + "'")
            self.assertTrue(re.search(expected_response2, second_response_1.text, re.IGNORECASE) or
                            re.search(expected_response2, second_response_2.text, re.IGNORECASE),
                            "Expected '" + expected_response2 + "' but got '" + second_response_1.text + "' and '" + second_response_2.text + "'")

    def assert_back_button(self, text):
        """
        Click back button and assert TG shows what was shown before
        """

        self.click_button("⬅️ BACK")

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

            self.click_button("📡 MY NODES")
            self.click_button("📡 " + valid_address)

            self.click_button("➖ DELETE NODE")

            first_response = next(self.telegram.iter_history(self.BOT_ID))

            self.assertEqual(first_response.text, '⚠️ Do you really want to remove the address from your monitoring '
                                                  'list? ⚠️\n' + valid_address, "➖ DELETE NODE button doesn't work!")

            if confirm:
                self.click_button("YES ✅")
                time.sleep(3)
                second_response_1 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
                second_response_2 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))
                self.assertEqual(second_response_1.text, "❌ Node address got deleted! ❌\n" + valid_address, \
                    "YES button on deletion confirmation does not yield deletion statement")
                self.assertTrue(re.search("add a node", second_response_2.text, re.IGNORECASE),
                                "YES button on deletion confirmation does not go back to nodes menu")
            else:
                self.click_button("NO ❌")
                time.sleep(3)
                second_response = next(self.telegram.iter_history(self.BOT_ID))
                self.assertNotEqual(second_response.text.find("Node: " + valid_address), -1, \
                    "NO button on single address deletion confirmation does not go back to Node details")

    def assert_add_all_nodes(self, confirm):
        with self.telegram:
            self.telegram.send_message(self.BOT_ID, "/start")
            time.sleep(3)
            self.click_button("📡 MY NODES")

            self.click_button("➕ ADD ALL")

            first_response = next(self.telegram.iter_history(self.BOT_ID))

            assert first_response.text == '⚠️ Do you really want to add all available Terra Nodes to your monitoring list? ⚠️', \
                "➕ ADD ALL button does not work!"

            if confirm:
                self.click_button("YES ✅")
                second_response_1 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
                second_response_2 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))
                assert second_response_1.text == "Added all Terra Nodes! 👌", \
                    "YES button on ➕ ADD ALL confirmation does not yield addition statement"
                assert second_response_2.text == "Click an address from the list below or add a node:", \
                    "YES button on ➕ ADD ALL confirmation does not go back to 📡 MY NODES menu"
                assert second_response_2.reply_markup.inline_keyboard[1][0].text.find('terravaloper') != -1, \
                    "Nodes are not added after YES button on ➕ ADD ALL confirmation"
            else:
                self.click_button("NO ❌")
                time.sleep(3)
                second_response = next(self.telegram.iter_history(self.BOT_ID))
                assert second_response.text == "Click an address from the list below or add a node:", \
                    "NO button on ➕ ADD ALL confirmation does not go back to 📡 MY NODES menu"

            print("➕ ADD ALL with confirmation=" + str(confirm) + " ✅")
            print("------------------------")


    def assert_delete_all_nodes(self, confirm):
        with self.telegram:
            self.telegram.send_message(self.BOT_ID, "/start")
            time.sleep(3)
            self.click_button("📡 MY NODES")
            self.click_button("➕ ADD ALL")

            self.telegram.send_message(self.BOT_ID, "/start")
            time.sleep(3)
            self.click_button("📡 MY NODES")
            self.click_button("➖ REMOVE ALL")

            first_response = next(self.telegram.iter_history(self.BOT_ID))

            assert first_response.text == '⚠️ Do you really want to remove all Terra Nodes from your monitoring list? ⚠️', \
                "➖ REMOVE ALL button does not work!"

            if confirm:
                self.click_button("YES ✅")
                second_response_1 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
                second_response_2 = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))
                assert second_response_1.text == "❌ Deleted all Terra Nodes! ❌", \
                    "YES button on ➖ REMOVE ALL confirmation does not yield deletion statement"
                assert second_response_2.text == "Click an address from the list below or add a node:", \
                    "YES button on ➖ REMOVE ALL confirmation does not go back to 📡 MY NODES menu"
                assert second_response_2.reply_markup.inline_keyboard[0][0].text == '➕ ADD ALL' and \
                       "Nodes are not deleted after YES button on ➖ REMOVE ALL confirmation"
            else:
                self.click_button("NO ❌")
                time.sleep(3)
                second_response = next(self.telegram.iter_history(self.BOT_ID))
                assert second_response.text == "Click an address from the list below or add a node:", \
                    "NO button on ➖ REMOVE ALL confirmation does not go back to 📡 MY NODES menu"

            print("➖ REMOVE ALL with confirmation=" + str(confirm) + " ✅")
            print("------------------------")

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
        self.assertTrue(re.search("I am your Terra Node Bot. 🤖", second_response.text, re.IGNORECASE),
                        "'I am your Terra Node Bot. 🤖' - not visible after node address change notification.")

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
            for x in range(40):
                block_height = data['height']
                new_block_height = int(block_height) + 20
                data['height'] = str(new_block_height)
                with open(file_name, 'w') as json_write_file:
                    json.dump(data, json_write_file)
                time.sleep(1)

        with self.telegram:
            first_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
            second_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

        self.assertNotEqual(first_response.text.find(expected_response1), -1, "Expected '" + expected_response1 + \
                                                                  "'\nbut got\n'" + first_response.text + "'")
        self.assertTrue(re.search("I am your Terra Node Bot. 🤖", second_response.text, re.IGNORECASE),
                        "'I am your Terra Node Bot. 🤖' - not visible after block height notification.")

        time.sleep(35)
        with self.telegram:
            first_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
            second_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

        self.assertNotEqual(first_response.text.find(expected_response2), -1, "Expected '" + expected_response2 + \
                                                                  "'\nbut got\n'" + first_response.text + "'")
        self.assertTrue(re.search("I am your Terra Node Bot. 🤖", second_response.text, re.IGNORECASE),
                        "'I am your Terra Node Bot. 🤖' - not visible after block height notification.")

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
        self.assertTrue(re.search("I am your Terra Node Bot. 🤖", second_response.text, re.IGNORECASE),
                        "'I am your Terra Node Bot. 🤖' - not visible after catching_up=" + str(catching_up) + " notification")

    def assert_unreachable_notification(self, file_name, expected1, expected2):
        os.rename(file_name + ".json", file_name + "_renamed.json")
        time.sleep(20)

        with self.telegram:
            first_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
            second_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

        self.assertNotEqual(first_response.text.find(expected1), -1,
                            "Expected '" + expected1 + "' but got '" + first_response.text + "'")
        self.assertTrue(re.search("I am your Terra Node Bot. 🤖", second_response.text, re.IGNORECASE),
                        "'I am your Terra Node Bot. 🤖' - not visible after node address change notification.")

        os.rename(file_name + "_renamed.json", file_name + ".json")
        time.sleep(20)

        with self.telegram:
            first_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 1, None))
            second_response = next(itertools.islice(self.telegram.iter_history(self.BOT_ID), 0, None))

        self.assertNotEqual(first_response.text.find(expected2), -1,
                            "Expected '" + expected2 + "' but got '" + first_response.text + "'")
        self.assertTrue(re.search("I am your Terra Node Bot. 🤖", second_response.text, re.IGNORECASE),
                        "'I am your Terra Node Bot. 🤖' - not visible after node address change notification.")

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

