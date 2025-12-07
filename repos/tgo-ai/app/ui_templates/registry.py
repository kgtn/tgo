"""
UI Template Registry.

This module provides a central registry for UI templates, allowing
dynamic registration and lookup of template schemas.
"""

import json
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.ui_templates.schema import UITemplate

logger = get_logger(__name__)


class UITemplateRegistry:
    """
    Central registry for UI templates.

    Templates register themselves using the @UITemplateRegistry.register decorator.
    The registry provides methods to lookup templates and generate documentation
    for use in LLM prompts.
    """

    _templates: Dict[str, Type["UITemplate"]] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, template_type: str):
        """
        Decorator to register a UI template class.

        Args:
            template_type: The type identifier for this template (e.g., "order", "product").

        Returns:
            Decorator function that registers the template class.

        Example:
            @UITemplateRegistry.register("order")
            class OrderTemplate(UITemplate):
                ...
        """

        def decorator(template_cls: Type["UITemplate"]) -> Type["UITemplate"]:
            cls._templates[template_type] = template_cls
            logger.debug(f"Registered UI template: {template_type}")
            return template_cls

        return decorator

    @classmethod
    def get_template(cls, template_type: str) -> Optional[Type["UITemplate"]]:
        """
        Get a template class by its type identifier.

        Args:
            template_type: The type identifier (e.g., "order", "product").

        Returns:
            The template class, or None if not found.
        """
        cls._ensure_initialized()
        return cls._templates.get(template_type)

    @classmethod
    def get_all_templates(cls) -> Dict[str, Type["UITemplate"]]:
        """
        Get all registered templates.

        Returns:
            Dictionary mapping template types to their classes.
        """
        cls._ensure_initialized()
        return cls._templates.copy()

    @classmethod
    def list_template_types(cls) -> List[str]:
        """
        Get a list of all registered template types.

        Returns:
            List of template type identifiers.
        """
        cls._ensure_initialized()
        return list(cls._templates.keys())

    @classmethod
    def get_template_schema(cls, template_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the JSON schema for a specific template.

        Args:
            template_type: The type identifier.

        Returns:
            JSON schema dictionary, or None if template not found.
        """
        template_cls = cls.get_template(template_type)
        if template_cls is None:
            return None
        return template_cls.model_json_schema()

    @classmethod
    def get_template_example(cls, template_type: str) -> Optional[Dict[str, Any]]:
        """
        Get an example for a specific template.

        Args:
            template_type: The type identifier.

        Returns:
            Example dictionary, or None if template not found.
        """
        template_cls = cls.get_template(template_type)
        if template_cls is None:
            return None
        try:
            return template_cls.get_example()
        except NotImplementedError:
            return None

    @classmethod
    def generate_full_documentation(cls) -> str:
        """
        Generate full documentation for all templates.

        This is primarily for debugging or admin purposes,
        not for inclusion in LLM prompts.

        Returns:
            Formatted documentation string.
        """
        cls._ensure_initialized()
        docs = ["# UI Template Documentation\n"]

        for template_type, template_cls in cls._templates.items():
            schema = template_cls.model_json_schema()
            description = template_cls.get_description()

            docs.append(f"## {template_type}\n")
            docs.append(f"{description}\n")
            docs.append("### Schema:\n")
            docs.append(f"```json\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n```\n")

            try:
                example = template_cls.get_example()
                docs.append("### Example:\n")
                docs.append(f"```tgo-ui-widget\n{json.dumps(example, indent=2, ensure_ascii=False)}\n```\n")
            except NotImplementedError:
                pass

        return "\n".join(docs)

    @classmethod
    def validate_data(cls, template_type: str, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate data against a template schema.

        Args:
            template_type: The type identifier.
            data: Data to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        template_cls = cls.get_template(template_type)
        if template_cls is None:
            return False, f"Unknown template type: {template_type}"

        try:
            template_cls(**data)
            return True, None
        except Exception as e:
            return False, str(e)

    @classmethod
    def render(cls, template_type: str, data: Dict[str, Any]) -> Optional[str]:
        """
        Render data as a tgo-ui-widget markdown code block.

        Args:
            template_type: The type identifier.
            data: Data to render.

        Returns:
            Formatted markdown string, or None if validation fails.
        """
        template_cls = cls.get_template(template_type)
        if template_cls is None:
            return None

        try:
            instance = template_cls(**data)
            return instance.to_markdown()
        except Exception as e:
            logger.error(f"Failed to render template {template_type}: {e}")
            return None

    @classmethod
    def _ensure_initialized(cls) -> None:
        """
        Ensure all template modules are imported.

        This triggers the @register decorators to run.
        """
        if cls._initialized:
            return

        # Import template modules to trigger registration
        try:
            from app.ui_templates.templates import (  # noqa: F401
                order,
                product,
                logistics,
            )
            cls._initialized = True
        except ImportError as e:
            logger.warning(f"Failed to import some template modules: {e}")
            cls._initialized = True
