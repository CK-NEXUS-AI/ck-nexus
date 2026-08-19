"""Research Intelligence — ค้นหา + อ่าน + วิเคราะห์ จากทุกเว็บ.

รวม:
- SearchEngine: ค้นหาจาก 6 search engines
- ContentReader: อ่านเนื้อหาเว็บ + สรุป
- IdeaScraper: ดึงไอเดียจากหลายแหล่ง
- SolutionManager: เครื่องมือแก้ข้อจำกัดทางเทคนิค
- IdeasExpanded: แนวคิดขยาย 78 เครื่องมือ ใน 12 หมวดหมู่
"""

from creator_app.anyclaw.research.content_reader import ContentReader
from creator_app.anyclaw.research.idea_scraper import IdeaScraper
from creator_app.anyclaw.research.search_engine import SearchEngine
from creator_app.anyclaw.research.solutions import SolutionManager
from creator_app.anyclaw.research.ideas_expanded import (
    IDEAS,
    Tool,
    get_by_category,
    get_free_no_key,
    get_all_categories,
    full_report as ideas_full_report,
)

__all__ = [
    "SearchEngine",
    "ContentReader",
    "IdeaScraper",
    "SolutionManager",
    "IDEAS",
    "Tool",
    "get_by_category",
    "get_free_no_key",
    "get_all_categories",
    "ideas_full_report",
]
