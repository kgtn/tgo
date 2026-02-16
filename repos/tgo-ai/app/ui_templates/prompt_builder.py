"""
Prompt Builder for UI Templates.

This module provides functions to generate lightweight template catalogs
and documentation for use in LLM system prompts.
"""

import json
from typing import List, Optional

from app.ui_templates.registry import UITemplateRegistry


# Action URI 规范说明（用于 LLM）
ACTION_URI_SPEC_ZH = """### Action URI 规范

操作按钮的 `action` 字段使用 URI 格式: `{协议}://{内容}`

**支持的协议:**

| 协议 | 用途 | 示例 |
|------|------|------|
| `url://` | 打开外部链接 | `url://https://example.com/product/123` |
| `msg://` | 发送消息到聊天 | `msg://帮我查询这个订单的物流信息` |
| `copy://` | 复制到剪贴板 | `copy://SF1234567890` |

**按钮字段说明:**
- `label`: 按钮显示文本（必填）
- `action`: Action URI（必填）
- `style`: 样式，可选值: default/primary/danger/link/ghost

**示例:**
```json
[
  {"label": "查看详情", "action": "url://https://example.com/order/123", "style": "primary"},
  {"label": "咨询客服", "action": "msg://帮我查询订单ORD-001的状态", "style": "default"},
  {"label": "复制单号", "action": "copy://SF1234567890", "style": "link"}
]
```
"""

ACTION_URI_SPEC_EN = """### Action URI Specification

The `action` field in buttons uses URI format: `{protocol}://{content}`

**Supported protocols:**

| Protocol | Purpose | Example |
|----------|---------|---------|
| `url://` | Open external link | `url://https://example.com/product/123` |
| `msg://` | Send message to chat | `msg://Help me check this order` |
| `copy://` | Copy to clipboard | `copy://SF1234567890` |

**Button fields:**
- `label`: Button display text (required)
- `action`: Action URI (required)
- `style`: Style, options: default/primary/danger/link/ghost

**Example:**
```json
[
  {"label": "View Details", "action": "url://https://example.com/order/123", "style": "primary"},
  {"label": "Contact Support", "action": "msg://Help me check order ORD-001", "style": "default"},
  {"label": "Copy Tracking #", "action": "copy://SF1234567890", "style": "link"}
]
```
"""


def generate_template_catalog(
    include_types: Optional[List[str]] = None,
    language: str = "en",
) -> str:
    """
    Generate a lightweight template catalog for system prompt injection.

    This generates a concise list of available templates with one-line
    descriptions, keeping token usage minimal (~200 tokens).

    Args:
        include_types: Optional list of template types to include.
                      If None, includes all registered templates.
        language: Language for descriptions ("zh" for Chinese, "en" for English).

    Returns:
        Formatted catalog string suitable for system prompt.
    """
    templates = UITemplateRegistry.get_all_templates()

    if include_types:
        templates = {k: v for k, v in templates.items() if k in include_types}

    if not templates:
        return ""

    if language == "zh":
        header = """## 可用的富文本 UI 模板

当需要展示结构化数据（订单、产品、物流等）时，请先调用 `get_ui_template` 工具获取模板格式，然后按格式输出数据。

可用模板:"""
    else:
        header = """## Available Rich UI Templates

When you need to display structured data (orders, products, logistics, etc.),
first call the `get_ui_template` tool to get the template format, then output data in that format.

Available templates:"""

    lines = [header]

    for template_type, template_cls in templates.items():
        description = template_cls.get_description()
        lines.append(f"- {template_type}: {description}")

    return "\n".join(lines)


def generate_template_detail(template_type: str) -> str:
    """
    Generate detailed documentation for a specific template.

    This is called by the get_ui_template tool to provide the LLM
    with full schema and example when needed.

    Args:
        template_type: The type identifier (e.g., "order", "product").

    Returns:
        Formatted documentation string with schema and example.
    """
    template_cls = UITemplateRegistry.get_template(template_type)

    if template_cls is None:
        return f"错误：未找到模板 '{template_type}'。可用模板: {', '.join(UITemplateRegistry.list_template_types())}"

    # Get schema (simplified for LLM consumption)
    schema = template_cls.model_json_schema()
    description = template_cls.get_description()

    # Get example
    try:
        example = template_cls.get_example()
    except NotImplementedError:
        example = None

    # Build response
    lines = [
        f"## {template_type} 模板",
        "",
        f"**描述**: {description}",
        "",
        "### 数据格式",
        "",
        "使用以下格式输出：",
        "",
        "```tgo-ui-widget",
        json.dumps({"type": template_type, "...": "其他字段"}, ensure_ascii=False),
        "```",
        "",
        "### 字段说明",
        "",
    ]

    # Extract field descriptions from schema
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    for field_name, field_info in properties.items():
        field_type = field_info.get("type", "any")
        field_desc = field_info.get("description", "")
        is_required = "必填" if field_name in required else "可选"
        lines.append(f"- `{field_name}` ({field_type}, {is_required}): {field_desc}")

    if example:
        lines.extend([
            "",
            "### 完整示例",
            "",
            "```tgo-ui-widget",
            json.dumps(example, indent=2, ensure_ascii=False),
            "```",
        ])

    # Check if template has actions field and add Action URI spec
    if "actions" in properties:
        lines.extend([
            "",
            ACTION_URI_SPEC_ZH,
        ])

    return "\n".join(lines)


