"""
Order UI Template.

Defines the schema for rendering order information as a rich UI component.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.ui_templates.schema import (
    UITemplate,
    UITemplateType,
    ImageInfo,
    ActionButton,
)
from app.ui_templates.registry import UITemplateRegistry


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "pending"  # 待付款
    PAID = "paid"  # 已付款
    PROCESSING = "processing"  # 处理中
    SHIPPED = "shipped"  # 已发货
    DELIVERED = "delivered"  # 已送达
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消
    REFUNDED = "refunded"  # 已退款


class OrderItem(BaseModel):
    """Single item in an order."""

    name: str = Field(..., description="商品名称")
    sku: Optional[str] = Field(default=None, description="商品 SKU")
    quantity: int = Field(..., ge=1, description="数量")
    unit_price: float = Field(..., ge=0, description="单价")
    total_price: float = Field(..., ge=0, description="小计")
    image: Optional[ImageInfo] = Field(default=None, description="商品图片")
    attributes: Optional[Dict[str, str]] = Field(
        default=None,
        description="商品属性（如颜色、尺寸）",
    )


@UITemplateRegistry.register("order")
class OrderTemplate(UITemplate):
    """
    订单详情展示模板。

    用于展示完整的订单信息，包括订单状态、商品列表、
    收货地址、支付信息等。
    """

    type: Literal[UITemplateType.ORDER] = Field(
        default=UITemplateType.ORDER,
        description="模板类型",
    )

    # 订单基本信息
    order_id: str = Field(..., description="订单号")
    status: OrderStatus = Field(..., description="订单状态")
    status_text: Optional[str] = Field(default=None, description="状态描述文本")

    # 时间信息
    created_at: Optional[str] = Field(default=None, description="下单时间")
    paid_at: Optional[str] = Field(default=None, description="支付时间")
    shipped_at: Optional[str] = Field(default=None, description="发货时间")
    delivered_at: Optional[str] = Field(default=None, description="送达时间")

    # 商品信息
    items: List[OrderItem] = Field(..., description="订单商品列表")

    # 金额信息
    subtotal: float = Field(..., ge=0, description="商品小计")
    shipping_fee: float = Field(default=0, ge=0, description="运费")
    discount: float = Field(default=0, ge=0, description="优惠金额")
    total: float = Field(..., ge=0, description="订单总额")
    currency: str = Field(default="CNY", description="货币代码")

    # 收货信息
    shipping_address: Optional[str] = Field(default=None, description="收货地址")
    receiver_name: Optional[str] = Field(default=None, description="收货人姓名")
    receiver_phone: Optional[str] = Field(default=None, description="收货人电话")

    # 物流信息
    tracking_number: Optional[str] = Field(default=None, description="物流单号")
    carrier: Optional[str] = Field(default=None, description="物流公司")

    # 操作按钮
    actions: Optional[List[ActionButton]] = Field(
        default=None,
        description="可用操作按钮",
    )

    @classmethod
    def get_example(cls) -> Dict[str, Any]:
        """Get an example order template."""
        return {
            "type": "order",
            "order_id": "ORD-2024-001234",
            "status": "shipped",
            "status_text": "商品已发货，正在配送中",
            "created_at": "2024-12-01 10:30:00",
            "paid_at": "2024-12-01 10:35:00",
            "shipped_at": "2024-12-02 14:00:00",
            "items": [
                {
                    "name": "无线蓝牙耳机",
                    "sku": "BT-EARPHONE-001",
                    "quantity": 1,
                    "unit_price": 299.00,
                    "total_price": 299.00,
                    "attributes": {"颜色": "黑色"},
                },
                {
                    "name": "手机保护壳",
                    "sku": "CASE-IP15-002",
                    "quantity": 2,
                    "unit_price": 49.00,
                    "total_price": 98.00,
                    "attributes": {"款式": "透明"},
                },
            ],
            "subtotal": 397.00,
            "shipping_fee": 0,
            "discount": 20.00,
            "total": 377.00,
            "currency": "CNY",
            "shipping_address": "北京市朝阳区xxx街道xxx号",
            "receiver_name": "张三",
            "receiver_phone": "138****1234",
            "tracking_number": "SF1234567890",
            "carrier": "顺丰速运",
            "actions": [
                {
                    "label": "查看物流",
                    "action": "url://https://www.sf-express.com/cn/sc/dynamic_function/waybill/#search/bill-number/SF1234567890",
                    "style": "primary",
                },
                {
                    "label": "复制单号",
                    "action": "copy://SF1234567890",
                    "style": "link",
                },
                {
                    "label": "联系客服",
                    "action": "msg://我想咨询订单 ORD-2024-001234 的问题",
                    "style": "default",
                },
            ],
        }

    @classmethod
    def get_description(cls) -> str:
        """Get template description."""
        return "订单详情展示，包含订单状态、商品列表、金额、收货地址等完整信息"
