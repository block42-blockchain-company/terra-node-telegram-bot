import unittest
from unittest.mock import patch

from constants.env_variables import read_list_from_env


def dict_mock(variable, default):
    return {"block": '42', "multistr": "hello;my,world", 'multiint': '1,2;3'}.get(variable, default)


class UtilTest(unittest.TestCase):

    def setUp(self) -> None:
        pass

    @patch('bot.constants.env_variables.os.getenv', dict_mock)
    def test_read_wrong_name(self):
        res = read_list_from_env("no_variable", int)
        self.assertEqual(res, [])

    @patch('bot.constants.env_variables.os.getenv', dict_mock)
    def test_read_one_string(self):
        res = read_list_from_env("block", str)
        self.assertEqual(res, ['42'])

    @patch('bot.constants.env_variables.os.getenv', dict_mock)
    def test_read_one_int(self):
        res = read_list_from_env("block", int)
        self.assertEqual(res, [42])

    @patch('bot.constants.env_variables.os.getenv', dict_mock)
    def test_read_multiple_strings(self):
        res = read_list_from_env("multistr", str)
        self.assertEqual(res, ['hello', 'my', 'world'])

    @patch('bot.constants.env_variables.os.getenv', dict_mock)
    def test_read_multiple_ints(self):
        res = read_list_from_env("multiint", int)
        self.assertEqual(res, [1, 2, 3])
