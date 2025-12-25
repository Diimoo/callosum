from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ee.callosum.callosumbot.slack.handlers.handle_standard_answers import (
    oneoff_standard_answers,
)
from ee.callosum.server.query_and_chat.models import StandardAnswerRequest
from ee.callosum.server.query_and_chat.models import StandardAnswerResponse
from callosum.auth.users import current_user
from callosum.db.engine.sql_engine import get_session
from callosum.db.models import User
from callosum.utils.logger import setup_logger

logger = setup_logger()

basic_router = APIRouter(prefix="/query")


@basic_router.get("/standard-answer")
def get_standard_answer(
    request: StandardAnswerRequest,
    db_session: Session = Depends(get_session),
    _: User | None = Depends(current_user),
) -> StandardAnswerResponse:
    try:
        standard_answers = oneoff_standard_answers(
            message=request.message,
            slack_bot_categories=request.slack_bot_categories,
            db_session=db_session,
        )
        return StandardAnswerResponse(standard_answers=standard_answers)
    except Exception as e:
        logger.error(f"Error in get_standard_answer: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred")
