import copy
from datetime import timedelta
from typing import Any

from callosum.configs.app_configs import ENTERPRISE_EDITION_ENABLED
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

# hack to slow down task dispatch in the cloud until
# we have a better implementation (backpressure, etc)
# Note that DynamicTenantScheduler can adjust the runtime value for this via Redis
CLOUD_BEAT_MULTIPLIER_DEFAULT = 8.0
CLOUD_DOC_PERMISSION_SYNC_MULTIPLIER_DEFAULT = 1.0

# tasks that run in either self-hosted on cloud
beat_task_templates: list[dict] = [
    {
        "name": "check-for-user-file-processing",
        "task": CallosumCeleryTask.CHECK_FOR_USER_FILE_PROCESSING,
        "schedule": timedelta(seconds=20),
        "options": {
            "priority": CallosumCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-user-file-project-sync",
        "task": CallosumCeleryTask.CHECK_FOR_USER_FILE_PROJECT_SYNC,
        "schedule": timedelta(seconds=20),
        "options": {
            "priority": CallosumCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-user-file-delete",
        "task": CallosumCeleryTask.CHECK_FOR_USER_FILE_DELETE,
        "schedule": timedelta(seconds=20),
        "options": {
            "priority": CallosumCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "user-file-docid-migration",
        "task": CallosumCeleryTask.USER_FILE_DOCID_MIGRATION,
        "schedule": timedelta(minutes=10),
        "options": {
            "priority": CallosumCeleryPriority.HIGH,
            "expires": BEAT_EXPIRES_DEFAULT,
            "queue": CallosumCeleryQueues.USER_FILES_INDEXING,
        },
    },
    {
        "name": "check-for-kg-processing",
        "task": CallosumCeleryTask.CHECK_KG_PROCESSING,
        "schedule": timedelta(seconds=60),
        "options": {
            "priority": CallosumCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-kg-processing-clustering-only",
        "task": CallosumCeleryTask.CHECK_KG_PROCESSING_CLUSTERING_ONLY,
        "schedule": timedelta(seconds=600),
        "options": {
            "priority": CallosumCeleryPriority.LOW,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-indexing",
        "task": CallosumCeleryTask.CHECK_FOR_INDEXING,
        "schedule": timedelta(seconds=15),
        "options": {
            "priority": CallosumCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-checkpoint-cleanup",
        "task": CallosumCeleryTask.CHECK_FOR_CHECKPOINT_CLEANUP,
        "schedule": timedelta(hours=1),
        "options": {
            "priority": CallosumCeleryPriority.LOW,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-index-attempt-cleanup",
        "task": CallosumCeleryTask.CHECK_FOR_INDEX_ATTEMPT_CLEANUP,
        "schedule": timedelta(minutes=30),
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
        "name": "check-for-vespa-sync",
        "task": CallosumCeleryTask.CHECK_FOR_VESPA_SYNC_TASK,
        "schedule": timedelta(seconds=20),
        "options": {
            "priority": CallosumCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-pruning",
        "task": CallosumCeleryTask.CHECK_FOR_PRUNING,
        "schedule": timedelta(seconds=20),
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
]

if ENTERPRISE_EDITION_ENABLED:
    beat_task_templates.extend(
        [
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
    )

# Only add the LLM model update task if the API URL is configured
if LLM_MODEL_UPDATE_API_URL:
    beat_task_templates.append(
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


def make_cloud_generator_task(task: dict[str, Any]) -> dict[str, Any]:
    cloud_task: dict[str, Any] = {}

    # constant options for cloud beat task generators
    task_schedule: timedelta = task["schedule"]
    cloud_task["schedule"] = task_schedule
    cloud_task["options"] = {}
    cloud_task["options"]["priority"] = CallosumCeleryPriority.HIGHEST
    cloud_task["options"]["expires"] = BEAT_EXPIRES_DEFAULT

    # settings dependent on the original task
    cloud_task["name"] = f"{CALLOSUM_CLOUD_CELERY_TASK_PREFIX}_{task['name']}"
    cloud_task["task"] = CallosumCeleryTask.CLOUD_BEAT_TASK_GENERATOR
    cloud_task["kwargs"] = {}
    cloud_task["kwargs"]["task_name"] = task["task"]

    optional_fields = ["queue", "priority", "expires"]
    for field in optional_fields:
        if field in task["options"]:
            cloud_task["kwargs"][field] = task["options"][field]

    return cloud_task


# tasks that only run in the cloud and are system wide
# the name attribute must start with CALLOSUM_CLOUD_CELERY_TASK_PREFIX = "cloud" to be seen
# by the DynamicTenantScheduler as system wide task and not a per tenant task
beat_cloud_tasks: list[dict] = [
    # cloud specific tasks
    {
        "name": f"{CALLOSUM_CLOUD_CELERY_TASK_PREFIX}_monitor-alembic",
        "task": CallosumCeleryTask.CLOUD_MONITOR_ALEMBIC,
        "schedule": timedelta(hours=1),
        "options": {
            "queue": CallosumCeleryQueues.MONITORING,
            "priority": CallosumCeleryPriority.HIGH,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": f"{CALLOSUM_CLOUD_CELERY_TASK_PREFIX}_monitor-celery-queues",
        "task": CallosumCeleryTask.CLOUD_MONITOR_CELERY_QUEUES,
        "schedule": timedelta(seconds=30),
        "options": {
            "queue": CallosumCeleryQueues.MONITORING,
            "priority": CallosumCeleryPriority.HIGH,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": f"{CALLOSUM_CLOUD_CELERY_TASK_PREFIX}_check-available-tenants",
        "task": CallosumCeleryTask.CLOUD_CHECK_AVAILABLE_TENANTS,
        "schedule": timedelta(minutes=10),
        "options": {
            "queue": CallosumCeleryQueues.MONITORING,
            "priority": CallosumCeleryPriority.HIGH,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": f"{CALLOSUM_CLOUD_CELERY_TASK_PREFIX}_monitor-celery-pidbox",
        "task": CallosumCeleryTask.CLOUD_MONITOR_CELERY_PIDBOX,
        "schedule": timedelta(hours=4),
        "options": {
            "queue": CallosumCeleryQueues.MONITORING,
            "priority": CallosumCeleryPriority.HIGH,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
]

# tasks that only run self hosted
tasks_to_schedule: list[dict] = []
if not MULTI_TENANT:
    tasks_to_schedule.extend(
        [
            {
                "name": "monitor-celery-queues",
                "task": CallosumCeleryTask.MONITOR_CELERY_QUEUES,
                "schedule": timedelta(seconds=10),
                "options": {
                    "priority": CallosumCeleryPriority.MEDIUM,
                    "expires": BEAT_EXPIRES_DEFAULT,
                    "queue": CallosumCeleryQueues.MONITORING,
                },
            },
            {
                "name": "monitor-process-memory",
                "task": CallosumCeleryTask.MONITOR_PROCESS_MEMORY,
                "schedule": timedelta(minutes=5),
                "options": {
                    "priority": CallosumCeleryPriority.LOW,
                    "expires": BEAT_EXPIRES_DEFAULT,
                    "queue": CallosumCeleryQueues.MONITORING,
                },
            },
            {
                "name": "celery-beat-heartbeat",
                "task": CallosumCeleryTask.CELERY_BEAT_HEARTBEAT,
                "schedule": timedelta(minutes=1),
                "options": {
                    "priority": CallosumCeleryPriority.HIGHEST,
                    "expires": BEAT_EXPIRES_DEFAULT,
                    "queue": CallosumCeleryQueues.PRIMARY,
                },
            },
        ]
    )

    tasks_to_schedule.extend(beat_task_templates)


def generate_cloud_tasks(
    beat_tasks: list[dict], beat_templates: list[dict], beat_multiplier: float
) -> list[dict[str, Any]]:
    """
    beat_tasks: system wide tasks that can be sent as is
    beat_templates: task templates that will be transformed into per tenant tasks via
    the cloud_beat_task_generator
    beat_multiplier: a multiplier that can be applied on top of the task schedule
    to speed up or slow down the task generation rate. useful in production.

    Returns a list of cloud tasks, which consists of incoming tasks + tasks generated
    from incoming templates.
    """

    if beat_multiplier <= 0:
        raise ValueError("beat_multiplier must be positive!")

    cloud_tasks: list[dict] = []

    # generate our tenant aware cloud tasks from the templates
    for beat_template in beat_templates:
        cloud_task = make_cloud_generator_task(beat_template)
        cloud_tasks.append(cloud_task)

    # factor in the cloud multiplier for the above
    for cloud_task in cloud_tasks:
        cloud_task["schedule"] = cloud_task["schedule"] * beat_multiplier

    # add the fixed cloud/system beat tasks. No multiplier for these.
    cloud_tasks.extend(copy.deepcopy(beat_tasks))
    return cloud_tasks


def get_cloud_tasks_to_schedule(beat_multiplier: float) -> list[dict[str, Any]]:
    return generate_cloud_tasks(beat_cloud_tasks, beat_task_templates, beat_multiplier)


def get_tasks_to_schedule() -> list[dict[str, Any]]:
    return tasks_to_schedule
