"""
UI Block Parser for streaming content.

This module provides utilities for detecting and parsing tgo-ui-widget
code blocks from streaming content.
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.ui_templates.registry import UITemplateRegistry

logger = get_logger(__name__)

# Regex patterns for UI block detection
UI_BLOCK_START_PATTERN = re.compile(r"```tgo-ui-widget\s*\n?", re.IGNORECASE)
UI_BLOCK_END_PATTERN = re.compile(r"\n?```")

# Complete block pattern for non-streaming parsing
UI_BLOCK_COMPLETE_PATTERN = re.compile(
    r"```tgo-ui-widget\s*\n([\s\S]*?)\n?```",
    re.IGNORECASE,
)


class UIBlockState(str, Enum):
    """State of UI block parsing."""

    IDLE = "idle"  # Not inside a UI block
    STARTED = "started"  # Found opening fence, collecting content
    COMPLETED = "completed"  # Found closing fence, block complete
    ERROR = "error"  # Parsing error


@dataclass
class UIBlock:
    """Represents a parsed UI block."""

    block_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    template_type: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    raw_content: str = ""
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)
    start_position: int = 0
    end_position: int = 0


@dataclass
class ParseResult:
    """Result of parsing content for UI blocks."""

    blocks: List[UIBlock] = field(default_factory=list)
    remaining_text: str = ""
    has_partial_block: bool = False
    partial_content: str = ""


class StreamingUIBlockParser:
    """
    Parser for detecting UI blocks in streaming content.

    This parser maintains state across streaming chunks to properly
    detect when a tgo-ui-widget code block starts and ends.
    """

    def __init__(
        self,
        on_block_started: Optional[Callable[[str], None]] = None,
        on_block_content: Optional[Callable[[str, str, int], None]] = None,
        on_block_completed: Optional[Callable[[UIBlock], None]] = None,
        on_block_error: Optional[Callable[[str, str, str], None]] = None,
    ):
        """
        Initialize the streaming parser.

        Args:
            on_block_started: Callback when block starts (block_id)
            on_block_content: Callback for content chunks (block_id, content, chunk_index)
            on_block_completed: Callback when block completes (UIBlock)
            on_block_error: Callback on error (block_id, error_type, message)
        """
        self._state = UIBlockState.IDLE
        self._current_block_id: Optional[str] = None
        self._buffer = ""
        self._block_content = ""
        self._chunk_index = 0

        # Callbacks
        self._on_block_started = on_block_started
        self._on_block_content = on_block_content
        self._on_block_completed = on_block_completed
        self._on_block_error = on_block_error

    @property
    def state(self) -> UIBlockState:
        """Current parser state."""
        return self._state

    @property
    def is_inside_block(self) -> bool:
        """Whether currently inside a UI block."""
        return self._state == UIBlockState.STARTED

    def feed(self, chunk: str) -> Tuple[str, Optional[UIBlock]]:
        """
        Feed a chunk of content to the parser.

        Args:
            chunk: Content chunk from streaming.

        Returns:
            Tuple of (non-UI content, completed UIBlock or None)
        """
        self._buffer += chunk
        non_ui_content = ""
        completed_block = None

        while True:
            if self._state == UIBlockState.IDLE:
                # Look for block start
                match = UI_BLOCK_START_PATTERN.search(self._buffer)
                if match:
                    # Emit content before the block
                    non_ui_content += self._buffer[: match.start()]
                    self._buffer = self._buffer[match.end() :]

                    # Start new block
                    self._state = UIBlockState.STARTED
                    self._current_block_id = str(uuid.uuid4())
                    self._block_content = ""
                    self._chunk_index = 0

                    if self._on_block_started:
                        self._on_block_started(self._current_block_id)
                else:
                    # No block start found - check if we might be in a partial match
                    # Keep potential partial match in buffer
                    potential_start = self._buffer.rfind("```")
                    if potential_start >= 0 and potential_start > len(self._buffer) - 20:
                        # Might be partial, keep it
                        non_ui_content += self._buffer[:potential_start]
                        self._buffer = self._buffer[potential_start:]
                    else:
                        non_ui_content += self._buffer
                        self._buffer = ""
                    break

            elif self._state == UIBlockState.STARTED:
                # Look for block end
                match = UI_BLOCK_END_PATTERN.search(self._buffer)
                if match:
                    # Found end - complete the block
                    self._block_content += self._buffer[: match.start()]
                    self._buffer = self._buffer[match.end() :]

                    # Parse and validate the block
                    completed_block = self._complete_block()
                    self._state = UIBlockState.IDLE
                    break
                else:
                    # No end found yet - buffer might contain partial end marker
                    # Keep last few characters in case of partial ```
                    if len(self._buffer) > 3:
                        content_to_add = self._buffer[:-3]
                        self._block_content += content_to_add
                        self._buffer = self._buffer[-3:]

                        if self._on_block_content and content_to_add:
                            self._on_block_content(
                                self._current_block_id,
                                content_to_add,
                                self._chunk_index,
                            )
                            self._chunk_index += 1
                    break

        return non_ui_content, completed_block

    def _complete_block(self) -> UIBlock:
        """Complete and parse the current block."""
        block = UIBlock(
            block_id=self._current_block_id,
            raw_content=self._block_content.strip(),
        )

        try:
            # Parse JSON content
            data = json.loads(block.raw_content)
            block.data = data

            # Extract template type
            template_type = data.get("type")
            if template_type:
                block.template_type = template_type

                # Validate against schema
                is_valid, error_msg = UITemplateRegistry.validate_data(
                    template_type, data
                )
                block.is_valid = is_valid
                if error_msg:
                    block.validation_errors.append(error_msg)
            else:
                block.validation_errors.append("Missing 'type' field in UI block")

        except json.JSONDecodeError as e:
            block.validation_errors.append(f"JSON parse error: {str(e)}")
            if self._on_block_error:
                self._on_block_error(
                    self._current_block_id,
                    "parse_error",
                    str(e),
                )

        if self._on_block_completed:
            self._on_block_completed(block)

        return block

    def flush(self) -> Tuple[str, Optional[UIBlock]]:
        """
        Flush any remaining content in the buffer.

        Call this when streaming is complete to handle any remaining content.

        Returns:
            Tuple of (remaining content, incomplete UIBlock or None)
        """
        remaining = self._buffer
        incomplete_block = None

        if self._state == UIBlockState.STARTED:
            # We have an incomplete block
            self._block_content += self._buffer
            incomplete_block = UIBlock(
                block_id=self._current_block_id,
                raw_content=self._block_content.strip(),
            )
            incomplete_block.validation_errors.append("Incomplete UI block (stream ended)")

            if self._on_block_error:
                self._on_block_error(
                    self._current_block_id,
                    "incomplete",
                    "Stream ended with incomplete UI block",
                )

            remaining = ""

        self._buffer = ""
        self._state = UIBlockState.IDLE

        return remaining, incomplete_block

    def reset(self) -> None:
        """Reset parser state."""
        self._state = UIBlockState.IDLE
        self._current_block_id = None
        self._buffer = ""
        self._block_content = ""
        self._chunk_index = 0


def parse_ui_blocks(content: str) -> ParseResult:
    """
    Parse all UI blocks from content (non-streaming).

    Args:
        content: Full content to parse.

    Returns:
        ParseResult with all found blocks.
    """
    result = ParseResult()
    last_end = 0

    for match in UI_BLOCK_COMPLETE_PATTERN.finditer(content):
        block = UIBlock(
            start_position=match.start(),
            end_position=match.end(),
            raw_content=match.group(1).strip(),
        )

        try:
            data = json.loads(block.raw_content)
            block.data = data
            block.template_type = data.get("type")

            if block.template_type:
                is_valid, error_msg = UITemplateRegistry.validate_data(
                    block.template_type, data
                )
                block.is_valid = is_valid
                if error_msg:
                    block.validation_errors.append(error_msg)
            else:
                block.validation_errors.append("Missing 'type' field")

        except json.JSONDecodeError as e:
            block.validation_errors.append(f"JSON parse error: {str(e)}")

        result.blocks.append(block)
        last_end = match.end()

    # Check for partial block at the end
    remaining = content[last_end:]
    partial_match = UI_BLOCK_START_PATTERN.search(remaining)
    if partial_match:
        result.has_partial_block = True
        result.partial_content = remaining[partial_match.start() :]
        result.remaining_text = remaining[: partial_match.start()]
    else:
        result.remaining_text = remaining

    return result


def extract_ui_blocks_for_rendering(content: str) -> List[Dict[str, Any]]:
    """
    Extract UI blocks from content in a format suitable for frontend rendering.

    Args:
        content: Content containing UI blocks.

    Returns:
        List of dicts with 'type', 'data', and 'raw' keys.
    """
    result = parse_ui_blocks(content)
    blocks = []

    for block in result.blocks:
        if block.is_valid and block.data:
            blocks.append({
                "type": block.template_type,
                "data": block.data,
                "raw": block.raw_content,
                "block_id": block.block_id,
            })

    return blocks
