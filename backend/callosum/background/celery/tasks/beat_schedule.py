from datetime import timedelta
from typing import Any

from callosum.configs.app_configs import LLM_MODEL_UPDATE_API_URL
from callosum.configs.constants import CALLOSUM_CLOUD_CELERY_TASK_PREFIX
from callosum.configs.constants import CallosumCeleryPriority
from callosum.configs.constants import CallosumCeleryQueues
from callosum.configs.constants import CallosumCeleryTask
from shared_configs.configs import MULTI_TENANT

# choosing 15 minutes because it roughly gives us enough time to process many tasks
# we might be able to reduce this greatly if we can run a unified
# loop across all tenants rather than tasks per tenant

# we set expires because it isn't necessary to queue up these tasks
# it's only important that they run relatively regularly
BEAT_EXPIRES_DEFAULT = 15 * 60  # 15 minutes (in seconds)

# tasks that only run in the cloud
# the name attribute must start with CALLOSUM_CELERY_CLOUD_PREFIX = "cloud" to be filtered
# by the DynamicTenantScheduler
cloud_tasks_to_schedule = [
    {
        "name": f"{CALLOSUM_CLOUD_CELERY_TASK_PREFIX}_check-for-indexing",
        "task": CallosumCeleryTask.CLOUD_CHECK_FOR_INDEXING,
        "schedule": timedelta(seconds=15),
        "options": {
            "priority": CallosumCeleryPriority.HIGHEST,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
]

# tasks that run in either self-hosted on cloud
tasks_to_schedule = [
    {
        "name": "check-for-vespa-sync",
        "task": CallosumCeleryTask.CHECK_FOR_VESPA_SYNC_TASK,
        "schedule": timedelta(seconds=20),
        "options": {
            "priority": CallosumCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-connector-deletion",
        "task": CallosumCeleryTask.CHECK_FOR_CONNECTOR_DELETION,
        "schedule": timedelta(seconds=20),
        "options": {
            "priority": CallosumCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-prune",
        "task": CallosumCeleryTask.CHECK_FOR_PRUNING,
        "schedule": timedelta(seconds=15),
        "options": {
            "priority": CallosumCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "kombu-message-cleanup",
        "task": CallosumCeleryTask.KOMBU_MESSAGE_CLEANUP_TASK,
        "schedule": timedelta(seconds=3600),
        "options": {
            "priority": CallosumCeleryPriority.LOWEST,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "monitor-vespa-sync",
        "task": CallosumCeleryTask.MONITOR_VESPA_SYNC,
        "schedule": timedelta(seconds=5),
        "options": {
            "priority": CallosumCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "monitor-background-processes",
        "task": CallosumCeleryTask.MONITOR_BACKGROUND_PROCESSES,
        "schedule": timedelta(minutes=5),
        "options": {
            "priority": CallosumCeleryPriority.LOW,
            "expires": BEAT_EXPIRES_DEFAULT,
            "queue": CallosumCeleryQueues.MONITORING,
        },
    },
    {
        "name": "check-for-doc-permissions-sync",
        "task": CallosumCeleryTask.CHECK_FOR_DOC_PERMISSIONS_SYNC,
        "schedule": timedelta(seconds=30),
        "options": {
            "priority": CallosumCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-external-group-sync",
        "task": CallosumCeleryTask.CHECK_FOR_EXTERNAL_GROUP_SYNC,
        "schedule": timedelta(seconds=20),
        "options": {
            "priority": CallosumCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
]

if not MULTI_TENANT:
    tasks_to_schedule.append(
        {
            "name": "check-for-indexing",
            "task": CallosumCeleryTask.CHECK_FOR_INDEXING,
            "schedule": timedelta(seconds=15),
            "options": {
                "priority": CallosumCeleryPriority.MEDIUM,
                "expires": BEAT_EXPIRES_DEFAULT,
            },
        }
    )

# Only add the LLM model update task if the API URL is configured
if LLM_MODEL_UPDATE_API_URL:
    tasks_to_schedule.append(
        {
            "name": "check-for-llm-model-update",
            "task": CallosumCeleryTask.CHECK_FOR_LLM_MODEL_UPDATE,
            "schedule": timedelta(hours=1),  # Check every hour
            "options": {
                "priority": CallosumCeleryPriority.LOW,
                "expires": BEAT_EXPIRES_DEFAULT,
            },
        }
    )


def get_cloud_tasks_to_schedule() -> list[dict[str, Any]]:
    return cloud_tasks_to_schedule


def get_tasks_to_schedule() -> list[dict[str, Any]]:
    return tasks_to_schedule
