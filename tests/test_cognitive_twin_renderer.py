pathlib = __import__("pathlib")

WEB = pathlib.Path(__file__).resolve().parents[1] / "creator_app" / "web"
RENDERER = WEB / "cognitive-twin-renderer.js"


def _read() -> str:
    return RENDERER.read_text(encoding="utf-8")


def test_renderer_asset_exists_and_is_presentation_only() -> None:
    assert RENDERER.is_file()
    js = _read()
    assert "CKNexusTwinRenderer" in js
    assert "normalizeProjectedState" in js
    assert "motionProfile" in js
    assert "fetch(" not in js
    assert "XMLHttpRequest" not in js
    assert "WebSocket(" not in js
    assert "EventSource(" not in js


def test_renderer_preserves_truth_boundary() -> None:
    js = _read()
    for truth in ("OBSERVED", "INFERRED", "SIMULATED", "VERIFIED"):
        assert truth in js
    assert 'state.truth === "VERIFIED" && !state.verified' in js
    assert 'return "OBSERVED"' in js


def test_renderer_has_fail_closed_capability_fallbacks() -> None:
    js = _read()
    assert 'this.mode = "css-fallback"' in js
    assert 'status("webgl-unavailable")' in js
    assert 'status("three-unavailable")' in js
    assert '"three-vrm"' in js
    assert '"three-basic"' in js
    assert "VRMLoaderPlugin" in js
    assert "THREE.GLTFLoader" in js


def test_renderer_motion_layers_are_bounded_and_reduced_motion_aware() -> None:
    js = _read()
    for layer in ("locomotion", "posture", "gesture", "face", "gaze", "micro"):
        assert layer in js
    assert "reducedMotion" in js
    assert "setReducedMotion" in js
    assert "locomotion: 0" in js


def test_renderer_consumes_projection_event_without_owning_runtime_transport() -> None:
    js = _read()
    assert 'PROJECTION_EVENT = "cknexus:projected-state"' in js
    assert "window.addEventListener(PROJECTION_EVENT" in js
    assert "renderer.consume(event && event.detail)" in js
    assert "mountProjectionBridge" in js


def test_renderer_does_not_create_runtime_authority_or_mutation_paths() -> None:
    js = _read()
    forbidden = (
        "/api/agnes/execute",
        "/api/agnes/pipeline/start",
        "Authorization:",
        "OPENAI_API_KEY",
        "production_mutation",
        'method: "POST"',
        "localStorage",
        "sessionStorage",
    )
    for value in forbidden:
        assert value not in js
