"""
Stack data structure (LIFO — last in, first out), backed by a Python
list.

Every operation is O(1) except where noted:
    push   — O(1) amortized
    pop    — O(1)
    peek   — O(1)
    is_empty — O(1)
    size     — O(1)
"""


class StackEmptyError(Exception):
    """Raised when pop() or peek() is called on an empty stack."""
    pass


class Stack:
    def __init__(self):
        self._items = []

    def push(self, item):
        """Push an item onto the top of the stack."""
        self._items.append(item)

    def pop(self):
        """Remove and return the item on top of the stack.

        Raises StackEmptyError if the stack is empty.
        """
        if self.is_empty():
            raise StackEmptyError("pop from an empty stack")
        return self._items.pop()

    def peek(self):
        """Return (without removing) the item on top of the stack.

        Raises StackEmptyError if the stack is empty.
        """
        if self.is_empty():
            raise StackEmptyError("peek at an empty stack")
        return self._items[-1]

    def is_empty(self):
        """Return True if the stack has no items."""
        return len(self._items) == 0

    def size(self):
        """Return the number of items currently on the stack."""
        return len(self._items)

    def __len__(self):
        return self.size()

    def __repr__(self):
        return f"Stack({self._items!r})"
