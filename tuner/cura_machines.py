"""Импорт видимых машин из установленной Cura 5.10.

Берутся только литералы: стол, стартовый код, ускорения, рывки, подачи, шаги/мм.
Ретракт, температуры и сопло не копируются. Формулы пропускаются.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CURA_DEFS = Path(r"C:\Program Files\UltiMaker Cura 5.10.0\share\cura\resources\definitions")

KEEP_EXACT = {
    "machine_width",
    "machine_depth",
    "machine_height",
    "machine_heated_bed",
    "machine_start_gcode",
    "machine_end_gcode",
    "machine_gcode_flavor",
    "machine_center_is_zero",
    "gantry_height",
    "machine_acceleration",
}
KEEP_PREFIXES = ("acceleration_", "jerk_", "machine_max_", "machine_steps_per_mm_")
_CACHE: list[dict] | None = None


def keep_key(key: str) -> bool:
    if key.startswith(("retraction_", "material_", "cool_")):
        return False
    return key in KEEP_EXACT or key.startswith(KEEP_PREFIXES)


def is_literal(value) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        text = value.strip()
        if not text or text[0] in "'\"":
            return False
        if any(token in text for token in (" if ", "extruderValues", "min(", "max(", " + ", " - ", " * ", " / ")):
            return False
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text):
            return False
        return True
    return False


def literal_of(node: dict):
    for slot in ("default_value", "value"):
        if slot in node and is_literal(node[slot]):
            return node[slot]
    return None


def load_def(stem: str) -> dict:
    path = CURA_DEFS / f"{stem}.def.json"
    if not path.is_file():
        raise FileNotFoundError(stem)
    return json.loads(path.read_text(encoding="utf-8"))


def manufacturer_of(stem: str) -> str:
    seen = set()
    current = stem
    while current and current not in seen:
        seen.add(current)
        data = load_def(current)
        meta = data.get("metadata") or {}
        if meta.get("manufacturer"):
            return meta["manufacturer"]
        current = data.get("inherits") or ""
    return ""


def resolve(stem: str) -> dict[str, object]:
    chain = []
    seen = set()
    current = stem
    while current and current not in seen:
        seen.add(current)
        chain.append(current)
        current = load_def(current).get("inherits") or ""
    settings: dict[str, object] = {}
    for item in reversed(chain):
        for key, node in (load_def(item).get("overrides") or {}).items():
            if not keep_key(key) or not isinstance(node, dict):
                continue
            value = literal_of(node)
            if value is not None:
                settings[key] = value
    return settings


def list_visible() -> list[dict]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    items = []
    if not CURA_DEFS.is_dir():
        _CACHE = []
        return _CACHE
    for path in CURA_DEFS.glob("*.def.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        meta = data.get("metadata") or {}
        if meta.get("visible") is not True:
            continue
        stem = path.name[: -len(".def.json")]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,80}", stem):
            continue
        items.append(
            {
                "id": stem,
                "name": data.get("name") or stem,
                "manufacturer": meta.get("manufacturer") or "",
            }
        )
    items.sort(key=lambda item: (item["name"].lower(), item["id"]))
    _CACHE = items
    return items


def import_card(stem: str) -> dict:
    if not any(item["id"] == stem for item in list_visible()):
        raise ValueError("машина не найдена среди видимых определений Cura")
    data = load_def(stem)
    meta = data.get("metadata") or {}
    return {
        "id": stem,
        "title": data.get("name") or stem,
        "kind": "machine",
        "manufacturer": manufacturer_of(stem),
        "source": f"cura:{stem}",
        "verified": False,
        "warn": "Импорт из Cura, на этом столе не проверен. Пока в HARDWARE стоит Tornado, на слайс не отправлять. Драйверы и направляющие в файле не описаны.",
        "note": "Числа и стартовый код взяты буквально из определения Cura. Ретракт, температуры и сопло не копировались.",
        "settings": resolve(stem),
    }
