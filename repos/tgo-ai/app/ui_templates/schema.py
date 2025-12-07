"""
UI Template Schema definitions.

This module defines the base schema and common types for UI templates.
All UI widgets use the unified code block language `tgo-ui-widget` with
a `type` field in the JSON to distinguish different UI components.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UITemplateType(str, Enum):
    """Enumeration of available UI template types."""

    ORDER = "order"
    PRODUCT = "product"
    PRODUCT_LIST = "product_list"
    LOGISTICS = "logistics"
    PRICE_COMPARISON = "price_comparison"


class UITemplate(BaseModel):
    """
    Base class for all UI templates.

    All UI templates must inherit from this class and define their
    specific fields. The `type` field is used by the frontend to
    determine which component to render.
    """

    type: UITemplateType = Field(
        ...,
        description="UI template type, used by frontend to route to correct renderer",
    )
    version: str = Field(
        default="1.0",
        description="Template version for backward compatibility",
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True

    @classmethod
    def get_example(cls) -> Dict[str, Any]:
        """
        Get an example instance of this template.
        Subclasses should override this method to provide meaningful examples.
        """
        raise NotImplementedError("Subclasses must implement get_example()")

    @classmethod
    def get_description(cls) -> str:
        """
        Get a short description of this template.
        Subclasses should override this method.
        """
        return cls.__doc__ or "No description available"

    def to_markdown(self) -> str:
        """
        Render this template as a tgo-ui-widget markdown code block.

        Returns:
            Formatted markdown string with tgo-ui-widget code block.
        """
        return f"```tgo-ui-widget\n{self.model_dump_json(indent=2)}\n```"


# Common sub-schemas used across multiple templates


class MoneyAmount(BaseModel):
    """Represents a monetary amount with currency."""

    amount: float = Field(..., description="Numeric amount")
    currency: str = Field(default="CNY", description="Currency code (e.g., CNY, USD)")

    def __str__(self) -> str:
        symbols = {"CNY": "¥", "USD": "$", "EUR": "€", "GBP": "£"}
        symbol = symbols.get(self.currency, self.currency)
        return f"{symbol}{self.amount:.2f}"


class ImageInfo(BaseModel):
    """Image information for display."""

    url: str = Field(..., description="Image URL")
    alt: Optional[str] = Field(default=None, description="Alternative text")
    width: Optional[int] = Field(default=None, description="Image width in pixels")
    height: Optional[int] = Field(default=None, description="Image height in pixels")


class ActionProtocol(str, Enum):
    """
    Action URI 协议类型。

    用于定义前端如何处理按钮点击操作。
    格式: {protocol}://{path}
    """

    URL = "url"  # 外部链接跳转: url://https://example.com
    MSG = "msg"  # 发送消息到聊天: msg://查看订单ORD-001的物流
    COPY = "copy"  # 复制到剪贴板: copy://SF1234567890


class ButtonStyle(str, Enum):
    """按钮样式类型。"""

    DEFAULT = "default"  # 默认样式
    PRIMARY = "primary"  # 主要操作
    DANGER = "danger"  # 危险操作
    LINK = "link"  # 链接样式
    GHOST = "ghost"  # 幽灵按钮


class ActionButton(BaseModel):
    """
    Action button definition for interactive UI elements.

    Action URI 格式: {protocol}://{content}

    支持的协议:
    - url://   打开外部链接，如 url://https://example.com
    - msg://   发送消息到聊天，如 msg://帮我查询这个订单
    - copy://  复制到剪贴板，如 copy://SF1234567890
    """

    label: str = Field(..., description="按钮显示文本")
    action: str = Field(
        ...,
        description="Action URI，格式: {protocol}://{content}",
        examples=[
            "url://https://example.com/product/123",
            "msg://帮我查询这个订单的物流信息",
            "copy://SF1234567890",
        ],
    )
    style: str = Field(
        default="default",
        description="按钮样式: default, primary, danger, link, ghost",
    )
