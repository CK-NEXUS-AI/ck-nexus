from creator_app.connector_fabric.mcp import MCP_PROTOCOL_VERSION
from creator_app.connector_fabric.models import (
    ConnectorConfig,
    ConnectorProtocol,
    DiscoverySnapshot,
)


def test_connector_config_public_dict_keeps_url():
    config = ConnectorConfig(
        connector_id="demo",
        url="https://example.com/mcp",
        protocol=ConnectorProtocol.MCP,
    )
    assert config.public_dict()["url"] == "https://example.com/mcp"


def test_discovery_snapshot_serializes_without_phantom_url_field():
    snapshot = DiscoverySnapshot(
        connector_id="demo",
        protocol=ConnectorProtocol.MCP,
        protocol_version=MCP_PROTOCOL_VERSION,
        tools=(),
    )
    payload = snapshot.as_dict()
    assert payload["connectorId"] == "demo"
    assert payload["protocol"] == "mcp"
    assert "url" not in payload
