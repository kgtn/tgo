"""Plugin API endpoints."""

from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.services.plugin_manager import plugin_manager
from app.models.visitor import Visitor # Import Visitor model
from app.schemas.plugin import (
    VisitorInfo,
    PluginListResponse,
    PluginInfo,
    PluginRenderRequest,
    PluginEventRequest,
    VisitorPanelRenderRequest,
    VisitorPanelRenderResponse,
    ChatToolbarResponse,
    PluginRenderResponse,
    PluginActionResponse,
)

logger = get_logger("api.plugins")
router = APIRouter()


def _get_visitor_info(db_visitor: Visitor, language: Optional[str] = None) -> VisitorInfo:
    """Helper to create VisitorInfo with prioritized name logic."""
    name = db_visitor.name
    if not name:
        is_zh = language and language.lower().startswith("zh")
        if is_zh and db_visitor.nickname_zh:
            name = db_visitor.nickname_zh
        else:
            name = db_visitor.nickname or f"Visitor {str(db_visitor.id)[:4]}"

    return VisitorInfo(
        id=str(db_visitor.id),
        platform_open_id=db_visitor.platform_open_id,
        name=name,
        email=db_visitor.email,
        phone=db_visitor.phone_number,
        avatar=db_visitor.avatar_url,
        metadata=db_visitor.custom_attributes or {}
    )


@router.get("", response_model=PluginListResponse)
async def list_plugins() -> PluginListResponse:
    """
    Get all registered plugins.
    
    Returns a list of all currently connected plugins with their capabilities.
    """
    plugins = plugin_manager.get_all_plugins()
    return PluginListResponse(plugins=plugins, total=len(plugins))


@router.get("/chat-toolbar/buttons", response_model=ChatToolbarResponse)
async def get_chat_toolbar_buttons() -> ChatToolbarResponse:
    """
    Get all chat toolbar buttons from registered plugins.
    
    Returns a list of buttons that should be displayed in the chat toolbar.
    """
    buttons = plugin_manager.get_chat_toolbar_buttons()
    return ChatToolbarResponse(buttons=buttons)


@router.post("/visitor-panel/render", response_model=VisitorPanelRenderResponse)
async def render_visitor_panels(
    request: VisitorPanelRenderRequest,
    db: Session = Depends(get_db)
) -> VisitorPanelRenderResponse:
    """
    Render all visitor panel plugins for a specific visitor.
    
    Returns a list of rendered panels from all plugins that support visitor_panel.
    """
    visitor_info = request.visitor
    
    # If visitor info not provided, fetch from database
    if not visitor_info and request.visitor_id:
        try:
            db_visitor = db.query(Visitor).filter(Visitor.id == request.visitor_id).first()
            if db_visitor:
                visitor_info = _get_visitor_info(db_visitor, request.language)
        except Exception as e:
            logger.warning(f"Failed to fetch visitor info for plugin render: {e}")

    panels = await plugin_manager.render_visitor_panels(
        visitor_id=request.visitor_id,
        session_id=request.session_id,
        visitor=visitor_info,
        context=request.context,
        language=request.language,
    )
    return VisitorPanelRenderResponse(panels=panels)


@router.post("/chat-toolbar/{plugin_id}/render", response_model=PluginRenderResponse)
async def render_chat_toolbar_plugin(
    plugin_id: str,
    request: PluginRenderRequest,
    db: Session = Depends(get_db)
) -> PluginRenderResponse:
    """
    Render a chat toolbar plugin's content.
    
    Called when user clicks a toolbar button.
    """
    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin not found: {plugin_id}"
        )
    
    visitor_info = request.visitor
    # If visitor info not provided, fetch from database
    if not visitor_info and request.visitor_id:
        try:
            db_visitor = db.query(Visitor).filter(Visitor.id == request.visitor_id).first()
            if db_visitor:
                visitor_info = _get_visitor_info(db_visitor, request.language)
        except Exception as e:
            logger.warning(f"Failed to fetch visitor info for plugin render: {e}")

    print("visitor_info--->",visitor_info)
    params = {
        "action_id": request.action_id,
        "visitor_id": request.visitor_id,
        "session_id": request.session_id,
        "visitor": visitor_info.model_dump(exclude_none=True) if visitor_info else None,
        "agent_id": request.agent_id,
        "context": request.context,
        "language": request.language,
    }
    
    result = await plugin_manager.send_request(plugin_id, "chat_toolbar/render", params)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Plugin did not respond in time"
        )
    
    return PluginRenderResponse(**result)


