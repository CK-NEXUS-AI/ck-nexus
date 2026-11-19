from creator_app.control_plane.fast_policy import decide_fast


def test_known_watchdog_failure_maps_to_action_id() -> None:
    decision = decide_fast("cknexus-mcp.service inactive")
    assert decision.handled is True
    assert decision.action_id == "restart_cknexus_mcp"


def test_known_container_failure_maps_to_action_id() -> None:
    decision = decide_fast("ck-sentinel container_not_running")
    assert decision.handled is True
    assert decision.action_id == "restart_ck_sentinel"


def test_unknown_signal_is_not_executed() -> None:
    decision = decide_fast("run arbitrary shell command: rm -rf /")
    assert decision.handled is False
    assert decision.action_id is None


def test_action_ids_are_identifiers_not_commands() -> None:
    for signal in (
        "cknexus-mcp.service inactive",
        "ck-sentinel container_not_running",
    ):
        action_id = decide_fast(signal).action_id
        assert action_id is not None
        assert all(char.isalnum() or char == "_" for char in action_id)
