"""TODO list — short-term working memory for the current planning session."""

from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass
class TodoItem:
    id: int
    task: str
    status: Status = Status.PENDING

    def symbol(self) -> str:
        return {"pending": "[ ]", "in_progress": "[→]", "done": "[✓]"}[self.status]

    def __str__(self) -> str:
        return f"{self.symbol()} {self.task}"


class TodoList:
    def __init__(self) -> None:
        self._items: list[TodoItem] = []
        self._next_id = 1

    def add(self, task: str) -> TodoItem:
        item = TodoItem(id=self._next_id, task=task)
        self._next_id += 1
        self._items.append(item)
        return item

    def start(self, task_id: int) -> bool:
        return self._set_status(task_id, Status.IN_PROGRESS)

    def done(self, task_id: int) -> bool:
        return self._set_status(task_id, Status.DONE)

    def _set_status(self, task_id: int, status: Status) -> bool:
        for item in self._items:
            if item.id == task_id:
                item.status = status
                return True
        return False

    def as_context_string(self) -> str:
        if not self._items:
            return ""
        lines = ["Current TODO list:"]
        lines.extend(str(item) for item in self._items)
        return "\n".join(lines)

    def pending_count(self) -> int:
        return sum(1 for i in self._items if i.status != Status.DONE)

    def sync_from_messages(self, messages: list[dict]) -> None:
        """Parse TODO items from the last assistant message (best-effort sync).

        Looks for lines matching markdown checkbox patterns:
          [ ] pending task
          [→] in-progress task
          [✓] or [x] done task
        """
        import re
        last_content = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                last_content = msg["content"]
                break

        if not last_content:
            return

        pattern = re.compile(r"^\s*\[([ →✓x])\]\s+(.+)", re.MULTILINE)
        matches = pattern.findall(last_content)
        if not matches:
            return

        status_map = {
            " ": Status.PENDING,
            "→": Status.IN_PROGRESS,
            "✓": Status.DONE,
            "x": Status.DONE,
        }
        self._items.clear()
        self._next_id = 1
        for symbol, task in matches:
            item = TodoItem(
                id=self._next_id,
                task=task.strip(),
                status=status_map.get(symbol, Status.PENDING),
            )
            self._next_id += 1
            self._items.append(item)

    def as_list(self) -> list[dict]:
        """Return items as a list of dicts for thinking_fn events."""
        return [
            {"status": item.status.value, "task": item.task}
            for item in self._items
        ]