@router.post("/chat-toolbar/{plugin_id}/event", response_model=PluginActionResponse)
async def send_chat_toolbar_event(
    plugin_id: str,
    request: PluginEventRequest
) -> PluginActionResponse:
    """
    Send an event to a chat toolbar plugin.
    
    Called when user interacts with the toolbar plugin's UI.
    """
    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin not found: {plugin_id}"
        )
    
    params = {
        "event_type": request.event_type,
        "action_id": request.action_id,
        "visitor_id": request.visitor_id,
        "session_id": request.session_id,
        "selected_id": request.selected_id,
        "language": request.language,
        "form_data": request.form_data,
        "payload": request.payload,
    }
    
    result = await plugin_manager.send_request(plugin_id, "chat_toolbar/event", params)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Plugin did not respond in time"
        )
    
    return PluginActionResponse(**result)


@router.get("/{plugin_id}", response_model=PluginInfo)
async def get_plugin(plugin_id: str) -> PluginInfo:
    """
    Get a specific plugin by ID.
    """
    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin not found: {plugin_id}"
        )
    return plugin.to_info()


@router.post("/{plugin_id}/render", response_model=PluginRenderResponse)
async def render_plugin(
    plugin_id: str, 
    request: PluginRenderRequest,
    db: Session = Depends(get_db)
) -> PluginRenderResponse:
    """
    Trigger a plugin to render its UI.
    
    Sends a render request to the plugin and returns the JSON-UI response.
    """
    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin not found: {plugin_id}"
        )
    
    visitor_info = request.visitor
    # If visitor info not provided, fetch from database
    if not visitor_info and request.visitor_id:
        try:
            db_visitor = db.query(Visitor).filter(Visitor.id == request.visitor_id).first()
            if db_visitor:
                visitor_info = _get_visitor_info(db_visitor, request.language)
        except Exception as e:
            logger.warning(f"Failed to fetch visitor info for plugin render: {e}")

    # Determine the render method based on plugin capabilities
    method = "visitor_panel/render"
    for cap in plugin.capabilities:
        if cap.type == "chat_toolbar":
            method = "chat_toolbar/render"
            break
    
    params = {
        "visitor_id": request.visitor_id,
        "session_id": request.session_id,
        "visitor": visitor_info.model_dump(exclude_none=True) if visitor_info else None,
        "agent_id": request.agent_id,
        "action_id": request.action_id,
        "context": request.context,
        "language": request.language,
    }
    
    result = await plugin_manager.send_request(plugin_id, method, params)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Plugin did not respond in time"
        )
    
    return PluginRenderResponse(**result)


@router.post("/{plugin_id}/event", response_model=PluginActionResponse)
async def send_plugin_event(plugin_id: str, request: PluginEventRequest) -> PluginActionResponse:
    """
    Send an event to a plugin.
    
    Used when user interacts with plugin UI (button click, form submit, etc.).
    Returns the JSON-ACTION response.
    """
    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin not found: {plugin_id}"
        )
    
    # Determine the event method based on plugin capabilities or explicit extension_type
    method = None
    if request.extension_type:
        method = f"{request.extension_type}/event"
    else:
        # Fallback to guessing (backward compatibility)
        method = "visitor_panel/event"
        for cap in plugin.capabilities:
            if cap.type == "chat_toolbar":
                method = "chat_toolbar/event"
                break
    
    params = {
        "event_type": request.event_type,
        "action_id": request.action_id,
        "visitor_id": request.visitor_id,
        "session_id": request.session_id,
        "selected_id": request.selected_id,
        "language": request.language,
        "form_data": request.form_data,
        "payload": request.payload,
    }
    
    result = await plugin_manager.send_request(plugin_id, method, params)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Plugin did not respond in time"
        )
    
    return PluginActionResponse(**result)
