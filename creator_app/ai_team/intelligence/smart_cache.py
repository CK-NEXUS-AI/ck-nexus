"""Smart Cache — แคชอัจฉริยะ 2 ชั้น.

ชั้นที่ 1: Exact Cache — จำคำตอบเดิมเป๊ะๆ (hash-based)
ชั้นที่ 2: Semantic Cache — ค้นหาคำตอบคล้ายๆ (keyword similarity)

ลดเวลาตอบกลับ 60-90% สำหรับคำถามที่เคยตอบแล้ว
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """รายการแคชหนึ่งรายการ."""

    key: str
    response: str
    timestamp: float
    hit_count: int = 0
    tags: tuple[str, ...] = ()
    semantic_keywords: tuple[str, ...] = ()


class SmartCache:
    """แคชอัจฉริยะ 2 ชั้น — Exact + Semantic.

    วิธีใช้:
        cache = SmartCache()
        result = cache.get("สรุปอีเมลล่าสุด")
        if result is None:
            response = do_expensive_work()
            cache.set("สรุปอีเมลล่าสุด", response, tags=("email", "summary"))
        else:
            print(f"Cache hit! ประหยัดเวลาไป {result.response[:50]}...")
    """

    def __init__(self, *, exact_ttl: float = 3600, semantic_ttl: float = 7200,
                 max_size: int = 1000, similarity_threshold: float = 0.6):
        self._exact: dict[str, CacheEntry] = {}
        self._semantic: list[CacheEntry] = []
        self._exact_ttl = exact_ttl
        self._semantic_ttl = semantic_ttl
        self._max_size = max_size
        self._similarity_threshold = similarity_threshold
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def _hash_key(self, query: str) -> str:
        """สร้าง hash จาก query."""
        normalized = query.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _extract_keywords(self, text: str) -> tuple[str, ...]:
        """แยกคำสำคัญจากข้อความ."""
        thai_keywords = [
            "อีเมล", "-email", "mail", "summarize", "สรุป",
            "ตาราง", "sheets", "คำนวณ", "calculate",
            "โค้ด", "code", "เขียน", "write", "debug",
            "ปลอดภัย", "security", "scan", "สแกน",
            "deploy", "deploy", "api", "key",
            " google", "slack", "telegram", "notion",
            "gmail", "calendar", "drive", "docs",
            "ghtest", "pytest", "ruff", "bandit",
        ]
        text_lower = text.lower()
        found = []
        for kw in thai_keywords:
            if kw in text_lower:
                found.append(kw)
        words = text_lower.split()
        for w in words:
            if len(w) > 3 and w not in found:
                found.append(w)
        return tuple(found[:20])

    def _keyword_similarity(self, kw1: tuple[str, ...], kw2: tuple[str, ...]) -> float:
        """คำนวณความคล้ายของ keyword sets."""
        if not kw1 or not kw2:
            return 0.0
        set1, set2 = set(kw1), set(kw2)
        intersection = set1 & set2
        union = set1 | set2
        return len(intersection) / len(union) if union else 0.0

    def get(self, query: str, *, allow_semantic: bool = True) -> CacheEntry | None:
        """ดึงจากแคช; ปิด semantic lookup ได้เมื่อต้องการผลตรงคำขอเท่านั้น."""
        now = time.time()

        # ชั้น 1: Exact Cache
        key = self._hash_key(query)
        entry = self._exact.get(key)
        if entry and (now - entry.timestamp) < self._exact_ttl:
            entry.hit_count += 1
            self._stats["hits"] += 1
            return entry
        elif entry:
            del self._exact[key]

        # ชั้น 2: Semantic Cache (opt-in for callers that can tolerate approximate matches)
        if not allow_semantic:
            self._stats["misses"] += 1
            return None

        query_kw = self._extract_keywords(query)
        best_match: CacheEntry | None = None
        best_score = 0.0
        for entry in self._semantic:
            if (now - entry.timestamp) >= self._semantic_ttl:
                continue
            score = self._keyword_similarity(query_kw, entry.semantic_keywords)
            if score > best_score and score >= self._similarity_threshold:
                best_score = score
                best_match = entry

        if best_match:
            best_match.hit_count += 1
            self._stats["hits"] += 1
            return best_match

        self._stats["misses"] += 1
        return None

    def set(self, query: str, response: str, *, tags: tuple[str, ...] = ()) -> None:
        """บันทึกลงแคช — ทั้ง exact และ semantic."""
        now = time.time()
        key = self._hash_key(query)
        keywords = self._extract_keywords(query)
        entry = CacheEntry(
            key=key, response=response, timestamp=now,
            tags=tags, semantic_keywords=keywords,
        )
        self._exact[key] = entry
        self._semantic.append(entry)
        self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        """ลบรายการเก่าถ้าเกิน max_size."""
        while len(self._semantic) > self._max_size:
            removed = self._semantic.pop(0)
            self._exact.pop(removed.key, None)
            self._stats["evictions"] += 1

    def invalidate(self, query: str) -> bool:
        """ลบรายการแคชของ query นี้."""
        key = self._hash_key(query)
        removed = key in self._exact
        if removed:
            del self._exact[key]
        self._semantic = [e for e in self._semantic if e.key != key]
        return removed

    def clear(self) -> None:
        """ล้างแคชทั้งหมด."""
        self._exact.clear()
        self._semantic.clear()

    @property
    def stats(self) -> dict[str, int]:
        """สถิติการใช้งาน."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0
        return {
            **self._stats,
            "total_entries_exact": len(self._exact),
            "total_entries_semantic": len(self._semantic),
            "hit_rate_percent": round(hit_rate, 1),
        }
