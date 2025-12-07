"""
Product UI Template.

Defines the schema for rendering product information as a rich UI component.
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


class ProductSpec(BaseModel):
    """Product specification item."""

    name: str = Field(..., description="规格名称")
    value: str = Field(..., description="规格值")


class ProductVariant(BaseModel):
    """Product variant (e.g., different colors or sizes)."""

    variant_id: str = Field(..., description="变体ID")
    name: str = Field(..., description="变体名称")
    price: float = Field(..., ge=0, description="价格")
    original_price: Optional[float] = Field(default=None, description="原价")
    stock: Optional[int] = Field(default=None, ge=0, description="库存")
    image: Optional[ImageInfo] = Field(default=None, description="变体图片")
    attributes: Optional[Dict[str, str]] = Field(
        default=None,
        description="变体属性",
    )


@UITemplateRegistry.register("product")
class ProductTemplate(UITemplate):
    """
    单个产品信息卡片模板。

    用于展示产品的详细信息，包括图片、价格、规格、
    库存状态等。适合在对话中推荐产品时使用。
    """

    type: Literal[UITemplateType.PRODUCT] = Field(
        default=UITemplateType.PRODUCT,
        description="模板类型",
    )

    # 产品基本信息
    product_id: str = Field(..., description="产品ID")
    name: str = Field(..., description="产品名称")
    description: Optional[str] = Field(default=None, description="产品描述")
    brand: Optional[str] = Field(default=None, description="品牌")
    category: Optional[str] = Field(default=None, description="分类")

    # 图片
    images: Optional[List[ImageInfo]] = Field(default=None, description="产品图片列表")
    thumbnail: Optional[ImageInfo] = Field(default=None, description="缩略图")

    # 价格信息
    price: float = Field(..., ge=0, description="当前价格")
    original_price: Optional[float] = Field(default=None, ge=0, description="原价")
    currency: str = Field(default="CNY", description="货币代码")
    discount_label: Optional[str] = Field(default=None, description="折扣标签")

    # 库存状态
    in_stock: bool = Field(default=True, description="是否有货")
    stock_quantity: Optional[int] = Field(default=None, ge=0, description="库存数量")
    stock_status: Optional[str] = Field(default=None, description="库存状态描述")

    # 规格参数
    specs: Optional[List[ProductSpec]] = Field(default=None, description="规格参数列表")

    # 变体（如颜色、尺寸）
    variants: Optional[List[ProductVariant]] = Field(
        default=None,
        description="产品变体列表",
    )

    # 评价信息
    rating: Optional[float] = Field(default=None, ge=0, le=5, description="评分")
    review_count: Optional[int] = Field(default=None, ge=0, description="评价数量")

    # 标签
    tags: Optional[List[str]] = Field(default=None, description="产品标签")

    # 操作按钮
    actions: Optional[List[ActionButton]] = Field(
        default=None,
        description="操作按钮",
    )

    # 链接
    url: Optional[str] = Field(default=None, description="产品详情页链接")

    @classmethod
    def get_example(cls) -> Dict[str, Any]:
        """Get an example product template."""
        return {
            "type": "product",
            "product_id": "PROD-001234",
            "name": "Apple iPhone 15 Pro Max 256GB",
            "description": "A17 Pro芯片，钛金属设计，4800万像素主摄",
            "brand": "Apple",
            "category": "手机",
            "thumbnail": {
                "url": "https://example.com/iphone15.jpg",
                "alt": "iPhone 15 Pro Max",
            },
            "price": 9999.00,
            "original_price": 10999.00,
            "currency": "CNY",
            "discount_label": "限时优惠",
            "in_stock": True,
            "stock_quantity": 50,
            "specs": [
                {"name": "屏幕尺寸", "value": "6.7英寸"},
                {"name": "存储容量", "value": "256GB"},
                {"name": "处理器", "value": "A17 Pro"},
            ],
            "rating": 4.8,
            "review_count": 2580,
            "tags": ["新品", "热销", "限时优惠"],
            "actions": [
                {
                    "label": "查看详情",
                    "action": "url://https://example.com/product/PROD-001234",
                    "style": "primary",
                },
                {
                    "label": "咨询客服",
                    "action": "msg://我想了解 iPhone 15 Pro Max 的更多信息",
                    "style": "default",
                },
                {
                    "label": "复制链接",
                    "action": "copy://https://example.com/product/PROD-001234",
                    "style": "link",
                },
            ],
            "url": "https://example.com/product/PROD-001234",
        }

    @classmethod
    def get_description(cls) -> str:
        """Get template description."""
        return "单个产品信息卡片，展示产品图片、价格、规格、库存等详细信息"


@UITemplateRegistry.register("product_list")
class ProductListTemplate(UITemplate):
    """
    产品列表展示模板。

    用于展示多个产品的列表，适合搜索结果、推荐列表等场景。
    """

    type: Literal[UITemplateType.PRODUCT_LIST] = Field(
        default=UITemplateType.PRODUCT_LIST,
        description="模板类型",
    )

    # 列表标题
    title: Optional[str] = Field(default=None, description="列表标题")
    subtitle: Optional[str] = Field(default=None, description="副标题")

    # 产品列表（简化版产品信息）
    products: List[Dict[str, Any]] = Field(..., description="产品列表")

    # 分页信息
    total_count: Optional[int] = Field(default=None, ge=0, description="总数量")
    page: Optional[int] = Field(default=None, ge=1, description="当前页")
    page_size: Optional[int] = Field(default=None, ge=1, description="每页数量")
    has_more: bool = Field(default=False, description="是否有更多")

    # 操作
    actions: Optional[List[ActionButton]] = Field(
        default=None,
        description="列表操作按钮",
    )

    @classmethod
    def get_example(cls) -> Dict[str, Any]:
        """Get an example product list template."""
        return {
            "type": "product_list",
            "title": "为您推荐",
            "subtitle": "根据您的浏览记录精选",
            "products": [
                {
                    "product_id": "PROD-001",
                    "name": "无线蓝牙耳机",
                    "price": 299.00,
                    "thumbnail": "https://example.com/earphone.jpg",
                    "rating": 4.5,
                },
                {
                    "product_id": "PROD-002",
                    "name": "智能手表",
                    "price": 899.00,
                    "thumbnail": "https://example.com/watch.jpg",
                    "rating": 4.7,
                },
            ],
            "total_count": 100,
            "page": 1,
            "page_size": 10,
            "has_more": True,
            "actions": [
                {
                    "label": "查看更多",
                    "action": "msg://帮我推荐更多类似的商品",
                    "style": "link",
                },
            ],
        }

    @classmethod
    def get_description(cls) -> str:
        """Get template description."""
        return "产品列表展示，适合搜索结果、推荐列表等场景"
