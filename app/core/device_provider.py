from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote

import httpx

from app.core.devices import CATEGORY_DOC_MODEL, DEVICE_CATALOG

DEFAULT_KNOWLEDGE_MODELS: dict[str, str] = {
    "GX11": "compressor-002",
    "P-102X": "pump-004",
    "GMC-4000": "cnc-003",
}


class DeviceProviderError(Exception):
    """设备事实获取失败，status 直接作为诊断接口的降级状态。"""

    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class DeviceContext:
    device_id: str
    name: str
    type: str
    model: str
    location: str
    status: str
    knowledge_model: str | None
    organization_id: str | None = None


class DeviceProvider(Protocol):
    def get_device(self, device_id: str) -> DeviceContext:
        raise NotImplementedError

    def close(self) -> None:
        pass


class StaticDeviceProvider:
    """离线演示与单元测试使用的内置设备数据，不作为生产事实来源。"""

    def __init__(self) -> None:
        self._devices: dict[str, DeviceContext] = {}
        for device_id, info in DEVICE_CATALOG.items():
            self._devices[device_id] = DeviceContext(
                device_id=device_id,
                name=info.get("name", device_id),
                type=info.get("type", ""),
                model=info["model"],
                location=info.get("location", ""),
                status=info.get("status", "unknown"),
                knowledge_model=CATEGORY_DOC_MODEL.get(info["category"]),
            )

    def get_device(self, device_id: str) -> DeviceContext:
        device = self._devices.get(device_id)
        if device is None:
            raise DeviceProviderError(
                "device_not_found", f"未找到设备 {device_id} 的设备档案。"
            )
        return device

    def close(self) -> None:
        pass


class HttpDeviceProvider:
    """调用 B 包 GET /api/v1/devices/{device_id} 获取真实设备事实。"""

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        organization_id: str | None = None,
        user_id: str | None = None,
        timeout: float = 5.0,
        client: httpx.Client | None = None,
        knowledge_models: dict[str, str] | None = None,
    ):
        if not base_url:
            raise ValueError("DEVICE_API_BASE_URL 未配置")
        self.base_url = base_url.rstrip("/")
        self.organization_id = organization_id
        self._knowledge_models = _load_knowledge_models(knowledge_models)
        self._headers: dict[str, str] = {}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"
        if organization_id:
            self._headers["X-Organization-Id"] = organization_id
        if user_id:
            self._headers["X-User-Id"] = user_id
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)

    @property
    def client(self) -> httpx.Client:
        return self._client

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def get_device(self, device_id: str) -> DeviceContext:
        url = f"{self.base_url}/api/v1/devices/{quote(device_id, safe='')}"
        try:
            response = self._client.get(url, headers=self._headers)
        except httpx.TimeoutException as exc:
            raise DeviceProviderError(
                "device_unavailable", "设备服务调用超时，无法校验设备事实。"
            ) from exc
        except httpx.HTTPError as exc:
            raise DeviceProviderError(
                "device_unavailable", "设备服务不可用，无法校验设备事实。"
            ) from exc

        if response.status_code == 404:
            raise DeviceProviderError(
                "device_not_found", f"未找到设备 {device_id} 的设备档案。"
            )
        if response.status_code in (401, 403):
            raise DeviceProviderError(
                "device_unauthorized", "无权读取该设备档案，请检查登录组织与权限。"
            )
        if response.status_code != 200:
            raise DeviceProviderError(
                "device_unavailable",
                f"设备服务返回异常状态 {response.status_code}，无法校验设备事实。",
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise DeviceProviderError(
                "device_unavailable", "设备服务响应无法解析。"
            ) from exc
        if not isinstance(data, dict) or not data.get("id"):
            raise DeviceProviderError(
                "device_unavailable", "设备服务响应缺少设备编号。"
            )

        model = str(data.get("model") or "")
        return DeviceContext(
            device_id=str(data["id"]),
            name=str(data.get("name") or ""),
            type=str(data.get("type") or ""),
            model=model,
            location=str(data.get("location") or ""),
            status=str(data.get("state") or data.get("status") or "unknown"),
            knowledge_model=self._resolve_knowledge_model(data, model),
            organization_id=self.organization_id,
        )

    def _resolve_knowledge_model(self, data: dict, model: str) -> str | None:
        explicit = data.get("knowledgeModel")
        if isinstance(explicit, str) and explicit:
            return explicit
        return self._knowledge_models.get(model)


def _load_knowledge_models(overrides: dict[str, str] | None) -> dict[str, str]:
    mapping = dict(DEFAULT_KNOWLEDGE_MODELS)
    raw = os.getenv("DEVICE_KNOWLEDGE_MODELS", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("DEVICE_KNOWLEDGE_MODELS 必须是 JSON 对象") from exc
        if not isinstance(parsed, dict):
            raise ValueError("DEVICE_KNOWLEDGE_MODELS 必须是 JSON 对象")
        mapping.update({str(key): str(value) for key, value in parsed.items()})
    if overrides:
        mapping.update(overrides)
    return mapping


def build_device_provider() -> DeviceProvider:
    provider = os.getenv("DEVICE_PROVIDER", "static").strip().lower()
    if provider == "static":
        return StaticDeviceProvider()
    if provider == "http":
        return HttpDeviceProvider(
            base_url=os.getenv("DEVICE_API_BASE_URL", ""),
            token=os.getenv("DEVICE_API_TOKEN") or None,
            organization_id=os.getenv("DEVICE_ORG_ID") or None,
            user_id=os.getenv("DEVICE_USER_ID") or None,
            timeout=float(os.getenv("DEVICE_API_TIMEOUT", "5")),
        )
    raise ValueError(f"不支持的 DEVICE_PROVIDER: {provider}")