def generate_usage_instructions(language: str = "zh") -> str:
    """
    Generate usage instructions for UI templates.

    This provides the LLM with guidance on when and how to use UI templates.

    Args:
        language: Language for instructions.

    Returns:
        Usage instructions string.
    """
    if language == "zh":
        return """### UI 模板使用指南

1. **何时使用**: 当用户询问订单、产品、物流等结构化数据时，使用 UI 模板可以提供更好的展示效果。

2. **如何使用**:
   - 首先调用 `get_ui_template(template_name)` 获取模板格式
   - 从业务系统获取数据后，按模板格式组织数据
   - 使用 `render_ui(template_name, data)` 或直接输出格式化的代码块

3. **输出格式**:
```tgo-ui-widget
{
  "type": "模板类型",
  "字段1": "值1",
  "字段2": "值2"
}
```

4. **注意事项**:
   - 确保 `type` 字段与模板类型匹配
   - 必填字段不能为空
   - 保持数据格式正确（如价格为数字，不是字符串）
"""
    else:
        return """### UI Template Usage Guide

1. **When to use**: Use UI templates when users ask about structured data like orders, products, or logistics for better presentation.

2. **How to use**:
   - First call `get_ui_template(template_name)` to get the template format
   - After getting data from business systems, organize it according to the template
   - Use `render_ui(template_name, data)` or output the formatted code block directly

3. **Output format**:
```tgo-ui-widget
{
  "type": "template_type",
  "field1": "value1",
  "field2": "value2"
}
```

4. **Notes**:
   - Ensure the `type` field matches the template type
   - Required fields cannot be empty
   - Keep data formats correct (e.g., prices as numbers, not strings)
"""


def generate_action_uri_spec(language: str = "zh") -> str:
    """
    Generate Action URI specification for LLM.

    This provides the LLM with guidance on how to format action buttons
    in UI templates.

    Args:
        language: Language for the specification ("zh" or "en").

    Returns:
        Action URI specification string.
    """
    if language == "zh":
        return ACTION_URI_SPEC_ZH
    else:
        return ACTION_URI_SPEC_EN


def generate_action_examples(language: str = "zh") -> str:
    """
    Generate common action examples for LLM reference.

    Args:
        language: Language for examples.

    Returns:
        Action examples string.
    """
    if language == "zh":
        return """### 常用 Action 示例

**打开链接 (url://):**
```json
{"label": "查看详情", "action": "url://https://example.com/product/123", "style": "primary"}
{"label": "去购买", "action": "url://https://item.jd.com/123.html", "style": "link"}
```

**发送消息 (msg://):**
```json
{"label": "咨询客服", "action": "msg://我想了解这个商品的更多信息", "style": "default"}
{"label": "查询物流", "action": "msg://帮我查询订单ORD-001的物流状态", "style": "link"}
```

**复制内容 (copy://):**
```json
{"label": "复制单号", "action": "copy://SF1234567890", "style": "link"}
{"label": "复制订单号", "action": "copy://ORD-2024-001234", "style": "ghost"}
```
"""
    else:
        return """### Common Action Examples

**Open Link (url://):**
```json
{"label": "View Details", "action": "url://https://example.com/product/123", "style": "primary"}
{"label": "Buy Now", "action": "url://https://item.jd.com/123.html", "style": "link"}
```

**Send Message (msg://):**
```json
{"label": "Contact Support", "action": "msg://I want to know more about this product", "style": "default"}
{"label": "Track Order", "action": "msg://Help me check the logistics of order ORD-001", "style": "link"}
```

**Copy Content (copy://):**
```json
{"label": "Copy Tracking #", "action": "copy://SF1234567890", "style": "link"}
{"label": "Copy Order ID", "action": "copy://ORD-2024-001234", "style": "ghost"}
```
"""
