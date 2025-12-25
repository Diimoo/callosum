from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from sqlalchemy.orm import Session

from callosum.auth.users import current_curator_or_admin_user
from callosum.auth.users import current_user
from callosum.background.celery.versioned_apps.client import app as client_app
from callosum.configs.constants import CallosumCeleryPriority
from callosum.configs.constants import CallosumCeleryTask
from callosum.db.document_set import check_document_sets_are_public
from callosum.db.document_set import fetch_all_document_sets_for_user
from callosum.db.document_set import get_document_set_by_id
from callosum.db.document_set import insert_document_set
from callosum.db.document_set import mark_document_set_as_to_be_deleted
from callosum.db.document_set import update_document_set
from callosum.db.engine.sql_engine import get_session
from callosum.db.models import User
from callosum.server.features.document_set.models import CheckDocSetPublicRequest
from callosum.server.features.document_set.models import CheckDocSetPublicResponse
from callosum.server.features.document_set.models import DocumentSetCreationRequest
from callosum.server.features.document_set.models import DocumentSetSummary
from callosum.server.features.document_set.models import DocumentSetUpdateRequest
from callosum.utils.variable_functionality import fetch_ee_implementation_or_noop
from shared_configs.contextvars import get_current_tenant_id


router = APIRouter(prefix="/manage")


@router.post("/admin/document-set")
def create_document_set(
    document_set_creation_request: DocumentSetCreationRequest,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
    tenant_id: str = Depends(get_current_tenant_id),
) -> int:
    fetch_ee_implementation_or_noop(
        "callosum.db.user_group", "validate_object_creation_for_user", None
    )(
        db_session=db_session,
        user=user,
        target_group_ids=document_set_creation_request.groups,
        object_is_public=document_set_creation_request.is_public,
        object_is_new=True,
    )
    try:
        document_set_db_model, _ = insert_document_set(
            document_set_creation_request=document_set_creation_request,
            user_id=user.id if user else None,
            db_session=db_session,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    client_app.send_task(
        CallosumCeleryTask.CHECK_FOR_VESPA_SYNC_TASK,
        kwargs={"tenant_id": tenant_id},
        priority=CallosumCeleryPriority.HIGH,
    )

    return document_set_db_model.id


@router.patch("/admin/document-set")
def patch_document_set(
    document_set_update_request: DocumentSetUpdateRequest,
    user: User | None = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
    tenant_id: str = Depends(get_current_tenant_id),
) -> None:
    document_set = get_document_set_by_id(db_session, document_set_update_request.id)
    if document_set is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document set {document_set_update_request.id} does not exist",
        )

    fetch_ee_implementation_or_noop(
        "callosum.db.user_group", "validate_object_creation_for_user", None
    )(
        db_session=db_session,
        user=user,
        target_group_ids=document_set_update_request.groups,
        object_is_public=document_set_update_request.is_public,
        object_is_owned_by_user=user and document_set.user_id == user.id,
    )
    try:
        update_document_set(
            document_set_update_request=document_set_update_request,
            db_session=db_session,
            user=user,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    client_app.send_task(
        CallosumCeleryTask.CHECK_FOR_VESPA_SYNC_TASK,
        kwargs={"tenant_id": tenant_id},
        priority=CallosumCeleryPriority.HIGH,
    )


@router.delete("/admin/document-set/{document_set_id}")
def delete_document_set(
    document_set_id: int,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
    tenant_id: str = Depends(get_current_tenant_id),
) -> None:
    document_set = get_document_set_by_id(db_session, document_set_id)
    if document_set is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document set {document_set_id} does not exist",
        )

    # check if the user has "edit" access to the document set.
    # `validate_object_creation_for_user` is poorly named, but this
    # is the right function to use here
    fetch_ee_implementation_or_noop(
        "callosum.db.user_group", "validate_object_creation_for_user", None
    )(
        db_session=db_session,
        user=user,
        object_is_public=document_set.is_public,
        object_is_owned_by_user=user and document_set.user_id == user.id,
    )

    try:
        mark_document_set_as_to_be_deleted(
            db_session=db_session,
            document_set_id=document_set_id,
            user=user,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    client_app.send_task(
        CallosumCeleryTask.CHECK_FOR_VESPA_SYNC_TASK,
        kwargs={"tenant_id": tenant_id},
        priority=CallosumCeleryPriority.HIGH,
    )


"""Endpoints for non-admins"""


@router.get("/document-set")
def list_document_sets_for_user(
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
    get_editable: bool = Query(
        False, description="If true, return editable document sets"
    ),
) -> list[DocumentSetSummary]:
    document_sets = fetch_all_document_sets_for_user(
        db_session=db_session, user=user, get_editable=get_editable
    )
    return [DocumentSetSummary.from_model(ds) for ds in document_sets]


@router.get("/document-set-public")
def document_set_public(
    check_public_request: CheckDocSetPublicRequest,
    _: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> CheckDocSetPublicResponse:
    is_public = check_document_sets_are_public(
        document_set_ids=check_public_request.document_set_ids, db_session=db_session
    )
    return CheckDocSetPublicResponse(is_public=is_public)
