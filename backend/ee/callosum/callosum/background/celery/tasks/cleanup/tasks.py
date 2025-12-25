from datetime import datetime
from datetime import timedelta

from celery import shared_task

from ee.callosum.db.query_history import get_all_query_history_export_tasks
from callosum.configs.app_configs import JOB_TIMEOUT
from callosum.configs.constants import CallosumCeleryTask
from callosum.db.engine.sql_engine import get_session_with_tenant
from callosum.db.enums import TaskStatus
from callosum.db.tasks import delete_task_with_id
from callosum.utils.logger import setup_logger


logger = setup_logger()


@shared_task(
    name=CallosumCeleryTask.EXPORT_QUERY_HISTORY_CLEANUP_TASK,
    ignore_result=True,
    soft_time_limit=JOB_TIMEOUT,
)
def export_query_history_cleanup_task(*, tenant_id: str) -> None:
    with get_session_with_tenant(tenant_id=tenant_id) as db_session:
        tasks = get_all_query_history_export_tasks(db_session=db_session)

        for task in tasks:
            if task.status == TaskStatus.SUCCESS:
                delete_task_with_id(db_session=db_session, task_id=task.task_id)
            elif task.status == TaskStatus.FAILURE:
                if task.start_time:
                    deadline = task.start_time + timedelta(hours=24)
                    now = datetime.now()
                    if now < deadline:
                        continue

                logger.error(
                    f"Task with {task.task_id=} failed; it is being deleted now"
                )
                delete_task_with_id(db_session=db_session, task_id=task.task_id)
