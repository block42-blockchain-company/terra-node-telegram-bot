import unittest
from unittest.mock import Mock, patch

from constants.messages import NODE_STARTED_SYNCING_MSG, NODE_FINISHED_SYNCING_MSG
from jobs.sentry_jobs import check_sentry_nodes_statuses


class SentryJobsTest(unittest.TestCase):
    context = {}
    context_mock = Mock()
    mock_ip = '192.168.42'

    def setUp(self) -> None:
        self.context['bot_data'] = {}
        self.context_mock.job.context = self.context

    @patch('jobs.sentry_jobs.SENTRY_NODES', [mock_ip])
    @patch('jobs.sentry_jobs.is_syncing')
    @patch('jobs.sentry_jobs.try_message_to_all_chats_and_platforms')
    def test_sentry_nodes_statuses_job(self, try_message_mock: Mock, is_syncing_mock: Mock):
        is_syncing_mock.return_value = False
        check_sentry_nodes_statuses(self.context_mock)
        try_message_mock.assert_not_called()

        is_syncing_mock.return_value = True
        check_sentry_nodes_statuses(self.context_mock)
        try_message_mock.assert_called_with(self.context_mock, NODE_STARTED_SYNCING_MSG.format(self.mock_ip),
                                            remove_job_when_blocked=False)

        is_syncing_mock.return_value = True
        check_sentry_nodes_statuses(self.context_mock)
        try_message_mock.assert_called_once()

        is_syncing_mock.return_value = False
        check_sentry_nodes_statuses(self.context_mock)
        self.assertEqual(try_message_mock.call_count, 2)
        try_message_mock.assert_called_with(self.context_mock, NODE_FINISHED_SYNCING_MSG.format(self.mock_ip),
                                            remove_job_when_blocked=False)

    @patch('jobs.sentry_jobs.SENTRY_NODES', [mock_ip])
    @patch('jobs.sentry_jobs.is_syncing')
    @patch('jobs.sentry_jobs.try_message_to_all_chats_and_platforms')
    def test_called_when_syncing_at_startup(self, try_message_mock: Mock, is_syncing_mock: Mock):
        is_syncing_mock.return_value = True
        check_sentry_nodes_statuses(self.context_mock)
        try_message_mock.assert_called_with(self.context_mock, NODE_STARTED_SYNCING_MSG.format(self.mock_ip),
                                            remove_job_when_blocked=False)
