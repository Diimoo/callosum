import uuid
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import UploadFile
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from callosum.auth.users import current_admin_user
from callosum.auth.users import current_chat_accesssible_user
from callosum.auth.users import current_curator_or_admin_user
from callosum.auth.users import current_limited_user
from callosum.auth.users import current_user
from callosum.configs.constants import FileOrigin
from callosum.configs.constants import MilestoneRecordType
from callosum.configs.constants import NotificationType
from callosum.db.engine import get_current_tenant_id
from callosum.db.engine import get_session
from callosum.db.models import StarterMessageModel as StarterMessage
from callosum.db.models import User
from callosum.db.notification import create_notification
from callosum.db.persona import create_assistant_label
from callosum.db.persona import create_update_persona
from callosum.db.persona import delete_persona_label
from callosum.db.persona import get_assistant_labels
from callosum.db.persona import get_persona_by_id
from callosum.db.persona import get_personas_for_user
from callosum.db.persona import mark_persona_as_deleted
from callosum.db.persona import mark_persona_as_not_deleted
from callosum.db.persona import update_all_personas_display_priority
from callosum.db.persona import update_persona_label
from callosum.db.persona import update_persona_public_status
from callosum.db.persona import update_persona_shared_users
from callosum.db.persona import update_persona_visibility
from callosum.db.prompts import build_prompt_name_from_persona_name
from callosum.db.prompts import upsert_prompt
from callosum.file_store.file_store import get_default_file_store
from callosum.file_store.models import ChatFileType
from callosum.secondary_llm_flows.starter_message_creation import (
    generate_starter_messages,
)
from callosum.server.features.persona.models import GenerateStarterMessageRequest
from callosum.server.features.persona.models import ImageGenerationToolStatus
from callosum.server.features.persona.models import PersonaLabelCreate
from callosum.server.features.persona.models import PersonaLabelResponse
from callosum.server.features.persona.models import PersonaSharedNotificationData
from callosum.server.features.persona.models import PersonaSnapshot
from callosum.server.features.persona.models import PersonaUpsertRequest
from callosum.server.features.persona.models import PromptSnapshot
from callosum.server.models import DisplayPriorityRequest
from callosum.tools.utils import is_image_generation_available
from callosum.utils.logger import setup_logger
from callosum.utils.telemetry import create_milestone_and_report


logger = setup_logger()


admin_router = APIRouter(prefix="/admin/persona")
basic_router = APIRouter(prefix="/persona")


class IsVisibleRequest(BaseModel):
    is_visible: bool


class IsPublicRequest(BaseModel):
    is_public: bool


