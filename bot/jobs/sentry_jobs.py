from constants.constants import SENTRY_JOB_INTERVAL_IN_SECONDS
from constants.env_variables import SENTRY_NODES
from constants.logger import logger
from constants.messages import NODE_STARTED_SYNCING_MSG, NODE_FINISHED_SYNCING_MSG
from helpers import try_message_to_all_chats_and_platforms
from service.network_service import is_syncing


def setup_sentry_jobs(dispatcher):
    dispatcher.job_queue.run_repeating(check_sentry_nodes_statuses,
                                       interval=SENTRY_JOB_INTERVAL_IN_SECONDS,
                                       context={'bot_data': dispatcher.bot_data})


def check_sentry_nodes_statuses(context):
    sentry_nodes_data = context.job.context['bot_data'].setdefault('sentry_nodes', {})

    for node_ip in SENTRY_NODES:
        message = check_sentry_node_status(node_ip, sentry_nodes_data)
        if message is not None:
            try_message_to_all_chats_and_platforms(context, message, remove_job_when_blocked=False)


def check_sentry_node_status(node_ip, sentry_nodes_data) -> [None, str]:
    try:
        is_currently_syncing = is_syncing(node_ip)
    except Exception as e:
        logger.error(e)
        return None

    was_syncing = sentry_nodes_data.setdefault(node_ip, {}).setdefault('syncing', False)

    if was_syncing != is_currently_syncing:
        sentry_nodes_data[node_ip]['syncing'] = is_currently_syncing

        if is_currently_syncing:
            text = NODE_STARTED_SYNCING_MSG.format(node_ip)
        else:
            text = NODE_FINISHED_SYNCING_MSG.format(node_ip)

        return text
    else:
        return None
