from creator_app.control_plane.fast_cache import ReadOnlyTTLCache


def test_cache_hits_inside_ttl_and_misses_after_ttl() -> None:
    now = [100.0]
    cache = ReadOnlyTTLCache(ttl_seconds=5.0, clock=lambda: now[0])
    cache.put("health", {"status": "ok"})
    assert cache.get("health") == {"status": "ok"}
    now[0] = 105.1
    assert cache.get("health") is None


def test_invalidate_removes_entry() -> None:
    cache = ReadOnlyTTLCache()
    cache.put("health", "ok")
    cache.invalidate("health")
    assert cache.get("health") is None


def test_non_cacheable_values_are_not_stored() -> None:
    cache = ReadOnlyTTLCache()
    cache.put("mutation", {"status": "changed"}, cacheable=False)
    assert cache.get("mutation") is None
