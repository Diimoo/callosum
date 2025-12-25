from typing import Any

from celery import shared_task
from celery import Task

from callosum.configs.app_configs import JOB_TIMEOUT
from callosum.configs.constants import CallosumCeleryTask
from callosum.evals.eval import run_eval
from callosum.evals.models import EvalConfigurationOptions
from callosum.utils.logger import setup_logger

logger = setup_logger()


@shared_task(
    name=CallosumCeleryTask.EVAL_RUN_TASK,
    ignore_result=True,
    soft_time_limit=JOB_TIMEOUT,
    bind=True,
    trail=False,
)
def eval_run_task(
    self: Task,
    *,
    configuration_dict: dict[str, Any],
) -> None:
    """Background task to run an evaluation with the given configuration"""
    try:
        configuration = EvalConfigurationOptions.model_validate(configuration_dict)
        run_eval(configuration, remote_dataset_name=configuration.dataset_name)
        logger.info("Successfully completed eval run task")

    except Exception:
        logger.error("Failed to run eval task")
        raise
