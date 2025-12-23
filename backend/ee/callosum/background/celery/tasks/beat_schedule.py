from datetime import timedelta
from typing import Any

from callosum.background.celery.tasks.beat_schedule import (
    cloud_tasks_to_schedule as base_cloud_tasks_to_schedule,
)
from callosum.background.celery.tasks.beat_schedule import (
    tasks_to_schedule as base_tasks_to_schedule,
)
from callosum.configs.constants import CallosumCeleryTask

ee_tasks_to_schedule = [
    {
        "name": "autogenerate-usage-report",
        "task": CallosumCeleryTask.AUTOGENERATE_USAGE_REPORT_TASK,
        "schedule": timedelta(days=30),  # TODO: change this to config flag
    },
    {
        "name": "check-ttl-management",
        "task": CallosumCeleryTask.CHECK_TTL_MANAGEMENT_TASK,
        "schedule": timedelta(hours=1),
    },
]


def get_cloud_tasks_to_schedule() -> list[dict[str, Any]]:
    return base_cloud_tasks_to_schedule


def get_tasks_to_schedule() -> list[dict[str, Any]]:
    return ee_tasks_to_schedule + base_tasks_to_schedule