@admin_router.patch("/{persona_id}/visible")
def patch_persona_visibility(
    persona_id: int,
    is_visible_request: IsVisibleRequest,
    user: User | None = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    update_persona_visibility(
        persona_id=persona_id,
        is_visible=is_visible_request.is_visible,
        db_session=db_session,
        user=user,
    )


@basic_router.patch("/{persona_id}/public")
def patch_user_presona_public_status(
    persona_id: int,
    is_public_request: IsPublicRequest,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    try:
        update_persona_public_status(
            persona_id=persona_id,
            is_public=is_public_request.is_public,
            db_session=db_session,
            user=user,
        )
    except ValueError as e:
        logger.exception("Failed to update persona public status")
        raise HTTPException(status_code=403, detail=str(e))


@admin_router.put("/display-priority")
def patch_persona_display_priority(
    display_priority_request: DisplayPriorityRequest,
    _: User | None = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    update_all_personas_display_priority(
        display_priority_map=display_priority_request.display_priority_map,
        db_session=db_session,
    )


@admin_router.get("")
def list_personas_admin(
    user: User | None = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
    include_deleted: bool = False,
    get_editable: bool = Query(False, description="If true, return editable personas"),
) -> list[PersonaSnapshot]:
    return [
        PersonaSnapshot.from_model(persona)
        for persona in get_personas_for_user(
            db_session=db_session,
            user=user,
            get_editable=get_editable,
            include_deleted=include_deleted,
            joinedload_all=True,
        )
    ]


@admin_router.patch("/{persona_id}/undelete")
def undelete_persona(
    persona_id: int,
    user: User | None = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    mark_persona_as_not_deleted(
        persona_id=persona_id,
        user=user,
        db_session=db_session,
    )


# used for assistat profile pictures
@admin_router.post("/upload-image")
def upload_file(
    file: UploadFile,
    db_session: Session = Depends(get_session),
    _: User | None = Depends(current_user),
) -> dict[str, str]:
    file_store = get_default_file_store(db_session)
    file_type = ChatFileType.IMAGE
    file_id = str(uuid.uuid4())
    file_store.save_file(
        file_name=file_id,
        content=file.file,
        display_name=file.filename,
        file_origin=FileOrigin.CHAT_UPLOAD,
        file_type=file.content_type or file_type.value,
    )
    return {"file_id": file_id}


"""Endpoints for all"""


@basic_router.post("")
def create_persona(
    persona_upsert_request: PersonaUpsertRequest,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
    tenant_id: str | None = Depends(get_current_tenant_id),
) -> PersonaSnapshot:
    prompt_id = (
        persona_upsert_request.prompt_ids[0]
        if persona_upsert_request.prompt_ids
        and len(persona_upsert_request.prompt_ids) > 0
        else None
    )
    prompt = upsert_prompt(
        db_session=db_session,
        user=user,
        name=build_prompt_name_from_persona_name(persona_upsert_request.name),
        system_prompt=persona_upsert_request.system_prompt,
        task_prompt=persona_upsert_request.task_prompt,
        # TODO: The PersonaUpsertRequest should provide the value for datetime_aware
        datetime_aware=False,
        include_citations=persona_upsert_request.include_citations,
        prompt_id=prompt_id,
    )
    prompt_snapshot = PromptSnapshot.from_model(prompt)
    persona_upsert_request.prompt_ids = [prompt.id]
    persona_snapshot = create_update_persona(
        persona_id=None,
        create_persona_request=persona_upsert_request,
        user=user,
        db_session=db_session,
    )
    persona_snapshot.prompts = [prompt_snapshot]
    create_milestone_and_report(
        user=user,
        distinct_id=tenant_id or "N/A",
        event_type=MilestoneRecordType.CREATED_ASSISTANT,
        properties=None,
        db_session=db_session,
    )

    return persona_snapshot


# NOTE: This endpoint cannot update persona configuration options that
# are core to the persona, such as its display priority and
# whether or not the assistant is a built-in / default assistant
@basic_router.patch("/{persona_id}")
def update_persona(
    persona_id: int,
    persona_upsert_request: PersonaUpsertRequest,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> PersonaSnapshot:
    prompt_id = (
        persona_upsert_request.prompt_ids[0]
        if persona_upsert_request.prompt_ids
        and len(persona_upsert_request.prompt_ids) > 0
        else None
    )
    prompt = upsert_prompt(
        db_session=db_session,
        user=user,
        name=build_prompt_name_from_persona_name(persona_upsert_request.name),
        # TODO: The PersonaUpsertRequest should provide the value for datetime_aware
        datetime_aware=False,
        system_prompt=persona_upsert_request.system_prompt,
        task_prompt=persona_upsert_request.task_prompt,
        include_citations=persona_upsert_request.include_citations,
        prompt_id=prompt_id,
    )
    prompt_snapshot = PromptSnapshot.from_model(prompt)
    persona_upsert_request.prompt_ids = [prompt.id]
    persona_snapshot = create_update_persona(
        persona_id=persona_id,
        create_persona_request=persona_upsert_request,
        user=user,
        db_session=db_session,
    )
    persona_snapshot.prompts = [prompt_snapshot]
    return persona_snapshot


class PersonaLabelPatchRequest(BaseModel):
    label_name: str


@basic_router.get("/labels")
def get_labels(
    db: Session = Depends(get_session),
    _: User | None = Depends(current_user),
) -> list[PersonaLabelResponse]:
    return [
        PersonaLabelResponse.from_model(label)
        for label in get_assistant_labels(db_session=db)
    ]


@basic_router.post("/labels")
def create_label(
    label: PersonaLabelCreate,
    db: Session = Depends(get_session),
    _: User | None = Depends(current_user),
) -> PersonaLabelResponse:
    """Create a new assistant label"""
    try:
        label_model = create_assistant_label(name=label.name, db_session=db)
        return PersonaLabelResponse.from_model(label_model)
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail=f"Label with name '{label.name}' already exists. Please choose a different name.",
        )


@admin_router.patch("/label/{label_id}")
def patch_persona_label(
    label_id: int,
    persona_label_patch_request: PersonaLabelPatchRequest,
    _: User | None = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    update_persona_label(
        label_id=label_id,
        label_name=persona_label_patch_request.label_name,
        db_session=db_session,
    )


@admin_router.delete("/label/{label_id}")
def delete_label(
    label_id: int,
    _: User | None = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    delete_persona_label(label_id=label_id, db_session=db_session)


class PersonaShareRequest(BaseModel):
    user_ids: list[UUID]


# We notify each user when a user is shared with them
@basic_router.patch("/{persona_id}/share")
def share_persona(
    persona_id: int,
    persona_share_request: PersonaShareRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    update_persona_shared_users(
        persona_id=persona_id,
        user_ids=persona_share_request.user_ids,
        user=user,
        db_session=db_session,
    )

    for user_id in persona_share_request.user_ids:
        # Don't notify the user that they have access to their own persona
        if user_id != user.id:
            create_notification(
                user_id=user_id,
                notif_type=NotificationType.PERSONA_SHARED,
                db_session=db_session,
                additional_data=PersonaSharedNotificationData(
                    persona_id=persona_id,
                ).model_dump(),
            )


@basic_router.delete("/{persona_id}")
def delete_persona(
    persona_id: int,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> None:
    mark_persona_as_deleted(
        persona_id=persona_id,
        user=user,
        db_session=db_session,
    )


@basic_router.get("/image-generation-tool")
def get_image_generation_tool(
    _: User
    | None = Depends(current_user),  # User param not used but kept for consistency
    db_session: Session = Depends(get_session),
) -> ImageGenerationToolStatus:  # Use bool instead of str for boolean values
    is_available = is_image_generation_available(db_session=db_session)
    return ImageGenerationToolStatus(is_available=is_available)


@basic_router.get("")
def list_personas(
    user: User | None = Depends(current_chat_accesssible_user),
    db_session: Session = Depends(get_session),
    include_deleted: bool = False,
    persona_ids: list[int] = Query(None),
) -> list[PersonaSnapshot]:
    personas = get_personas_for_user(
        user=user,
        include_deleted=include_deleted,
        db_session=db_session,
        get_editable=False,
        joinedload_all=True,
    )

    if persona_ids:
        personas = [p for p in personas if p.id in persona_ids]

    # Filter out personas with unavailable tools
    personas = [
        p
        for p in personas
        if not (
            any(tool.in_code_tool_id == "ImageGenerationTool" for tool in p.tools)
            and not is_image_generation_available(db_session=db_session)
        )
    ]

    return [PersonaSnapshot.from_model(p) for p in personas]


@basic_router.get("/{persona_id}")
def get_persona(
    persona_id: int,
    user: User | None = Depends(current_limited_user),
    db_session: Session = Depends(get_session),
) -> PersonaSnapshot:
    return PersonaSnapshot.from_model(
        get_persona_by_id(
            persona_id=persona_id,
            user=user,
            db_session=db_session,
            is_for_edit=False,
        )
    )


@basic_router.post("/assistant-prompt-refresh")
def build_assistant_prompts(
    generate_persona_prompt_request: GenerateStarterMessageRequest,
    db_session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
) -> list[StarterMessage]:
    try:
        logger.info(
            f"Generating {generate_persona_prompt_request.generation_count} starter messages"
            f" for user: {user.id if user else 'Anonymous'}",
        )
        starter_messages = generate_starter_messages(
            name=generate_persona_prompt_request.name,
            description=generate_persona_prompt_request.description,
            instructions=generate_persona_prompt_request.instructions,
            document_set_ids=generate_persona_prompt_request.document_set_ids,
            generation_count=generate_persona_prompt_request.generation_count,
            db_session=db_session,
            user=user,
        )
        return starter_messages
    except Exception as e:
        logger.exception("Failed to generate starter messages")
        raise HTTPException(status_code=500, detail=str(e))
