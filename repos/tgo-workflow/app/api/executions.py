from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.execution import WorkflowExecution, NodeExecution
from app.schemas.execution import (
    WorkflowExecution as WorkflowExecutionSchema, 
    WorkflowExecuteRequest,
    WorkflowExecutionCancelResponse
)
from celery_app.celery import celery_app
from datetime import datetime
from celery_app.tasks import execute_workflow_task
from typing import List
import uuid

router = APIRouter()

@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionSchema)
async def execute_workflow(
    workflow_id: str,
    request: WorkflowExecuteRequest,
    project_id: str = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db)
):
    # Verify workflow exists and belongs to project
    from app.models.workflow import Workflow
    wf_query = select(Workflow).where(Workflow.id == workflow_id, Workflow.project_id == project_id)
    wf_result = await db.execute(wf_query)
    if not wf_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Create execution record
    execution_id = str(uuid.uuid4())
    db_execution = WorkflowExecution(
        id=execution_id,
        project_id=project_id,
        workflow_id=workflow_id,
        status="pending",
        input=request.inputs
    )
    db.add(db_execution)
    await db.commit()
    await db.refresh(db_execution)
    db_execution.node_executions = [] # Avoid lazy loading error
    
    # Trigger Celery task
    # Pass project_id to the task as well
    execute_workflow_task.delay(execution_id, workflow_id, request.inputs, project_id=project_id)
    
    return db_execution

@router.get("/executions/{execution_id}", response_model=WorkflowExecutionSchema)
async def get_execution_status(
    execution_id: str,
    project_id: str = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(WorkflowExecution)
        .where(WorkflowExecution.id == execution_id, WorkflowExecution.project_id == project_id)
    )
    result = await db.execute(query)
    execution = result.scalar_one_or_none()
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    # Load node executions
    node_query = (
        select(NodeExecution)
        .where(NodeExecution.execution_id == execution_id, NodeExecution.project_id == project_id)
        .order_by(NodeExecution.started_at)
    )
    node_result = await db.execute(node_query)
    execution.node_executions = list(node_result.scalars().all())
    
    return execution

@router.get("/{workflow_id}/executions", response_model=List[WorkflowExecutionSchema])
async def get_workflow_executions(
    workflow_id: str,
    project_id: str = Query(..., description="Project ID"),
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(WorkflowExecution)
        .options(selectinload(WorkflowExecution.node_executions))
        .where(WorkflowExecution.workflow_id == workflow_id, WorkflowExecution.project_id == project_id)
        .order_by(desc(WorkflowExecution.started_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())

@router.post("/executions/{execution_id}/cancel", response_model=WorkflowExecutionCancelResponse)
async def cancel_execution(
    execution_id: str,
    project_id: str = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(WorkflowExecution)
        .where(WorkflowExecution.id == execution_id, WorkflowExecution.project_id == project_id)
    )
    result = await db.execute(query)
    execution = result.scalar_one_or_none()
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    if execution.status not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel execution in {execution.status} status")
        
    # Update status in DB
    execution.status = "cancelled"
    execution.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(execution)
    
    # Terminate Celery task if it's running
    celery_app.control.revoke(execution_id, terminate=True)
    
    return WorkflowExecutionCancelResponse(
        id=execution_id,
        status="cancelled",
        cancelled_at=execution.completed_at
    )

