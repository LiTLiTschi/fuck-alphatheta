"""
Threading utilities for thread-safe communication between components.
"""

from queue import Queue, Empty
from threading import Event
from typing import Any, Optional
import time


class ThreadSafeQueue:
    """
    Wrapper around queue.Queue with helper methods for common operations.
    """

    def __init__(self, maxsize: int = 0):
        """
        Initialize thread-safe queue.

        Args:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self.queue = Queue(maxsize=maxsize)

    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None):
        """
        Put an item into the queue.

        Args:
            item: Item to add to queue
            block: Whether to block if queue is full
            timeout: Timeout in seconds (None = wait forever)
        """
        self.queue.put(item, block=block, timeout=timeout)

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """
        Get an item from the queue.

        Args:
            block: Whether to block if queue is empty
            timeout: Timeout in seconds (None = wait forever)

        Returns:
            Item from queue

        Raises:
            Empty: If queue is empty and timeout expires
        """
        return self.queue.get(block=block, timeout=timeout)

    def get_nowait(self) -> Optional[Any]:
        """
        Get an item from queue without blocking.

        Returns:
            Item from queue or None if queue is empty
        """
        try:
            return self.queue.get_nowait()
        except Empty:
            return None

    def get_all(self) -> list:
        """
        Get all items currently in the queue without blocking.

        Returns:
            List of all items in queue (empty list if queue is empty)
        """
        items = []
        while True:
            item = self.get_nowait()
            if item is None:
                break
            items.append(item)
        return items

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self.queue.empty()

    def qsize(self) -> int:
        """Get approximate queue size."""
        return self.queue.qsize()

    def clear(self):
        """Clear all items from the queue."""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except Empty:
                break


class ShutdownEvent:
    """
    Thread-safe shutdown event for coordinating thread termination.
    """

    def __init__(self):
        """Initialize shutdown event."""
        self.event = Event()

    def set(self):
        """Signal shutdown."""
        self.event.set()

    def is_set(self) -> bool:
        """Check if shutdown has been signaled."""
        return self.event.is_set()

    def wait(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for shutdown signal.

        Args:
            timeout: Timeout in seconds (None = wait forever)

        Returns:
            True if shutdown was signaled, False if timeout
        """
        return self.event.wait(timeout)

    def clear(self):
        """Clear shutdown signal."""
        self.event.clear()


class RateLimiter:
    """
    Simple rate limiter for controlling operation frequency.
    """

    def __init__(self, max_calls_per_second: float):
        """
        Initialize rate limiter.

        Args:
            max_calls_per_second: Maximum allowed calls per second
        """
        self.min_interval = 1.0 / max_calls_per_second
        self.last_call_time = 0.0

    def wait_if_needed(self):
        """
        Wait if necessary to maintain rate limit.
        """
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time

        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            time.sleep(sleep_time)

        self.last_call_time = time.time()

    def can_proceed(self) -> bool:
        """
        Check if we can proceed without waiting.

        Returns:
            True if enough time has passed, False otherwise
        """
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        return time_since_last_call >= self.min_interval
