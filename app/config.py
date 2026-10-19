from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEMO_DOCS_DIR = DATA_DIR / "demo_docs"
STORAGE_PATH = DATA_DIR / "knowledge_base.json"
