"""
Action URI Parser and Utilities.

This module provides utilities for parsing and building Action URIs
used in tgo-ui-widget ActionButton definitions.

Action URI Format: {protocol}://{content}

Supported protocols:
- url://   Open external URL
- msg://   Send message to chat
- copy://  Copy text to clipboard
"""

import re
from dataclasses import dataclass
from typing import Optional

from app.ui_templates.schema import ActionProtocol


@dataclass
class ParsedAction:
    """Parsed Action URI components."""

    protocol: str
    """Protocol type (url, msg, copy)"""

    content: str
    """Content after protocol://"""

    raw: str
    """Original URI string"""

    is_valid: bool = True
    """Whether the URI was successfully parsed"""

    error: Optional[str] = None
    """Error message if parsing failed"""


# Regex pattern for Action URI
ACTION_URI_PATTERN = re.compile(
    r"^(?P<protocol>[a-z]+)://(?P<content>.*)$",
    re.IGNORECASE,
)

# Valid protocols
VALID_PROTOCOLS = {p.value for p in ActionProtocol}


def parse_action_uri(uri: str) -> ParsedAction:
    """
    Parse an Action URI string into its components.

    Args:
        uri: Action URI string (e.g., "url://https://example.com")

    Returns:
        ParsedAction with protocol, content, and validation status.

    Examples:
        >>> result = parse_action_uri("url://https://example.com")
        >>> result.protocol
        'url'
        >>> result.content
        'https://example.com'

        >>> result = parse_action_uri("msg://查看订单详情")
        >>> result.protocol
        'msg'
        >>> result.content
        '查看订单详情'

        >>> result = parse_action_uri("copy://SF1234567890")
        >>> result.protocol
        'copy'
        >>> result.content
        'SF1234567890'
    """
    if not uri:
        return ParsedAction(
            protocol="",
            content="",
            raw=uri,
            is_valid=False,
            error="Empty URI",
        )

    match = ACTION_URI_PATTERN.match(uri)
    if not match:
        return ParsedAction(
            protocol="",
            content="",
            raw=uri,
            is_valid=False,
            error=f"Invalid Action URI format: {uri}",
        )

    protocol = match.group("protocol").lower()
    content = match.group("content") or ""

    # Validate protocol
    is_valid = protocol in VALID_PROTOCOLS
    error = None if is_valid else f"Unknown protocol: {protocol}. Supported: {', '.join(VALID_PROTOCOLS)}"

    return ParsedAction(
        protocol=protocol,
        content=content,
        raw=uri,
        is_valid=is_valid,
        error=error,
    )


def build_action_uri(protocol: str, content: str) -> str:
    """
    Build an Action URI from components.

    Args:
        protocol: Protocol type (url, msg, copy)
        content: Content to include after protocol://

    Returns:
        Formatted Action URI string.

    Examples:
        >>> build_action_uri("url", "https://example.com")
        'url://https://example.com'

        >>> build_action_uri("msg", "查看订单详情")
        'msg://查看订单详情'

        >>> build_action_uri("copy", "SF1234567890")
        'copy://SF1234567890'
    """
    return f"{protocol}://{content}"


def is_valid_action_uri(uri: str) -> bool:
    """
    Check if a string is a valid Action URI.

    Args:
        uri: String to validate.

    Returns:
        True if valid Action URI, False otherwise.
    """
    result = parse_action_uri(uri)
    return result.is_valid


def get_protocol(uri: str) -> Optional[str]:
    """
    Extract the protocol from an Action URI.

    Args:
        uri: Action URI string.

    Returns:
        Protocol string or None if invalid.
    """
    result = parse_action_uri(uri)
    return result.protocol if result.is_valid else None


# Convenience builders for supported action types


def url_action(url: str) -> str:
    """
    Build an external URL action.

    Args:
        url: Full URL to open.

    Returns:
        Action URI for external navigation.

    Example:
        >>> url_action("https://example.com/product/123")
        'url://https://example.com/product/123'
    """
    return build_action_uri("url", url)


def msg_action(message: str) -> str:
    """
    Build a send message action.

    Args:
        message: Message content to send to chat.

    Returns:
        Action URI for sending message.

    Example:
        >>> msg_action("帮我查询这个订单的物流")
        'msg://帮我查询这个订单的物流'
    """
    return build_action_uri("msg", message)


def copy_action(text: str) -> str:
    """
    Build a copy to clipboard action.

    Args:
        text: Text to copy.

    Returns:
        Action URI for copy action.

    Example:
        >>> copy_action("SF1234567890")
        'copy://SF1234567890'
    """
    return build_action_uri("copy", text)


# Action handler descriptions for reference
ACTION_HANDLERS = {
    "url": "Open external URL in browser",
    "msg": "Send message to chat input",
    "copy": "Copy text to clipboard",
}


def get_action_description(protocol: str) -> str:
    """
    Get a human-readable description of an action protocol.

    Args:
        protocol: Action protocol name.

    Returns:
        Description string.
    """
    return ACTION_HANDLERS.get(protocol, f"Unknown action: {protocol}")
