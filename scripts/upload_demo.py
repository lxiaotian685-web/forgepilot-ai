from __future__ import annotations

import os
from pathlib import Path

import httpx

from app.config import default_organization_id

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT / "data" / "demo_uploads"

DEMO_UPLOADS = [
    (
        "ac07_upload_demo.txt",
        "AC-07 现场维护补充说明（演示上传）",
        "compressor-002",
    )
]


def main() -> None:
    base_url = os.getenv("C_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    headers = {"X-Organization-Id": default_organization_id()}
    token = os.getenv("C_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(timeout=30) as client:
        for filename, title, model in DEMO_UPLOADS:
            path = UPLOAD_DIR / filename
            if not path.exists():
                print(f"跳过不存在文件: {path}")
                continue
            with path.open("rb") as handle:
                response = client.post(
                    f"{base_url}/api/v1/documents/upload",
                    headers=headers,
                    data={
                        "title": title,
                        "equipment_model": model,
                        "version": "1.0",
                        "source": filename,
                    },
                    files={"file": (filename, handle, "text/plain")},
                )
            print(f"{filename}: HTTP {response.status_code}")
            print(response.text)
            response.raise_for_status()


if __name__ == "__main__":
    main()
