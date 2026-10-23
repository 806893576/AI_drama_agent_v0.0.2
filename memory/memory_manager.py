"""统一记忆管理器。"""

from __future__ import annotations

from memory.checkpoint import JsonCheckpointStore
from memory.long_memory import LongTermMemory
from memory.short_memory import ShortTermMemory
from memory.vector_memory import MemoryDocument, VectorMemory


class MemoryManager:
    def __init__(self) -> None:
        self.short = ShortTermMemory()
        self.long = LongTermMemory()
        self.vector = VectorMemory()
        self.checkpoints = JsonCheckpointStore()

    def remember_project_note(self, key: str, text: str) -> None:
        self.long.put(key, text)
        self.vector.add(MemoryDocument(doc_id=key, text=text))
