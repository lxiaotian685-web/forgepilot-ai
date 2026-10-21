import httpx
import pytest

from app.core.device_provider import (
    DeviceProviderError,
    HttpDeviceProvider,
    StaticDeviceProvider,
    build_device_provider,
)


def _payload(**overrides) -> dict:
    data = {
        "id": "AC-07",
        "name": "螺杆空气压缩机",
        "type": "动力与流体机械",
        "model": "GX11",
        "location": "压缩站 Bay03",
        "state": "attention",
    }
    data.update(overrides)
    return data


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_static_provider_returns_device_facts():
    device = StaticDeviceProvider().get_device("AC-07")

    assert device.device_id == "AC-07"
    assert device.name == "螺杆空气压缩机"
    assert device.type == "动力与流体机械"
    assert device.model == "GX11"
    assert device.location == "压缩站 Bay03"
    assert device.status == "attention"
    assert device.knowledge_model == "compressor-002"


def test_static_provider_unknown_device():
    with pytest.raises(DeviceProviderError) as raised:
        StaticDeviceProvider().get_device("UNKNOWN-99")

    assert raised.value.status == "device_not_found"


def test_http_provider_maps_b_fields_and_identity_headers():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("authorization")
        captured["organization"] = request.headers.get("x-organization-id")
        captured["user"] = request.headers.get("x-user-id")
        return httpx.Response(200, json=_payload())

    provider = HttpDeviceProvider(
        base_url="http://business-api",
        token="token",
        organization_id="demo-org",
        user_id="technician@example.com",
        client=_client(handler),
    )

    device = provider.get_device("AC-07")

    assert captured["url"].endswith("/api/v1/devices/AC-07")
    assert captured["authorization"] == "Bearer token"
    assert captured["organization"] == "demo-org"
    assert captured["user"] == "technician@example.com"
    assert device.device_id == "AC-07"
    assert device.status == "attention"
    assert device.knowledge_model == "compressor-002"
    assert device.organization_id == "demo-org"


def test_http_provider_accepts_explicit_knowledge_model():
    def handler(request):
        return httpx.Response(200, json=_payload(knowledgeModel="compressor-002"))

    provider = HttpDeviceProvider(
        base_url="http://business-api", client=_client(handler)
    )

    assert provider.get_device("AC-07").knowledge_model == "compressor-002"


def test_http_provider_unknown_model_has_no_knowledge():
    def handler(request):
        return httpx.Response(200, json=_payload(model="NEW-MODEL"))

    provider = HttpDeviceProvider(
        base_url="http://business-api", client=_client(handler)
    )

    assert provider.get_device("AC-07").knowledge_model is None


def test_http_provider_knowledge_model_env_override(monkeypatch):
    monkeypatch.setenv("DEVICE_KNOWLEDGE_MODELS", '{"NEW-MODEL": "compressor-002"}')

    def handler(request):
        return httpx.Response(200, json=_payload(model="NEW-MODEL"))

    provider = HttpDeviceProvider(
        base_url="http://business-api", client=_client(handler)
    )

    assert provider.get_device("AC-07").knowledge_model == "compressor-002"


def test_http_provider_missing_device_is_404():
    def handler(request):
        return httpx.Response(404, json={"error": {}})

    provider = HttpDeviceProvider(
        base_url="http://business-api", client=_client(handler)
    )

    with pytest.raises(DeviceProviderError) as raised:
        provider.get_device("AC-07")

    assert raised.value.status == "device_not_found"


def test_http_provider_unauthorized_is_not_leaked():
    def handler(request):
        return httpx.Response(403, json={"error": {}})

    provider = HttpDeviceProvider(
        base_url="http://business-api", client=_client(handler)
    )

    with pytest.raises(DeviceProviderError) as raised:
        provider.get_device("AC-07")

    assert raised.value.status == "device_unauthorized"


def test_http_provider_server_error_is_unavailable():
    def handler(request):
        return httpx.Response(500, text="boom")

    provider = HttpDeviceProvider(
        base_url="http://business-api", client=_client(handler)
    )

    with pytest.raises(DeviceProviderError) as raised:
        provider.get_device("AC-07")

    assert raised.value.status == "device_unavailable"


def test_http_provider_timeout_is_unavailable():
    def handler(request):
        raise httpx.TimeoutException("timeout")

    provider = HttpDeviceProvider(
        base_url="http://business-api", client=_client(handler)
    )

    with pytest.raises(DeviceProviderError) as raised:
        provider.get_device("AC-07")

    assert raised.value.status == "device_unavailable"


def test_http_provider_invalid_json_is_unavailable():
    def handler(request):
        return httpx.Response(200, text="not json")

    provider = HttpDeviceProvider(
        base_url="http://business-api", client=_client(handler)
    )

    with pytest.raises(DeviceProviderError) as raised:
        provider.get_device("AC-07")

    assert raised.value.status == "device_unavailable"


def test_http_provider_reuses_client():
    count = {"n": 0}

    def handler(request):
        count["n"] += 1
        return httpx.Response(200, json=_payload())

    provider = HttpDeviceProvider(
        base_url="http://business-api", client=_client(handler)
    )

    assert provider.client is provider.client
    provider.get_device("AC-07")
    provider.get_device("AC-07")
    assert count["n"] == 2


def test_build_device_provider_defaults_to_static(monkeypatch):
    monkeypatch.delenv("DEVICE_PROVIDER", raising=False)

    provider = build_device_provider()

    assert isinstance(provider, StaticDeviceProvider)


def test_build_device_provider_builds_http_from_env(monkeypatch):
    monkeypatch.setenv("DEVICE_PROVIDER", "http")
    monkeypatch.setenv("DEVICE_API_BASE_URL", "http://business-api")

    provider = build_device_provider()

    assert isinstance(provider, HttpDeviceProvider)
    provider.close()


def test_build_device_provider_rejects_unknown_value(monkeypatch):
    monkeypatch.setenv("DEVICE_PROVIDER", "unknown")

    with pytest.raises(ValueError):
        build_device_provider()
