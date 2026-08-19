"""Tests สำหรับ Intelligence Modules ทั้ง 5."""

from __future__ import annotations

import asyncio

from creator_app.ai_team.intelligence.auto_model_router import AutoModelRouter, TaskDifficulty
from creator_app.ai_team.intelligence.multi_perspective import MultiPerspectiveThinker
from creator_app.ai_team.intelligence.parallel_executor import ParallelExecutor, TaskStatus
from creator_app.ai_team.intelligence.self_correction import SelfCorrectionLoop
from creator_app.ai_team.intelligence.semantic_memory import SemanticMemory
from creator_app.ai_team.intelligence.smart_cache import SmartCache

# ═══ SmartCache ═══

class TestSmartCache:
    def test_exact_cache_hit(self):
        cache = SmartCache()
        cache.set("สรุปอีเมล", "มี 3 ฉบับ", tags=("email",))
        result = cache.get("สรุปอีเมล")
        assert result is not None
        assert result.response == "มี 3 ฉบับ"

    def test_exact_cache_miss(self):
        cache = SmartCache()
        result = cache.get("ไม่มีในแคช")
        assert result is None

    def test_semantic_cache_hit(self):
        cache = SmartCache(similarity_threshold=0.3)
        cache.set("สรุปอีเมลล่าสุด 3 ฉบับ", "มี 3 ฉบับ")
        result = cache.get("สรุปอีเมลล่าสุด 5 ฉบับ")
        assert result is not None

    def test_cache_invalidation(self):
        cache = SmartCache()
        cache.set("test", "value")
        assert cache.invalidate("test")
        assert cache.get("test") is None

    def test_cache_stats(self):
        cache = SmartCache()
        cache.set("q1", "a1")
        cache.get("q1")
        cache.get("q2")
        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_entries_exact"] == 1

    def test_cache_clear(self):
        cache = SmartCache()
        cache.set("q", "a")
        cache.clear()
        assert cache.get("q") is None

    def test_cache_eviction(self):
        cache = SmartCache(max_size=3)
        for i in range(5):
            cache.set(f"q{i}", f"a{i}")
        assert cache.stats["total_entries_exact"] <= 3


# ═══ ParallelExecutor ═══

class TestParallelExecutor:
    def test_run_batch(self):
        executor = ParallelExecutor(max_concurrency=3)

        async def task_a():
            return "a"

        async def task_b():
            return "b"

        async def _run():
            return await executor.run_batch("test", [("a", task_a), ("b", task_b)])

        results = asyncio.run(_run())
        assert len(results) == 2
        assert all(r.status == TaskStatus.COMPLETED for r in results)

    def test_run_batch_with_timeout(self):
        executor = ParallelExecutor()

        async def slow():
            await asyncio.sleep(10)
            return "slow"

        async def _run():
            return await executor.run_batch("timeout-test", [("slow", slow)], timeout=0.1)

        results = asyncio.run(_run())
        assert results[0].status == TaskStatus.FAILED

    def test_run_batch_with_fallback(self):
        executor = ParallelExecutor()

        async def failing():
            raise ValueError("boom")

        def fallback(task_id, exc):
            return f"fallback for {task_id}"

        async def _run():
            return await executor.run_batch(
                "fb-test", [("fail", failing)], fallback=fallback,
            )

        results = asyncio.run(_run())
        assert results[0].status == TaskStatus.COMPLETED
        assert results[0].result == "fallback for fail"

    def test_run_sequential(self):
        executor = ParallelExecutor()

        async def task1():
            return 1

        async def task2():
            return 2

        async def _run():
            return await executor.run_sequential([("t1", task1), ("t2", task2)])

        results = asyncio.run(_run())
        assert len(results) == 2
        assert results[0].result == 1
        assert results[1].result == 2

    def test_stats(self):
        executor = ParallelExecutor()

        async def ok():
            return "ok"

        async def _run():
            return await executor.run_batch("s", [("ok", ok)])

        asyncio.run(_run())
        stats = executor.stats()
        assert stats["total_tasks"] == 1
        assert stats["completed"] == 1


# ═══ AutoModelRouter ═══

class TestAutoModelRouter:
    def test_classify_trivial(self):
        router = AutoModelRouter()
        assert router.classify_difficulty("x") == TaskDifficulty.TRIVIAL

    def test_classify_easy(self):
        router = AutoModelRouter()
        assert router.classify_difficulty("translate language") == TaskDifficulty.EASY

    def test_classify_hard(self):
        router = AutoModelRouter()
        assert router.classify_difficulty("deep analysis security audit") == TaskDifficulty.HARD

    def test_select_model_easy(self):
        router = AutoModelRouter(prefer_free=True)
        model = router.select_model("hello")
        assert model.cost_per_token == 0.0

    def test_select_model_hard(self):
        router = AutoModelRouter(prefer_free=False)
        model = router.select_model("deep analysis security audit architecture design system")
        assert model.quality_rating >= 8

    def test_stats(self):
        router = AutoModelRouter()
        router.select_model("hello")
        stats = router.stats()
        assert stats["total_routed"] == 1


