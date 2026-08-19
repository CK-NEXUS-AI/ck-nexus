"""Multi-Perspective Thinker — คิดหลายมุมก่อนตอบ.

มองปัญหาจาก 4 มุม:
1. 🧠 Technical — มุมมองทางเทคนิค
2. 👤 User — มุมมองของผู้ใช้
3. 🛡️ Security — มุมมองความปลอดภัย
4. 💰 Business — มุมมองธุรกิจ

ทำให้คำตอบมีมิติมากกว่าการคิดมุมเดียว
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Perspective:
    """มุมมองหนึ่งมุม."""

    name: str
    icon: str
    analysis: str
    concerns: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    risk_level: str = "low"  # low, medium, high


@dataclass
class PerspectiveAnalysis:
    """ผลวิเคราะห์จากทุกมุม."""

    query: str
    perspectives: list[Perspective] = field(default_factory=list)
    synthesis: str = ""
    overall_risk: str = "low"
    recommendation: str = ""

    @property
    def summary(self) -> str:
        lines = [f"🔍 วิเคราะห์จาก {len(self.perspectives)} มุมมอง:"]
        for p in self.perspectives:
            lines.append(f"  {p.icon} {p.name}: {p.analysis[:80]}...")
        lines.append(f"\n📋 สรุป: {self.recommendation}")
        return "\n".join(lines)


class MultiPerspectiveThinker:
    """คิดหลายมุมก่อนตอบ — ทำให้คำตอบมีมิติมากขึ้น.

    วิธีใช้:
        thinker = MultiPerspectiveThinker()
        analysis = thinker.analyze("สร้างระบบชำระเงิน")
        print(analysis.summary)
    """

    _TECHNICAL_KEYWORDS = frozenset({
        "โค้ด", "code", "api", "database", "db", "server",
        "deploy", "architecture", "system", "ระบบ",
        "performance", " scalability", " latency",
    })

    _SECURITY_KEYWORDS = frozenset({
        "password", "auth", "token", "secret", "key",
        "加密", "encrypt", "decrypt", "firewall",
        "vulnerability", "security", "ปลอดภัย",
        "permission", "access", "privilege",
    })

    _USER_KEYWORDS = frozenset({
        "user", "ux", "ui", "interface", "หน้าจอ",
        "mobile", "responsive", "ease", "simple",
        "user-friendly", " intuitive",
    })

    _BUSINESS_KEYWORDS = frozenset({
        "cost", "price", "revenue", "roi", "profit",
        "market", "customer", "client", "user growth",
        "monetize", "subscription", "budget", "ต้นทุน",
    })

    def __init__(self) -> None:
        self._history: list[PerspectiveAnalysis] = []

    def analyze(self, query: str) -> PerspectiveAnalysis:
        """วิเคราะห์จากทุกมุมมอง."""
        query_lower = query.lower()
        perspectives: list[Perspective] = []

        # Technical perspective
        tech_score = sum(1 for kw in self._TECHNICAL_KEYWORDS if kw in query_lower)
        perspectives.append(Perspective(
            name="Technical",
            icon="🧠",
            analysis=self._technical_analysis(query, tech_score),
            concerns=self._technical_concerns(query),
            suggestions=self._technical_suggestions(query),
            risk_level="medium" if tech_score > 2 else "low",
        ))

        # Security perspective
        sec_score = sum(1 for kw in self._SECURITY_KEYWORDS if kw in query_lower)
        perspectives.append(Perspective(
            name="Security",
            icon="🛡️",
            analysis=self._security_analysis(query, sec_score),
            concerns=self._security_concerns(query),
            suggestions=self._security_suggestions(query),
            risk_level="high" if sec_score > 2 else "medium" if sec_score > 0 else "low",
        ))

        # User perspective
        user_score = sum(1 for kw in self._USER_KEYWORDS if kw in query_lower)
        perspectives.append(Perspective(
            name="User Experience",
            icon="👤",
            analysis=self._user_analysis(query, user_score),
            concerns=self._user_concerns(query),
            suggestions=self._user_suggestions(query),
        ))

        # Business perspective
        biz_score = sum(1 for kw in self._BUSINESS_KEYWORDS if kw in query_lower)
        perspectives.append(Perspective(
            name="Business",
            icon="💰",
            analysis=self._business_analysis(query, biz_score),
            concerns=self._business_concerns(query),
            suggestions=self._business_suggestions(query),
        ))

        risk_levels = {"low": 0, "medium": 1, "high": 2}
        max_risk = max(
            (risk_levels.get(p.risk_level, 0) for p in perspectives),
            default=0,
        )
        overall_risk = ["low", "medium", "high"][max_risk]

        synthesis = self._synthesize(perspectives, query)
        recommendation = self._recommend(perspectives, overall_risk)

        result = PerspectiveAnalysis(
            query=query,
            perspectives=perspectives,
            synthesis=synthesis,
            overall_risk=overall_risk,
            recommendation=recommendation,
        )
        self._history.append(result)
        return result

    def _technical_analysis(self, query: str, score: int) -> str:
        if score > 2:
            return "งานนี้มีความซับซ้อนทางเทคนิคสูง — ต้องออกแบบระบบให้ดี"
        if score > 0:
            return "มีองค์ประกอบทางเทคนิค — ตรวจสอบ dependencies"
        return "ไม่พบองค์ประกอบทางเทคนิคหลัก"

    def _technical_concerns(self, query: str) -> list[str]:
        concerns = []
        if any(kw in query.lower() for kw in ["scale", "many", "จำนวนมาก"]):
            concerns.append("ต้องรองรับปริมาณงานมาก")
        if any(kw in query.lower() for kw in ["real-time", "เรียลไทม์"]):
            concerns.append("ต้องการ latency ต่ำ")
        return concerns

    def _technical_suggestions(self, query: str) -> list[str]:
        return ["ใช้ async/await สำหรับ I/O-bound tasks", "เพิ่ม caching สำหรับผลลัพธ์ที่คำนวณซ้ำ"]

    def _security_analysis(self, query: str, score: int) -> str:
        if score > 2:
            return "⚠️ มีองค์ประกอบความปลอดภัยสูง — ต้องตรวจให้ละเอียด"
        if score > 0:
            return "มีองค์ประกอบที่เกี่ยวกับความปลอดภัย"
        return "ความเสี่ยงด้านความปลอดภัยต่ำ"

    def _security_concerns(self, query: str) -> list[str]:
        concerns = []
        if any(kw in query.lower() for kw in ["api", "key", "token", "secret"]):
            concerns.append("ต้องจัดการ secrets อย่างปลอดภัย")
        if any(kw in query.lower() for kw in ["user", "login", "auth"]):
            concerns.append("ต้องมี authentication/authorization")
        return concerns

    def _security_suggestions(self, query: str) -> list[str]:
        return ["ใช้ env vars สำหรับ secrets — ไม่ commit", "เพิ่ม rate limiting", "ใช้ HTTPS เท่านั้น"]

    def _user_analysis(self, query: str, score: int) -> str:
        if score > 2:
            return "เน้น UX/UI — ต้องใช้งานง่ายและเข้าใจได้ทันที"
        if score > 0:
            return "มีองค์ประกอบที่ต้อง考虑用户体验"
        return "ไม่พบข้อกำหนด UX เฉพาะ"

    def _user_concerns(self, query: str) -> list[str]:
        return ["ต้องรองรับทุกอุปกรณ์" if "mobile" in query.lower() else ""]

    def _user_suggestions(self, query: str) -> list[str]:
        return ["ทดสอบกับผู้ใช้จริง", "มี error message ที่เข้าใจง่าย"]

    def _business_analysis(self, query: str, score: int) -> str:
        if score > 2:
            return "มีผลกระทบทางธุรกิจสูง — ต้องคำนึงถึง ROI"
        if score > 0:
            return "มีองค์ประกอบทางธุรกิจที่ต้องพิจารณา"
        return "ไม่พบข้อกำหนดทางธุรกิจเฉพาะ"

    def _business_concerns(self, query: str) -> list[str]:
        return ["ต้องมีต้นทุนที่ควบคุมได้"]

    def _business_suggestions(self, query: str) -> list[str]:
        return ["เริ่มจาก MVP", "วัดผลก่อนขยาย"]

    def _synthesize(self, perspectives: list[Perspective], query: str) -> str:
        high_risk = [p for p in perspectives if p.risk_level == "high"]
        if high_risk:
            return f"⚠️ มี {len(high_risk)} มุมที่เสี่ยงสูง — ต้องให้ความสำคัญก่อน"
        return "ไม่มีมุมเสี่ยงสูง — สามารถดำเนินการได้"

    def _recommend(self, perspectives: list[Perspective], risk: str) -> str:
        if risk == "high":
            return "ทำ security review ก่อน implement"
        if risk == "medium":
            return "วางแผนให้ดี แล้วค่อย implement"
        return "เริ่มทำได้เลย — ไม่มีข้อจำกัดหลัก"

    @property
    def history(self) -> list[PerspectiveAnalysis]:
        return list(self._history)

    def stats(self) -> dict[str, Any]:
        if not self._history:
            return {"total_analyzed": 0}
        risks = {}
        for h in self._history:
            risks[h.overall_risk] = risks.get(h.overall_risk, 0) + 1
        return {"total_analyzed": len(self._history), "risk_distribution": risks}
