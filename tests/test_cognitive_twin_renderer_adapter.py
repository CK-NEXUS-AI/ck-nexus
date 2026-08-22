pathlib = __import__("pathlib")

WEB = pathlib.Path(__file__).resolve().parents[1] / "creator_app" / "web"
RENDERER = WEB / "cognitive-twin-renderer.js"


def _read() -> str:
    return RENDERER.read_text(encoding="utf-8")


def test_renderer_adapter_asset_exists() -> None:
    assert RENDERER.is_file()


def test_renderer_adapter_is_presentation_only_and_fail_safe() -> None:
    js = _read()
    assert 'authority: "presentation-only"' in js
    assert 'mode = "css-fallback"' in js
    assert 'mode = "three-presentation"' in js
    assert "three_runtime_unavailable" in js
    assert "private_data_forbidden" in js


def test_renderer_adapter_preserves_truth_classes() -> None:
    js = _read()
    for truth in ("OBSERVED", "INFERRED", "SIMULATED", "VERIFIED"):
        assert truth in js
    assert "truth_class_invalid" in js
    assert "validateProjection" in js


def test_renderer_adapter_has_no_runtime_mutation_or_credentials() -> None:
    js = _read()
    forbidden = (
        "/api/agnes/execute",
        "/api/agnes/pipeline/start",
        "/api/integrations/github-app/token",
        "OPENAI_API_KEY",
        "raw_credentials =",
        'method: "POST"',
        "method: 'POST'",
    )
    for value in forbidden:
        assert value not in js


def test_renderer_adapter_supports_optional_three_vrm_glb_runtime() -> None:
    js = _read()
    assert "window.THREE" in js
    assert "window.GLTFLoader" in js
    assert "window.VRMLoaderPlugin" in js
    assert "THREE.WebGLRenderer" in js
    assert "THREE.CapsuleGeometry" in js


def test_renderer_adapter_has_visibility_lod_and_motion_governors() -> None:
    js = _read()
    assert 'document.addEventListener("visibilitychange"' in js
    assert "setLod(mode)" in js
    assert "setMotion(motion)" in js
    for layer in ("locomotion", "posture", "gesture", "face", "gaze", "microMotion"):
        assert layer in js


def test_renderer_adapter_does_not_load_external_dependencies() -> None:
    js = _read()
    assert "https://" not in js
    assert "http://" not in js
    assert "import(" not in js
    assert "fetch(" not in js
