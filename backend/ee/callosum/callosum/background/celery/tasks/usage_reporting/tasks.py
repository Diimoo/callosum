from datetime import datetime
from uuid import UUID

from celery import shared_task
from celery import Task

from ee.callosum.server.reporting.usage_export_generation import create_new_usage_report
from callosum.configs.app_configs import JOB_TIMEOUT
from callosum.configs.constants import CallosumCeleryTask
from callosum.db.engine.sql_engine import get_session_with_current_tenant
from callosum.utils.logger import setup_logger

logger = setup_logger()


@shared_task(
    name=CallosumCeleryTask.GENERATE_USAGE_REPORT_TASK,
    ignore_result=True,
    soft_time_limit=JOB_TIMEOUT,
    bind=True,
    trail=False,
)
def generate_usage_report_task(
    self: Task,
    *,
    tenant_id: str,
    user_id: str | None = None,
    period_from: str | None = None,
    period_to: str | None = None,
) -> None:
    """User-initiated usage report generation task"""
    # Parse period if provided
    period = None
    if period_from and period_to:
        period = (
            datetime.fromisoformat(period_from),
            datetime.fromisoformat(period_to),
        )

    # Generate the report
    with get_session_with_current_tenant() as db_session:
        create_new_usage_report(
            db_session=db_session,
            user_id=UUID(user_id) if user_id else None,
            period=period,
        )
