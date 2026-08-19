"""Intelligence Layer — สมองความคิดของ CK-NEXUS.

รวม:
- SmartCache: แคช 2 ชั้น (memory + disk)
- ParallelExecutor: รันหลายงานพร้อมกัน
- AutoModelRouter: เลือกโมเดลอัตโนมัติ
- SelfCorrectionLoop: ตรวจสอบก่อนส่ง
- MultiPerspectiveThinker: คิดหลายมุมมอง
- SemanticMemory: ความจำเชิงความหมาย
- ReflexionEngine: สะท้อนคิดและเรียนรู้จากความผิดพลาด
- ComputerUseAgent: ควบคุม GUI เหมือนมนุษย์
- BackgroundExecutor: ทำงานเบื้องหลังอัตโนมัติ
- MCPHubExtended: เชื่อมทุกแอพผ่าน MCP
"""

from creator_app.ai_team.intelligence.smart_cache import SmartCache
from creator_app.ai_team.intelligence.parallel_executor import ParallelExecutor
from creator_app.ai_team.intelligence.auto_model_router import AutoModelRouter
from creator_app.ai_team.intelligence.self_correction import SelfCorrectionLoop
from creator_app.ai_team.intelligence.multi_perspective import MultiPerspectiveThinker
from creator_app.ai_team.intelligence.semantic_memory import SemanticMemory
from creator_app.ai_team.intelligence.reflexion import ReflexionEngine
from creator_app.ai_team.intelligence.computer_use import ComputerUseAgent
from creator_app.ai_team.intelligence.background_executor import BackgroundExecutor
from creator_app.ai_team.intelligence.mcp_hub_extended import MCPHubExtended

__all__ = [
    "SmartCache",
    "ParallelExecutor",
    "AutoModelRouter",
    "SelfCorrectionLoop",
    "MultiPerspectiveThinker",
    "SemanticMemory",
    "ReflexionEngine",
    "ComputerUseAgent",
    "BackgroundExecutor",
    "MCPHubExtended",
]
