"""
Event processing for ht subprocess communication.
"""
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import HTProcess

logger = logging.getLogger(__name__)


class EventProcessor:
    """Handles processing of events from ht subprocess."""
    
    def __init__(self, ht_process: 'HTProcess'):
        self.ht_process = ht_process
        self.handlers = {
            'output': self._handle_output,
            'pid': self._handle_pid,
            'snapshot': self._handle_snapshot,
            'resize': self._handle_resize,
            'init': self._handle_init,
        }
    
    def process_event(self, event: dict) -> None:
        """Process a single event from ht."""
        event_type = event.get('type')
        handler = self.handlers.get(event_type)
        if handler:
            handler(event)
        else:
            # Handle unknown events gracefully
            logger.debug(f"Received unknown event type: {event_type}")
            self.ht_process.unknown_events.append(event)
    
    def _handle_output(self, event: dict) -> None:
        """Handle output events."""
        seq = event['data']['seq']
        self.ht_process.output.append(seq)
        self.ht_process.output_events.append(event)
        logger.debug(f"Output event: {len(seq)} characters")
    
    def _handle_pid(self, event: dict) -> None:
        """Handle PID events."""
        pid = event['data']['pid']
        self.ht_process.subprocess_pid = pid
        logger.debug(f"Subprocess PID: {pid}")
    
    def _handle_snapshot(self, event: dict) -> None:
        """Handle snapshot events."""
        # Store the latest snapshot
        self.ht_process.latest_snapshot = event['data']['text']
        logger.debug("Snapshot captured")
    
    def _handle_resize(self, event: dict) -> None:
        """Handle resize events."""
        data = event['data']
        self.ht_process.rows = data['rows']
        self.ht_process.cols = data['cols']
        logger.debug(f"Terminal resized to {data['cols']}x{data['rows']}")
    
    def _handle_init(self, event: dict) -> None:
        """Handle init events."""
        # Init is like snapshot but sent once at startup
        if 'text' in event['data']:
            self.ht_process.latest_snapshot = event['data']['text']
        logger.debug("Process initialized")
