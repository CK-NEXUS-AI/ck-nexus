"""Auto Model Router — เลือกโมเดลอัตโนมัติตามความยากของงาน.

งานง่าย → โมเดลเร็ว (Groq/Llama3) — ตอบภายใน 1 วินาที
งานยาก → โมเดลฉลาด (GPT-4o/Claude) — คิดลึกกว่า
ประหยัดค่าใช้จ่าย + เร็วขึ้น + ตอบได้ดีกว่า
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TaskDifficulty(Enum):
    TRIVIAL = "trivial"       # ทักทาย, คำสั่งง่ายๆ
    EASY = "easy"             # สรุปสั้นๆ, แปลภาษา
    MEDIUM = "medium"         # เขียนโค้ด, วิเคราะห์ข้อมูล
    HARD = "hard"             # ออกแบบระบบ, architecture review
    EXPERT = "expert"         # security audit, multi-step reasoning


@dataclass
class ModelProfile:
    """โปรไฟล์ของโมเดล."""

    name: str
    speed_rating: int     # 1-10 (10 = เร็วที่สุด)
    quality_rating: int   # 1-10 (10 = เก่งที่สุด)
    cost_per_token: float # relative cost
    strengths: tuple[str, ...] = ()
    max_difficulty: TaskDifficulty = TaskDifficulty.HARD


MODEL_PROFILES: list[ModelProfile] = [
    ModelProfile(
        name="groq/llama3",
        speed_rating=10, quality_rating=6, cost_per_token=0.0,
        strengths=("fast", "simple", "translation", "summary"),
        max_difficulty=TaskDifficulty.EASY,
    ),
    ModelProfile(
        name="gemini-flash",
        speed_rating=9, quality_rating=7, cost_per_token=0.0,
        strengths=("fast", "code", "analysis", "multilingual"),
        max_difficulty=TaskDifficulty.MEDIUM,
    ),
    ModelProfile(
        name="gpt-4o-mini",
        speed_rating=7, quality_rating=7, cost_per_token=0.15,
        strengths=("code", "analysis", "reasoning"),
        max_difficulty=TaskDifficulty.MEDIUM,
    ),
    ModelProfile(
        name="gpt-4o",
        speed_rating=5, quality_rating=9, cost_per_token=1.0,
        strengths=("reasoning", "complex", "architecture", "creative"),
        max_difficulty=TaskDifficulty.HARD,
    ),
    ModelProfile(
        name="claude-3.5-sonnet",
        speed_rating=5, quality_rating=9, cost_per_token=0.8,
        strengths=("reasoning", "code", "analysis", "security"),
        max_difficulty=TaskDifficulty.EXPERT,
    ),
    ModelProfile(
        name="ollama/llama3-local",
        speed_rating=8, quality_rating=5, cost_per_token=0.0,
        strengths=("fast", "local", "privacy", "offline"),
        max_difficulty=TaskDifficulty.EASY,
    ),
]


class AutoModelRouter:
    """เลือกโมเดลอัตโนมัติตามความยากของงาน.

    วิธีใช้:
        router = AutoModelRouter()
        model = router.select_model("สรุปอีเมลล่าสุด 3 ฉบับ")
        print(f"เลือก: {model.name} (เร็ว {model.speed_rating}/10, เก่ง {model.quality_rating}/10)")

        model = router.select_model("วิเคราะห์ช่องโหว่ security ของระบบ")
        print(f"เลือก: {model.name}")
    """

    # คำสำคัญบ่งบอกความยาก
    _HARD_KEYWORDS = frozenset({
        "วิเคราะห์เชิงลึก", "deep analysis", "architecture", "ออกแบบระบบ",
        "security audit", "threat model", "penetration",
        "multi-step", "หลายขั้นตอน", "complex", "ซับซ้อน",
        "reasoning", "logic", "ตรรกะ", "proof", "พิสูจน์",
        "optimization", "optimize", "refactor ขนาดใหญ่",
        "review โค้ด", "code review", " refactor ",
    })

    _EASY_KEYWORDS = frozenset({
        "ทักทาย", "hello", "hi", "สวัสดี",
        "แปล", "translate",
        "สรุปสั้น", "short summary",
        "คำนวณ", "calculate",
        "หา", "search", "ค้นหา",
    })

    def __init__(self, *, prefer_free: bool = True, available_models: list[str] | None = None):
        self._prefer_free = prefer_free
        self._available = available_models
        self._history: list[dict] = []

    def classify_difficulty(self, task: str) -> TaskDifficulty:
        """จัดระดับความยากของงาน."""
        task_lower = task.lower()
        if any(kw in task_lower for kw in self._HARD_KEYWORDS):
            return TaskDifficulty.HARD
        if any(kw in task_lower for kw in self._EASY_KEYWORDS):
            return TaskDifficulty.EASY
        if len(task) < 20:
            return TaskDifficulty.TRIVIAL
        if len(task) > 200:
            return TaskDifficulty.MEDIUM
        complex_indicators = [
            "สร้าง", "create", "เขียน", "write",
            "debug", "แก้", "fix", "วิเคราะห์",
            "analyze", "check", "ตรวจ",
        ]
        if sum(1 for kw in complex_indicators if kw in task_lower) >= 3:
            return TaskDifficulty.MEDIUM
        return TaskDifficulty.EASY

    def select_model(self, task: str) -> ModelProfile:
        """เลือกโมเดลที่เหมาะสมกับงาน."""
        difficulty = self.classify_difficulty(task)
        candidates = [
            m for m in MODEL_PROFILES
            if self._is_available(m) and self._difficulty_ok(m, difficulty)
        ]
        if not candidates:
            candidates = MODEL_PROFILES[:]

        if self._prefer_free:
            free = [m for m in candidates if m.cost_per_token == 0.0]
            if free:
                candidates = free


        def score(m: ModelProfile) -> float:
            speed_w = 0.4 if difficulty.value in ("trivial", "easy") else 0.2
            quality_w = 0.6 if difficulty.value in ("hard", "expert") else 0.4
            cost_penalty = m.cost_per_token * 0.3
            return (m.speed_rating * speed_w + m.quality_rating * quality_w - cost_penalty)

        candidates.sort(key=score, reverse=True)
        chosen = candidates[0]
        self._history.append({
            "task": task[:100],
            "difficulty": difficulty.value,
            "model": chosen.name,
        })
        return chosen

    def _is_available(self, model: ModelProfile) -> bool:
        if self._available is None:
            return True
        return model.name in self._available

    def _difficulty_ok(self, model: ModelProfile, difficulty: TaskDifficulty) -> bool:
        order = list(TaskDifficulty)
        return order.index(difficulty) <= order.index(model.max_difficulty)

    def stats(self) -> dict[str, Any]:

        if not self._history:
            return {"total_routed": 0}
        models_used = {}
        difficulties = {}
        for h in self._history:
            models_used[h["model"]] = models_used.get(h["model"], 0) + 1
            difficulties[h["difficulty"]] = difficulties.get(h["difficulty"], 0) + 1
        return {
            "total_routed": len(self._history),
            "models_used": models_used,
            "difficulties": difficulties,
        }
