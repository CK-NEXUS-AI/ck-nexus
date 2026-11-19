from creator_app.creator_intelligence import get_mode, list_modes


def test_slash_aliases_are_ck_nexus_modes() -> None:
    assert get_mode("/expert").id == "expert"
    assert get_mode("/geo").id == "ai-search"
    assert get_mode("/viral").id == "creator"


def test_research_modes_require_sources() -> None:
    assert get_mode("research").requires_sources is True
    assert get_mode("seo").requires_sources is True
    assert get_mode("privacy-check").requires_sources is True


def test_modes_do_not_publish_externally() -> None:
    assert all(mode.allows_external_publish is False for mode in list_modes())


def test_unknown_mode_fails_closed() -> None:
    try:
        get_mode("/not-a-real-mode")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown mode must fail closed")