# ═══ SelfCorrectionLoop ═══

class TestSelfCorrectionLoop:
    def test_verify_confident_response(self):
        sc = SelfCorrectionLoop(min_confidence=0.5)
        response = (
            "create OAuth2 system with JWT authentication"
            " and role-based access control"
        )
        result = sc.verify("create system", response)
        assert result.passes

    def test_verify_uncertain_response(self):
        sc = SelfCorrectionLoop(min_confidence=0.5)
        result = sc.verify(
            "how does it work",
            "maybe it works perhaps i think possibly somehow im not sure probably idk",
        )
        assert not result.passes

    def test_refine(self):
        sc = SelfCorrectionLoop()
        refined = sc.refine("maybe it works perhaps", ["reduce hedge words"])
        assert len(refined) <= len("maybe it works perhaps")

    def test_stats(self):
        sc = SelfCorrectionLoop()
        sc.verify("q", "a" * 100)
        stats = sc.stats
        assert stats["total_verified"] == 1


# ═══ MultiPerspectiveThinker ═══

class TestMultiPerspectiveThinker:
    def test_analyze(self):
        thinker = MultiPerspectiveThinker()
        analysis = thinker.analyze("create payment system")
        assert len(analysis.perspectives) == 4
        assert analysis.overall_risk in ("low", "medium", "high")

    def test_security_focused(self):
        thinker = MultiPerspectiveThinker()
        analysis = thinker.analyze("create auth token encryption security system")
        sec = [p for p in analysis.perspectives if p.name == "Security"]
        assert len(sec) == 1
        assert sec[0].risk_level == "high"

    def test_history(self):
        thinker = MultiPerspectiveThinker()
        thinker.analyze("task 1")
        thinker.analyze("task 2")
        assert len(thinker.history) == 2

    def test_stats(self):
        thinker = MultiPerspectiveThinker()
        thinker.analyze("task 1")
        stats = thinker.stats()
        assert stats["total_analyzed"] == 1


# ═══ SemanticMemory ═══

class TestSemanticMemory:
    def test_store_and_recall(self):
        mem = SemanticMemory()
        mem.store("CK-NEXUS uses Evidence-First principle", "principle", importance=0.9)
        results = mem.recall("CK-NEXUS Evidence")
        assert len(results) > 0
        assert "CK-NEXUS" in results[0].content

    def test_recall_by_category(self):
        mem = SemanticMemory()
        mem.store("repo is on GitHub", "knowledge")
        mem.store("CI uses Ruff", "tool")
        results = mem.recall("CI", category="tool")
        assert all(r.category == "tool" for r in results)

    def test_store_experience(self):
        mem = SemanticMemory()
        idx = mem.store_experience("push to GitHub", "success", success=True)
        assert idx >= 0
        results = mem.recall("push GitHub")
        assert len(results) > 0

    def test_suggest_related(self):
        mem = SemanticMemory()
        mem.store("Python is great for scripting", "knowledge")
        mem.store("JavaScript is great for web", "knowledge")
        suggestions = mem.suggest_related("Python scripting")
        assert len(suggestions) >= 1

    def test_stats(self):
        mem = SemanticMemory()
        mem.store("test content", "test", importance=0.5)
        stats = mem.stats()
        assert stats["total_memories"] == 1

    def test_eviction(self):
        mem = SemanticMemory(max_size=5)
        for i in range(10):
            mem.store(f"content {i}", "test")
        assert len([e for e in mem._memories if e.category != "__deleted__"]) <= 5


# ═══ EnhancedUniversalSystem ═══

class TestEnhancedUniversalSystem:
    def test_process(self):
        from creator_app.ai_team.universal_system import EnhancedUniversalSystem
        system = EnhancedUniversalSystem()
        result = system.process("create system")
        assert "Intelligence Stats" in result

    def test_process_cache_hit(self):
        from creator_app.ai_team.universal_system import EnhancedUniversalSystem
        system = EnhancedUniversalSystem()
        system.process("create system")
        result2 = system.process("create system")
        assert "Cache Hit" in result2

    def test_stats(self):
        from creator_app.ai_team.universal_system import EnhancedUniversalSystem
        system = EnhancedUniversalSystem()
        system.process("test")
        stats = system.stats()
        assert "features_enabled" in stats
        assert stats["features_enabled"]["cache"] is True

    def test_process_with_all_disabled(self):
        from creator_app.ai_team.universal_system import EnhancedUniversalSystem
        system = EnhancedUniversalSystem(
            enable_cache=False, enable_parallel=False,
            enable_auto_route=False, enable_self_correction=False,
            enable_perspective=False, enable_memory=False,
        )
        result = system.process("create system")
        assert "Intelligence Stats" in result
