import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "ops" / "vps" / "services" / "cknexus_api_gateway.py"
)
SPEC = importlib.util.spec_from_file_location("cknexus_api_gateway_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_qwen_base_accepts_official_dashscope_endpoints():
    assert MODULE.validated_qwen_base("https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    assert MODULE.validated_qwen_base("https://tenant.maas.aliyuncs.com/compatible-mode/v1")


def test_qwen_base_rejects_untrusted_endpoints_and_credentials():
    for value in (
        "http://dashscope.aliyuncs.com/compatible-mode/v1",
        "https://attacker.example/compatible-mode/v1",
        "https://dashscope.aliyuncs.com.evil.example/compatible-mode/v1",
        "https://user:pass@dashscope.aliyuncs.com/compatible-mode/v1",
        "https://dashscope.aliyuncs.com/other-path",
        "https://dashscope.aliyuncs.com/compatible-mode/v1?redirect=evil",
    ):
        assert MODULE.validated_qwen_base(value) == ""
