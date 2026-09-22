"""
Queue data structure (FIFO — first in, first out), backed by
collections.deque so both ends are O(1).

(Named queue_ds.py rather than queue.py so it doesn't shadow Python's
built-in `queue` module from the standard library.)

Every operation is O(1):
    enqueue  — O(1)
    dequeue  — O(1)
    peek     — O(1)
    is_empty — O(1)
    size     — O(1)
"""

from collections import deque


class QueueEmptyError(Exception):
    """Raised when dequeue() or peek() is called on an empty queue."""
    pass


class Queue:
    def __init__(self):
        self._items = deque()

    def enqueue(self, item):
        """Add an item to the back of the queue."""
        self._items.append(item)

    def dequeue(self):
        """Remove and return the item at the front of the queue.

        Raises QueueEmptyError if the queue is empty.
        """
        if self.is_empty():
            raise QueueEmptyError("dequeue from an empty queue")
        return self._items.popleft()

    def peek(self):
        """Return (without removing) the item at the front of the
        queue.

        Raises QueueEmptyError if the queue is empty.
        """
        if self.is_empty():
            raise QueueEmptyError("peek at an empty queue")
        return self._items[0]

    def is_empty(self):
        """Return True if the queue has no items."""
        return len(self._items) == 0

    def size(self):
        """Return the number of items currently in the queue."""
        return len(self._items)

    def __len__(self):
        return self.size()

    def __repr__(self):
        return f"Queue({list(self._items)!r})"
