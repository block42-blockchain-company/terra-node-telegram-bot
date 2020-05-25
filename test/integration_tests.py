import os
import unittest
import time
from subprocess import Popen

from pyrogram import Client as TelegramClient


"""
######################################################################################################################################################
Test Cases
######################################################################################################################################################
"""


class TerraNodeBot(unittest.TestCase):
    terra_node_bot_process = {}
    telegram = TelegramClient(
        "my_account",
        api_id=os.environ['TELEGRAM_API_ID'],
        api_hash=os.environ['TELEGRAM_API_HASH']
    )

    BOT_ID = os.environ['TELEGRAM_BOT_ID']


    def setUpClass(cls):
        # Delete previous sessions for clean testing
        if os.path.exists("../storage/session.data"):
            os.remove("../storage/session.data")

        # Start the Telegram Terra Node Bot
        self.terra_node_bot_process = Popen(['python3', 'terra_node_bot.py'], cwd="../")
        time.sleep(5)

    def test_start(self):
        with self.telegram:
            self.telegram.send_message(self.BOT_ID, "/start")
            time.sleep(3)


        #response = next(self.telegram.iter_history(self.BOT_ID))
        #self.assertEqual(response.reply_markup.inline_keyboard[0][0].text,
        #                 "Add Node", "Add Node not visible after /start")


    def tearDownClass(cls):
        self.terra_node_bot_process.terminate()


if __name__ == '__main__':
    unittest.main()

