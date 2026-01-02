"""Workflow service proxy endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.common_responses import CREATE_RESPONSES, CRUD_RESPONSES, LIST_RESPONSES
from app.core.security import get_current_active_user
from app.models import Staff
from app.schemas.ai_workflows import (
    PaginatedWorkflowSummaryResponse,
    WorkflowCreate,
    WorkflowDuplicateRequest,
    WorkflowExecuteRequest,
    WorkflowExecution,
    WorkflowExecutionCancelResponse,
    WorkflowInDB,
    WorkflowUpdate,
    WorkflowValidationResponse,
    WorkflowValidateRequest,
    WorkflowVariablesResponse,
)
from app.services.workflow_client import workflow_client

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedWorkflowSummaryResponse,
    responses=LIST_RESPONSES,
    summary="List Workflows",
)
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    sort_by: str = Query("updated_at"),
    sort_order: str = Query("desc"),
    current_user: Staff = Depends(get_current_active_user),
) -> PaginatedWorkflowSummaryResponse:
    """List workflows from Workflow service."""
    data = await workflow_client.list_workflows(
        project_id=str(current_user.project_id),
        skip=skip,
        limit=limit,
        status=status,
        search=search,
        tags=tags,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PaginatedWorkflowSummaryResponse.model_validate(data)


@router.post(
    "",
    response_model=WorkflowInDB,
    responses=CREATE_RESPONSES,
    status_code=201,
    summary="Create Workflow",
)
async def create_workflow(
    workflow_data: WorkflowCreate,
    current_user: Staff = Depends(get_current_active_user),
) -> WorkflowInDB:
    """Create workflow in Workflow service."""
    data = await workflow_client.create_workflow(
        str(current_user.project_id), workflow_data.model_dump(by_alias=True)
    )
    return WorkflowInDB.model_validate(data)


@router.get(
    "/{workflow_id}",
    response_model=WorkflowInDB,
    responses=CRUD_RESPONSES,
    summary="Get Workflow",
)
async def get_workflow(
    workflow_id: str,
    current_user: Staff = Depends(get_current_active_user),
) -> WorkflowInDB:
    """Get workflow from Workflow service."""
    data = await workflow_client.get_workflow(workflow_id, str(current_user.project_id))
    return WorkflowInDB.model_validate(data)


@router.put(
    "/{workflow_id}",
    response_model=WorkflowInDB,
    responses=CRUD_RESPONSES,
    summary="Update Workflow",
)
async def update_workflow(
    workflow_id: str,
    workflow_data: WorkflowUpdate,
    current_user: Staff = Depends(get_current_active_user),
) -> WorkflowInDB:
    """Update workflow in Workflow service."""
    data = await workflow_client.update_workflow(
        workflow_id,
        str(current_user.project_id),
        workflow_data.model_dump(by_alias=True, exclude_none=True),
    )
    return WorkflowInDB.model_validate(data)


@router.delete(
    "/{workflow_id}",
    responses=CRUD_RESPONSES,
    status_code=204,
    summary="Delete Workflow",
)
async def delete_workflow(
    workflow_id: str,
    current_user: Staff = Depends(get_current_active_user),
) -> None:
    """Delete workflow from Workflow service."""
    await workflow_client.delete_workflow(workflow_id, str(current_user.project_id))


@router.post(
    "/{workflow_id}/duplicate",
    response_model=WorkflowInDB,
    responses=CRUD_RESPONSES,
    summary="Duplicate Workflow",
)
async def duplicate_workflow(
    workflow_id: str,
    request: Optional[WorkflowDuplicateRequest] = None,
    current_user: Staff = Depends(get_current_active_user),
) -> WorkflowInDB:
    """Duplicate workflow in Workflow service."""
    payload = request.model_dump(by_alias=True, exclude_none=True) if request else None
    data = await workflow_client.duplicate_workflow(
        workflow_id, str(current_user.project_id), payload
    )
    return WorkflowInDB.model_validate(data)


@router.post(
    "/validate",
    response_model=WorkflowValidationResponse,
    responses=CRUD_RESPONSES,
    summary="Validate Workflow Generic",
)
async def validate_workflow_generic(
    request: WorkflowValidateRequest,
    current_user: Staff = Depends(get_current_active_user),
) -> WorkflowValidationResponse:
    """Validate an arbitrary workflow graph (nodes/edges) in Workflow service."""
    data = await workflow_client.validate_workflow_generic(
        str(current_user.project_id), request.model_dump(by_alias=True)
    )
    return WorkflowValidationResponse.model_validate(data)


@router.post(
    "/{workflow_id}/validate",
    response_model=WorkflowValidationResponse,
    responses=CRUD_RESPONSES,
    summary="Validate Workflow",
)
async def validate_workflow(
    workflow_id: str,
    current_user: Staff = Depends(get_current_active_user),
) -> WorkflowValidationResponse:
    """Validate an existing workflow by id in Workflow service."""
    data = await workflow_client.validate_workflow(workflow_id, str(current_user.project_id))
    return WorkflowValidationResponse.model_validate(data)


@router.post(
    "/{workflow_id}/publish",
    response_model=WorkflowInDB,
    responses=CRUD_RESPONSES,
    summary="Publish Workflow",
)
async def publish_workflow(
    workflow_id: str,
    current_user: Staff = Depends(get_current_active_user),
) -> WorkflowInDB:
    """Publish a workflow in Workflow service."""
    data = await workflow_client.publish_workflow(workflow_id, str(current_user.project_id))
    return WorkflowInDB.model_validate(data)


@router.get(
    "/{workflow_id}/variables",
    response_model=WorkflowVariablesResponse,
    responses=CRUD_RESPONSES,
    summary="Get Workflow Variables",
)
async def get_workflow_variables(
    workflow_id: str,
    current_user: Staff = Depends(get_current_active_user),
) -> WorkflowVariablesResponse:
    """Get available variables for a workflow in Workflow service."""
    data = await workflow_client.get_workflow_variables(
        workflow_id, str(current_user.project_id)
    )
    return WorkflowVariablesResponse.model_validate(data)


@router.post(
    "/{workflow_id}/execute",
    response_model=WorkflowExecution,
    summary="Execute Workflow",
)
async def execute_workflow(
    workflow_id: str,
    request: WorkflowExecuteRequest,
    current_user: Staff = Depends(get_current_active_user),
) -> WorkflowExecution:
    """Execute workflow in Workflow service."""
    data = await workflow_client.execute_workflow(
        workflow_id, str(current_user.project_id), request.model_dump(by_alias=True)
    )
    return WorkflowExecution.model_validate(data)


@router.get(
    "/executions/{execution_id}",
    response_model=WorkflowExecution,
    summary="Get Execution Status",
)
async def get_execution(
    execution_id: str,
    current_user: Staff = Depends(get_current_active_user),
) -> WorkflowExecution:
    """Get execution status from Workflow service."""
    data = await workflow_client.get_execution(execution_id, str(current_user.project_id))
    return WorkflowExecution.model_validate(data)


@router.get(
    "/{workflow_id}/executions",
    response_model=List[WorkflowExecution],
    summary="List Workflow Executions",
)
async def list_workflow_executions(
    workflow_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Staff = Depends(get_current_active_user),
) -> List[WorkflowExecution]:
    """List workflow executions from Workflow service."""
    data = await workflow_client.list_workflow_executions(
        workflow_id, str(current_user.project_id), skip=skip, limit=limit
    )
    return [WorkflowExecution.model_validate(item) for item in data]


@router.post(
    "/executions/{execution_id}/cancel",
    response_model=WorkflowExecutionCancelResponse,
    responses=CRUD_RESPONSES,
    summary="Cancel Execution",
)
async def cancel_execution(
    execution_id: str,
    current_user: Staff = Depends(get_current_active_user),
) -> WorkflowExecutionCancelResponse:
    """Cancel a workflow execution in Workflow service."""
    data = await workflow_client.cancel_execution(execution_id, str(current_user.project_id))
    return WorkflowExecutionCancelResponse.model_validate(data)

