from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "raw_data.json"


def load_sample_works() -> List[Dict[str, Any]]:
    """Load the bundled sample dataset to emulate BrCris/Oasisbr/BDTD endpoints."""
    if not DATA_PATH.exists():
        return []
    with open(DATA_PATH, encoding="utf-8") as handle:
        payload = json.load(handle)
    works = payload.get("works") or []
    return works.copy()


def extract_authors(entry: Dict[str, Any]) -> List[str]:
    authors = []
    for raw in entry.get("autores") or []:
        if isinstance(raw, dict):
            name = raw.get("nome") or raw.get("name")
        else:
            name = str(raw)
        if name:
            authors.append(name)
    return authors
