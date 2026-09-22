"""Филаменты и диаметры сопел из установленной Cura 5.10.

У филамента берутся температуры, стол, обдув и диаметр прутка.
Ретракт не копируется: на этом Bowden он уже подобран отдельно.
Сопло — уникальный диаметр и ширины линий, без стартового кода.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

CURA = Path(r"C:\Program Files\UltiMaker Cura 5.10.0\share\cura\resources")
MATERIALS = CURA / "materials"
VARIANTS = CURA / "variants"

_MATERIALS: list[dict] | None = None
_NOZZLES: list[dict] | None = None

SETTING_MAP = {
    "print temperature": "material_print_temperature",
    "heated bed temperature": "material_bed_temperature",
    "print cooling": "cool_fan_speed",
}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _stem_id(stem: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", stem)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned or not cleaned[0].isalnum():
        cleaned = "m_" + cleaned
    return cleaned[:81]


def _float(text: str | None) -> float | None:
    if text is None:
        return None
    try:
        return float(str(text).strip())
    except ValueError:
        return None


def _material_files() -> list[Path]:
    return sorted(MATERIALS.glob("*.xml.fdm_material"))


def _parse_material(path: Path) -> dict | None:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return None
    brand = material = color = label = ""
    diameter = None
    raw_settings: dict[str, str] = {}
    for node in root:
        name = _local(node.tag)
        if name == "metadata":
            for child in node:
                if _local(child.tag) != "name":
                    continue
                for part in child:
                    key = _local(part.tag)
                    if key == "brand":
                        brand = (part.text or "").strip()
                    elif key == "material":
                        material = (part.text or "").strip()
                    elif key == "color":
                        color = (part.text or "").strip()
                    elif key == "label":
                        label = (part.text or "").strip()
        elif name == "properties":
            for child in node:
                if _local(child.tag) == "diameter":
                    diameter = _float(child.text)
        elif name == "settings":
            for child in node:
                if _local(child.tag) != "setting":
                    continue
                key = child.attrib.get("key") or ""
                if key in SETTING_MAP and child.text:
                    raw_settings[key] = child.text.strip()
    title = label or " ".join(part for part in (brand, material, color) if part)
    if not title:
        return None
    stem = path.name[: -len(".xml.fdm_material")]
    return {
        "id": _stem_id(stem),
        "name": title,
        "brand": brand,
        "material": material,
        "diameter": diameter,
        "raw": raw_settings,
    }


def list_materials() -> list[dict]:
    global _MATERIALS
    if _MATERIALS is None:
        items = []
        for path in _material_files():
            parsed = _parse_material(path)
            if parsed:
                items.append({key: value for key, value in parsed.items() if key != "raw"})
        items.sort(key=lambda item: (item["name"].lower(), item["id"]))
        _MATERIALS = items
    return _MATERIALS


def import_material(stem_id: str) -> dict:
    found = None
    for path in _material_files():
        parsed = _parse_material(path)
        if parsed and parsed["id"] == stem_id:
            found = parsed
            break
    if not found:
        raise ValueError("филамент не найден в каталоге Cura")
    settings: dict[str, object] = {}
    for src, dst in SETTING_MAP.items():
        value = _float(found["raw"].get(src))
        if value is None:
            continue
        settings[dst] = value
    if "cool_fan_speed" in settings:
        settings["cool_fan_enabled"] = settings["cool_fan_speed"] > 0
    if found["diameter"] is not None:
        settings["material_diameter"] = found["diameter"]
    if "material_print_temperature" not in settings and "material_bed_temperature" not in settings:
        raise ValueError("в файле нет температур сопла или стола")
    diameter = found["diameter"]
    wrong_diameter = diameter is not None and abs(diameter - 1.75) > 0.05
    warn = "Из каталога Cura, на этом столе не проверено. Ретракт не скопирован."
    if wrong_diameter:
        warn = f"В файле пруток {diameter:g} мм, на этой машине 1.75. На слайс не отправлять, пока катушка не совпадёт. Ретракт не скопирован."
    return {
        "id": found["id"],
        "title": found["name"],
        "kind": "filament",
        "verified": False,
        "warn": warn,
        "note": "Температуры, стол и обдув из материала Cura. Ретракт этой машины не брался.",
        "source": f"cura-material:{found['id']}",
        "settings": settings,
    }


def list_nozzles() -> list[dict]:
    global _NOZZLES
    if _NOZZLES is not None:
        return _NOZZLES
    sizes: set[float] = set()
    if VARIANTS.is_dir():
        for path in VARIANTS.rglob("*.inst.cfg"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "hardware_type = nozzle" not in text:
                continue
            match = re.search(r"^machine_nozzle_size\s*=\s*([0-9.]+)", text, re.M)
            if not match:
                continue
            mm = round(float(match.group(1)), 2)
            if 0.1 <= mm <= 2:
                sizes.add(mm)
    items = []
    for mm in sorted(sizes):
        code = f"{int(round(mm * 100)):03d}"
        items.append({"id": f"d{code}", "name": f"Сопло {mm:g} мм", "nozzle_mm": mm})
    _NOZZLES = items
    return items


def import_nozzle(nozzle_id: str) -> dict:
    found = next((item for item in list_nozzles() if item["id"] == nozzle_id), None)
    if not found:
        raise ValueError("такого диаметра нет среди сопел Cura")
    mm = float(found["nozzle_mm"])
    if mm >= 0.4:
        layer, first = 0.2, 0.3
    else:
        layer = round(mm * 0.5, 2)
        first = round(mm * 0.75, 2)
    widths = {
        "machine_nozzle_size": mm,
        "line_width": mm,
        "wall_line_width": mm,
        "wall_line_width_0": mm,
        "wall_line_width_x": mm,
        "skin_line_width": mm,
        "infill_line_width": mm,
        "layer_height": layer,
        "layer_height_0": first,
    }
    warn = ""
    if abs(mm - 0.6) > 0.01:
        warn = "Сейчас в HARDWARE сопло 0.6. Этот набор на слайс не отправлять."
    return {
        "id": found["id"],
        "title": found["name"],
        "kind": "nozzle",
        "nozzle_mm": mm,
        "verified": False,
        "warn": warn,
        "note": "Диаметр из вариантов Cura. Ширины линий равны соплу. Стартовый код и ретракт не меняются.",
        "source": f"cura-nozzle:{found['id']}",
        "settings": widths,
    }
