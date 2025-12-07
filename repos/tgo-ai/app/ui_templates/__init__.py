"""
UI Templates module for structured data rendering.

This module provides a system for defining and rendering rich UI components
in markdown format that can be parsed and rendered by frontend clients.

Usage:
    # Generate catalog for system prompt
    from app.ui_templates import generate_template_catalog
    catalog = generate_template_catalog()

    # Get template detail for LLM
    from app.ui_templates.tools import get_ui_template
    detail = get_ui_template("order")

    # Render data as UI widget
    from app.ui_templates.tools import render_ui
    markdown = render_ui("order", {"order_id": "...", ...})
"""

from app.ui_templates.schema import (
    UITemplate,
    UITemplateType,
    MoneyAmount,
    ImageInfo,
    ActionButton,
    ActionProtocol,
    ButtonStyle,
)
from app.ui_templates.action import (
    ParsedAction,
    parse_action_uri,
    build_action_uri,
    is_valid_action_uri,
    get_protocol,
    url_action,
    msg_action,
    copy_action,
)
from app.ui_templates.registry import UITemplateRegistry
from app.ui_templates.prompt_builder import (
    generate_template_catalog,
    generate_template_detail,
    generate_usage_instructions,
    generate_action_uri_spec,
    generate_action_examples,
)
from app.ui_templates.tools import (
    get_ui_template,
    render_ui,
    list_ui_templates,
    validate_ui_data,
    execute_ui_tool,
    UI_TEMPLATE_TOOLS,
    UI_TEMPLATE_TOOL_FUNCTIONS,
)
from app.ui_templates.parser import (
    StreamingUIBlockParser,
    UIBlock,
    UIBlockState,
    ParseResult,
    parse_ui_blocks,
    extract_ui_blocks_for_rendering,
)

__all__ = [
    # Schema classes
    "UITemplate",
    "UITemplateType",
    "MoneyAmount",
    "ImageInfo",
    "ActionButton",
    "ActionProtocol",
    "ButtonStyle",
    # Registry
    "UITemplateRegistry",
    # Prompt builder
    "generate_template_catalog",
    "generate_template_detail",
    "generate_usage_instructions",
    "generate_action_uri_spec",
    "generate_action_examples",
    # Tools
    "get_ui_template",
    "render_ui",
    "list_ui_templates",
    "validate_ui_data",
    "execute_ui_tool",
    "UI_TEMPLATE_TOOLS",
    "UI_TEMPLATE_TOOL_FUNCTIONS",
    # Parser
    "StreamingUIBlockParser",
    "UIBlock",
    "UIBlockState",
    "ParseResult",
    "parse_ui_blocks",
    "extract_ui_blocks_for_rendering",
    # Action URI utilities
    "ParsedAction",
    "parse_action_uri",
    "build_action_uri",
    "is_valid_action_uri",
    "get_protocol",
    "url_action",
    "msg_action",
    "copy_action",
]
