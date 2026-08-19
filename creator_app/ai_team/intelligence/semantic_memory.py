"""Semantic Memory — จำแบบเข้าใจ ไม่ใช่แค่ท่องจำ.

เก็บความรู้แบบมีความหมาย — ไม่ใช่แค่ text:
- เข้าใจ context ของสิ่งที่เรียนรู้
- เชื่อมโยงความรู้เดิมกับสิ่งใหม่
- แนะนำสิ่งที่ควรรู้จากประสบการณ์เดิม
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    """ความรู้หนึ่งชิ้น."""

    content: str
    category: str
    context: str = ""
    importance: float = 0.5  # 0.0-1.0
    keywords: tuple[str, ...] = ()
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    related_to: tuple[str, ...] = ()  # indices of related memories
    tags: tuple[str, ...] = ()


class SemanticMemory:
    """ระบบความจำเชิงความหมาย — เข้าใจ ไม่ใช่แค่จำ.

    วิธีใช้:
        mem = SemanticMemory()
        mem.store("CK-NEXUS ต้องใช้ Evidence-First", "principle", importance=0.9)
        mem.store("Ruff + Bandit คือ CI tools", "knowledge", importance=0.7)
        
        results = mem.recall("CI tools อะไรบ้าง")
        for r in results:
            print(f"  - {r.content} (importance: {r.importance})")
    """

    def __init__(self, *, max_size: int = 5000, decay_rate: float = 0.01):
        self._memories: list[MemoryEntry] = []
        self._max_size = max_size
        self._decay_rate = decay_rate
        self._category_index: dict[str, list[int]] = {}
        self._keyword_index: dict[str, list[int]] = {}

    def store(
        self,
        content: str,
        category: str,
        *,
        context: str = "",
        importance: float = 0.5,
        keywords: tuple[str, ...] = (),
        tags: tuple[str, ...] = (),
    ) -> int:
        """เก็บความรู้ใหม่ — return index."""
        auto_keywords = self._extract_keywords(content)
        all_keywords = tuple(set(auto_keywords) | set(keywords))

        entry = MemoryEntry(
            content=content,
            category=category,
            context=context,
            importance=importance,
            keywords=all_keywords,
            tags=tags,
        )
        idx = len(self._memories)
        self._memories.append(entry)
        self._update_indices(idx, entry)
        self._evict_if_needed()
        return idx

    def recall(
        self,
        query: str,
        *,
        limit: int = 5,
        min_importance: float = 0.0,
        category: str | None = None,
    ) -> list[MemoryEntry]:
        """ค้นหาความรู้ที่เกี่ยวข้อง."""
        query_kw = set(self._extract_keywords(query))
        scored: list[tuple[float, MemoryEntry]] = []

        for entry in self._memories:
            if entry.importance < min_importance:
                continue
            if category and entry.category != category:
                continue
            score = self._relevance_score(query_kw, entry)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [entry for _, entry in scored[:limit]]
        for entry in results:
            entry.access_count += 1
        return results

    def store_experience(
        self,
        action: str,
        result: str,
        *,
        success: bool = True,
        importance: float = 0.6,
    ) -> int:
        """เก็บประสบการณ์ — action → result."""
        category = "experience_success" if success else "experience_failure"
        content = f"ทำ {action} → ได้ {result}"
        context = f"{'สำเร็จ' if success else 'ล้มเหลว'}: {action}"
        return self.store(
            content, category,
            context=context,
            importance=importance,
            keywords=self._extract_keywords(action + " " + result),
            tags=("experience",),
        )

    def suggest_related(self, query: str, limit: int = 3) -> list[MemoryEntry]:
        """แนะนำความรู้ที่เกี่ยวข้อง."""
        results = self.recall(query, limit=limit + 5)
        seen_content: set[str] = set()
        unique: list[MemoryEntry] = []
        for r in results:
            if r.content not in seen_content:
                seen_content.add(r.content)
                unique.append(r)
        return unique[:limit]

    def get_by_category(self, category: str) -> list[MemoryEntry]:
        """ดึงความรู้ทั้งหมดในหมวด."""
        return [e for e in self._memories if e.category == category]

    def get_important(self, min_importance: float = 0.8) -> list[MemoryEntry]:
        """ดึงความรู้ที่สำคัญ."""
        return [e for e in self._memories if e.importance >= min_importance]

    def _relevance_score(self, query_kw: set[str], entry: MemoryEntry) -> float:
        """คำนวณคะแนนความเกี่ยวข้อง."""
        if not query_kw:
            return 0.0
        entry_kw = set(entry.keywords)
        intersection = query_kw & entry_kw
        union = query_kw | entry_kw
        jaccard = len(intersection) / len(union) if union else 0.0
        category_bonus = 0.1 if any(k in entry.category for k in query_kw) else 0.0
        importance_bonus = entry.importance * 0.2
        recency_bonus = 0.1 / (1 + self._decay_rate * (time.time() - entry.timestamp))
        access_bonus = min(entry.access_count * 0.05, 0.2)
        return jaccard + category_bonus + importance_bonus + recency_bonus + access_bonus

    def _extract_keywords(self, text: str) -> list[str]:
        """แยกคำสำคัญ."""
        thai_stop = {"ของ", "ใน", "และ", "เป็น", "ที่", "มี", "ได้", "ไม่", "กับ", "จะ"}
        eng_stop = {
            "the", "a", "an", "is", "are", "was", "were",
            "be", "been", "to", "of", "in", "for", "on", "with",
        }
        words = text.lower().split()
        return [w for w in words if len(w) > 2 and w not in thai_stop and w not in eng_stop]

    def _update_indices(self, idx: int, entry: MemoryEntry) -> None:
        """อัปเดต index."""
        self._category_index.setdefault(entry.category, []).append(idx)
        for kw in entry.keywords:
            self._keyword_index.setdefault(kw, []).append(idx)

    def _evict_if_needed(self) -> None:
        """ลบความรู้เก่าถ้าเกิน max_size."""
        if len(self._memories) <= self._max_size:
            return
        scored = sorted(
            enumerate(self._memories),
            key=lambda x: x[1].importance + x[1].access_count * 0.1,
        )
        to_remove = scored[:len(self._memories) - self._max_size]
        for idx, _ in to_remove:
            self._memories[idx] = MemoryEntry(content="", category="__deleted__")

    def stats(self) -> dict[str, Any]:
        """สถิติ."""
        active = [e for e in self._memories if e.category != "__deleted__"]
        categories: dict[str, int] = {}
        for e in active:
            categories[e.category] = categories.get(e.category, 0) + 1
        return {
            "total_memories": len(active),
            "categories": categories,
            "avg_importance": round(
                sum(e.importance for e in active) / len(active), 3
            ) if active else 0.0,
        }
