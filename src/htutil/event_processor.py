"""
Event processing for ht subprocess communication.
"""

import logging
from typing import TYPE_CHECKING, Dict, Any, Callable

if TYPE_CHECKING:
    from .ht import HTProcess

logger = logging.getLogger(__name__)


class EventProcessor:
    """Handles processing of events from ht subprocess."""

    def __init__(self, ht_process: "HTProcess") -> None:
        self.ht_process = ht_process
        self.handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {
            "output": self._handle_output,
            "pid": self._handle_pid,
            "snapshot": self._handle_snapshot,
            "resize": self._handle_resize,
            "init": self._handle_init,
        }

    def process_event(self, event: Dict[str, Any]) -> None:
        """Process a single event from ht."""
        event_type = event.get("type")
        if event_type is None:
            logger.debug("Received event with no type")
            self.ht_process.unknown_events.append(event)
            return

        handler = self.handlers.get(event_type)
        if handler:
            handler(event)
        else:
            # Handle unknown events gracefully
            logger.debug(f"Received unknown event type: {event_type}")
            self.ht_process.unknown_events.append(event)

    def _handle_output(self, event: Dict[str, Any]) -> None:
        """Handle output events."""
        seq = event["data"]["seq"]
        self.ht_process.output.append(seq)
        self.ht_process.output_events.append(event)
        logger.debug(f"Output event: {len(seq)} characters")

    def _handle_pid(self, event: Dict[str, Any]) -> None:
        """Handle PID events."""
        pid = event["data"]["pid"]
        self.ht_process.subprocess_pid = pid
        logger.debug(f"Subprocess PID: {pid}")

    def _handle_snapshot(self, event: Dict[str, Any]) -> None:
        """Handle snapshot events."""
        # Store the latest snapshot
        self.ht_process.latest_snapshot = event["data"]["text"]
        logger.debug("Snapshot captured")

    def _handle_resize(self, event: Dict[str, Any]) -> None:
        """Handle resize events."""
        data = event["data"]
        self.ht_process.rows = data["rows"]
        self.ht_process.cols = data["cols"]
        logger.debug(f"Terminal resized to {data['cols']}x{data['rows']}")

    def _handle_init(self, event: Dict[str, Any]) -> None:
        """Handle init events."""
        # Init is like snapshot but sent once at startup
        if "text" in event["data"]:
            self.ht_process.latest_snapshot = event["data"]["text"]
        logger.debug("Process initialized")
