"""Check required backend settings before a public deployment.

Run separately with each service's environment. Never prints secret values.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


def _url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def check_business(env: dict[str, str]) -> list[str]:
    errors = []
    if env.get("APP_ENV", "").lower() != "production":
        errors.append("APP_ENV 必须为 production")
    if not env.get("DATABASE_URL", "").startswith("postgresql+psycopg://"):
        errors.append("DATABASE_URL 必须是 PostgreSQL psycopg 连接串")
    if env.get("AUTH_MODE", "").lower() != "token":
        errors.append("AUTH_MODE 必须为 token")
    secret = env.get("AUTH_SECRET", "")
    if len(secret) < 32 or "change-me" in secret.lower():
        errors.append("AUTH_SECRET 必须是至少 32 字符的独立随机值")
    if not env.get("CORS_ORIGINS", "") or "*" in env.get("CORS_ORIGINS", ""):
        errors.append("CORS_ORIGINS 必须明确列出前端来源")
    if len(env.get("AGENT_AUDIT_KEY", "")) < 32:
        errors.append("AGENT_AUDIT_KEY 必须是至少 32 字符的随机值，并与知识服务一致")
    return errors


def check_knowledge(env: dict[str, str]) -> list[str]:
    errors = []
    if env.get("APP_ENV", "").lower() != "production":
        errors.append("APP_ENV 必须为 production")
    if env.get("LLM_PROVIDER", "").lower() != "openai":
        errors.append("LLM_PROVIDER 必须为 openai")
    for key in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        if not env.get(key):
            errors.append(f"{key} 必须配置")
    if env.get("LLM_BASE_URL") and not _url(env["LLM_BASE_URL"]):
        errors.append("LLM_BASE_URL 必须是有效 HTTP(S) 地址")
    if env.get("DEVICE_PROVIDER", "").lower() != "http":
        errors.append("DEVICE_PROVIDER 必须为 http")
    for key in ("DEVICE_API_BASE_URL", "BUSINESS_API_BASE_URL", "C_IDENTITY_API_BASE_URL"):
        if not _url(env.get(key, "")):
            errors.append(f"{key} 必须是有效 HTTP(S) 地址")
    if env.get("C_REQUIRE_AUTH", "").lower() != "true":
        errors.append("C_REQUIRE_AUTH 必须为 true")
    if len(env.get("AGENT_AUDIT_KEY", "")) < 32:
        errors.append("AGENT_AUDIT_KEY 必须是至少 32 字符的随机值，并与业务服务一致")
    storage = env.get("KNOWLEDGE_STORAGE_PATH", "")
    if not storage or not (Path(storage).is_absolute() or PurePosixPath(storage).is_absolute()):
        errors.append("KNOWLEDGE_STORAGE_PATH 必须指向持久化卷上的绝对文件路径")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=("business", "knowledge"))
    args = parser.parse_args()
    errors = (check_business if args.service == "business" else check_knowledge)(dict(os.environ))
    if errors:
        print(f"{args.service} 部署前检查未通过：")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"{args.service} 必填配置检查通过；仍需实际连接、迁移和接口验收。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
