"""
UI Template implementations.

This module contains concrete implementations of UI templates
for various data types like orders, products, and logistics.
"""

from app.ui_templates.templates.order import OrderTemplate, OrderItem, OrderStatus
from app.ui_templates.templates.product import ProductTemplate, ProductSpec
from app.ui_templates.templates.logistics import (
    LogisticsTemplate,
    LogisticsStatus,
    LogisticsEvent,
)

__all__ = [
    "OrderTemplate",
    "OrderItem",
    "OrderStatus",
    "ProductTemplate",
    "ProductSpec",
    "LogisticsTemplate",
    "LogisticsStatus",
    "LogisticsEvent",
]
