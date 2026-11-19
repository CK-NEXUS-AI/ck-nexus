"""Shared Knowledge — ระบบความรู้ร่วมของทีม.

ทุกครั้งที่ทำงานเสร็จ → บันทึกลง Shared Knowledge
ครั้งต่อไปที่เจอปัญหาคล้ายกัน → เรียกใช้ความรู้เดิม
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class KnowledgeEntry:
    entry_id: str
    topic: str
    agent_name: str
    content: str
    keywords: tuple[str, ...] = ()
    confidence: float = 0.0
    created_at: float = field(default_factory=time.time)
    used_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class SharedKnowledge:
    """ระบบความรู้ร่วมของทีม.

    บันทึกผลลัพธ์จากทุก Agent → เรียกใช้เมื่อเจอปัญหาคล้ายกัน
    """

    def __init__(self, persistence_path: str | None = None) -> None:
        self._entries: list[KnowledgeEntry] = []
        self._persistence_path = persistence_path
        if persistence_path:
            self._load()

    def add(
        self,
        topic: str,
        agent_name: str,
        content: str,
        keywords: tuple[str, ...] = (),
        confidence: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeEntry:
        """เพิ่มความรู้ใหม่."""
        entry = KnowledgeEntry(
            entry_id=f"know-{len(self._entries) + 1:04d}",
            topic=topic,
            agent_name=agent_name,
            content=content,
            keywords=tuple(k.lower() for k in keywords),
            confidence=confidence,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        if self._persistence_path:
            self._save()
        return entry

    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        min_confidence: float = 0.0,
    ) -> tuple[KnowledgeEntry, ...]:
        """ค้นหาความรู้จาก query."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored: list[tuple[float, KnowledgeEntry]] = []
        for entry in self._entries:
            score = 0.0
            # Score by keyword match
            for kw in entry.keywords:
                if kw in query_lower:
                    score += 2.0
                for word in query_words:
                    if word in kw:
                        score += 0.5
            # Score by topic match
            if query_lower in entry.topic.lower():
                score += 3.0
            # Score by confidence
            score += entry.confidence
            # Bonus for frequently used
            score += min(entry.used_count * 0.1, 1.0)

            if score > 0 and entry.confidence >= min_confidence:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [entry for _, entry in scored[:max_results]]

        # Mark as used
        for entry in results:
            entry.used_count += 1

        if self._persistence_path:
            self._save()

        return tuple(results)

    def get_by_topic(self, topic: str) -> tuple[KnowledgeEntry, ...]:
        """ดึงความรู้ตามหัวข้อ."""
        return tuple(e for e in self._entries if topic.lower() in e.topic.lower())

    def get_by_agent(self, agent_name: str) -> tuple[KnowledgeEntry, ...]:
        """ดึงความรู้ตาม Agent."""
        return tuple(e for e in self._entries if e.agent_name == agent_name)

    def stats(self) -> dict[str, Any]:
        """สถิติของระบบความรู้."""
        agent_counts: dict[str, int] = {}
        for e in self._entries:
            agent_counts[e.agent_name] = agent_counts.get(e.agent_name, 0) + 1

        return {
            "total_entries": len(self._entries),
            "by_agent": agent_counts,
            "avg_confidence": (
                sum(e.confidence for e in self._entries) / len(self._entries)
                if self._entries
                else 0.0
            ),
            "most_used": max(self._entries, key=lambda e: e.used_count).entry_id
            if self._entries
            else None,
        }

    def clear(self) -> None:
        """ล้างทั้งหมด."""
        self._entries.clear()
        if self._persistence_path:
            self._save()

    def _save(self) -> None:
        """บันทึกลงไฟล์."""
        if not self._persistence_path:
            return
        path = Path(self._persistence_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "entry_id": e.entry_id,
                "topic": e.topic,
                "agent_name": e.agent_name,
                "content": e.content,
                "keywords": list(e.keywords),
                "confidence": e.confidence,
                "created_at": e.created_at,
                "used_count": e.used_count,
                "metadata": e.metadata,
            }
            for e in self._entries
        ]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load(self) -> None:
        """โหลดจากไฟล์."""
        if not self._persistence_path:
            return
        path = Path(self._persistence_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data:
                self._entries.append(
                    KnowledgeEntry(
                        entry_id=item["entry_id"],
                        topic=item["topic"],
                        agent_name=item["agent_name"],
                        content=item["content"],
                        keywords=tuple(item.get("keywords", [])),
                        confidence=item.get("confidence", 0.0),
                        created_at=item.get("created_at", time.time()),
                        used_count=item.get("used_count", 0),
                        metadata=item.get("metadata", {}),
                    )
                )
        except (json.JSONDecodeError, KeyError):
            pass
