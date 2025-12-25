from fastapi import APIRouter
from fastapi import Depends

from ee.callosum.auth.users import current_cloud_superuser
from callosum.background.celery.apps.client import celery_app as client_app
from callosum.configs.constants import CallosumCeleryTask
from callosum.db.models import User
from callosum.evals.models import EvalConfigurationOptions
from callosum.server.evals.models import EvalRunAck
from callosum.utils.logger import setup_logger

logger = setup_logger()

router = APIRouter(prefix="/evals")


@router.post("/eval_run", response_model=EvalRunAck)
def eval_run(
    request: EvalConfigurationOptions,
    user: User = Depends(current_cloud_superuser),
) -> EvalRunAck:
    """
    Run an evaluation with the given message and optional dataset.
    This endpoint requires a valid API key for authentication.
    """
    client_app.send_task(
        CallosumCeleryTask.EVAL_RUN_TASK,
        kwargs={
            "configuration_dict": request.model_dump(),
        },
    )
    return EvalRunAck(success=True)
