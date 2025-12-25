"""API endpoints for default assistant configuration."""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from callosum.auth.users import current_admin_user
from callosum.db.engine.sql_engine import get_session
from callosum.db.models import User
from callosum.db.persona import get_default_assistant
from callosum.db.persona import update_default_assistant_configuration
from callosum.server.features.default_assistant.models import DefaultAssistantConfiguration
from callosum.server.features.default_assistant.models import DefaultAssistantUpdateRequest
from callosum.utils.logger import setup_logger

logger = setup_logger()

router = APIRouter(prefix="/admin/default-assistant")


@router.get("/configuration")
def get_default_assistant_configuration(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> DefaultAssistantConfiguration:
    """Get the current default assistant configuration.

    Returns:
        DefaultAssistantConfiguration with current tool IDs and system prompt
    """
    persona = get_default_assistant(db_session)
    if not persona:
        raise HTTPException(status_code=404, detail="Default assistant not found")

    # Extract DB tool IDs from the persona's tools
    tool_ids = [tool.id for tool in persona.tools]

    return DefaultAssistantConfiguration(
        tool_ids=tool_ids,
        system_prompt=persona.system_prompt or "",
    )


@router.patch("")
def update_default_assistant(
    update_request: DefaultAssistantUpdateRequest,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> DefaultAssistantConfiguration:
    """Update the default assistant configuration.

    Args:
        update_request: Request with optional tool_ids and system_prompt

    Returns:
        Updated DefaultAssistantConfiguration

    Raises:
        400: If invalid tool IDs are provided
        404: If default assistant not found
    """
    # Validate tool IDs if provided
    try:
        # Update the default assistant
        updated_persona = update_default_assistant_configuration(
            db_session=db_session,
            tool_ids=update_request.tool_ids,
            system_prompt=update_request.system_prompt,
        )

        # Return the updated configuration
        tool_ids = [tool.id for tool in updated_persona.tools]
        return DefaultAssistantConfiguration(
            tool_ids=tool_ids,
            system_prompt=updated_persona.system_prompt or "",
        )

    except ValueError as e:
        if "Default assistant not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
