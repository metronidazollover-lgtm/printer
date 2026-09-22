"""Собрать tuner/fields.json из определения Cura 5.10.

Запуск из корня папки принтера:
  python tuner/build_fields.py
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from plain_hints import HINTS

CURA = Path(r"C:\Program Files\UltiMaker Cura 5.10.0\share\cura\resources")
OUT = Path(__file__).resolve().parent / "fields.json"

CATEGORIES = [
    ("resolution", "Качество"),
    ("shell", "Стенки"),
    ("top_bottom", "Верх и низ"),
    ("infill", "Заполнение"),
    ("material", "Материал"),
    ("speed", "Скорость"),
    ("travel", "Перемещения"),
    ("cooling", "Охлаждение"),
    ("support", "Поддержки"),
    ("platform_adhesion", "Прилипание к столу"),
    ("dual", "Несколько экструдеров"),
    ("meshfix", "Исправление сетки"),
    ("blackmagic", "Особые режимы"),
    ("experimental", "Эксперимент"),
    ("machine_settings", "Принтер"),
    ("ppr", "После обработки"),
    ("command_line_settings", "Служебные"),
]

READONLY = {
    "machine_start_gcode",
    "machine_end_gcode",
    "machine_width",
    "machine_depth",
    "machine_height",
}

UNITS = {
    "mm": "мм",
    "mm/s": "мм/с",
    "mm/s²": "мм/с²",
    "mm/s^2": "мм/с²",
    "s": "с",
    "%": "%",
    "°C": "°C",
    "°": "°",
    "mm²": "мм²",
    "mm³": "мм³",
    "g": "г",
}


def unescape(raw: str) -> str:
    out = []
    i = 0
    while i < len(raw):
        if raw[i] == "\\" and i + 1 < len(raw):
            n = raw[i + 1]
            out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(n, n))
            i += 2
        else:
            out.append(raw[i])
            i += 1
    return "".join(out)


def load_po(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    ctxt = msgid = msgstr = None
    mode = None

    def flush() -> None:
        nonlocal ctxt, msgid, msgstr, mode
        if ctxt is not None and msgid is not None:
            entries[ctxt] = msgstr or ""
        ctxt = msgid = msgstr = None
        mode = None

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("msgctxt "):
            flush()
            ctxt = unescape(line[len("msgctxt ") :].strip()[1:-1])
            mode = "ctxt"
        elif line.startswith("msgid "):
            msgid = unescape(line[len("msgid ") :].strip()[1:-1])
            mode = "id"
        elif line.startswith("msgstr "):
            msgstr = unescape(line[len("msgstr ") :].strip()[1:-1])
            mode = "str"
        elif line.startswith('"') and mode:
            piece = unescape(line.strip()[1:-1])
            if mode == "ctxt":
                ctxt = (ctxt or "") + piece
            elif mode == "id":
                msgid = (msgid or "") + piece
            elif mode == "str":
                msgstr = (msgstr or "") + piece
        elif not line.strip():
            flush()
    flush()
    return entries


def vis_keys(name: str) -> set[str]:
    keys = set()
    for line in (CURA / "setting_visibility" / name).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("[") or "=" in line:
            continue
        keys.add(line)
    return keys


def walk(node: dict, category: str, out: dict) -> None:
    for key, value in node.items():
        if not isinstance(value, dict):
            continue
        children = value.get("children") if isinstance(value.get("children"), dict) else None
        if value.get("type") == "category":
            walk(children or {}, key, out)
            continue
        options = []
        raw_options = value.get("options")
        if isinstance(raw_options, dict):
            for opt_key, opt_val in raw_options.items():
                if isinstance(opt_val, dict):
                    label = opt_val.get("label") or opt_key
                else:
                    label = str(opt_val)
                options.append({"value": opt_key, "label": label})
        out[key] = {
            "category": category,
            "type": value.get("type") or "str",
            "label": value.get("label") or key,
            "unit": value.get("unit") or "",
            "description": value.get("description") or "",
            "options": options,
        }
        if children:
            walk(children, category, out)


def strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"</(p|li|div|tr|h\d)>", ". ", text, flags=re.I)
    text = re.sub(r"<li[^>]*>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text


def shorten(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text)
    chunk = " ".join(part for part in parts[:2] if part).strip()
    if len(chunk) > 320:
        chunk = chunk[:320].rsplit(" ", 1)[0].rstrip(" ,;") + "…"
    replacements = (
        ("рабочей пластины", "стола"),
        ("рабочей пластине", "столе"),
        ("рабочую пластину", "стол"),
        ("рабочая пластина", "стол"),
        ("Рабочая пластина", "Стол"),
    )
    for src, dst in replacements:
        chunk = chunk.replace(src, dst)
    if chunk and chunk[-1] not in ".!?…":
        chunk += "."
    return chunk


def mostly_english(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return False
    ascii_letters = sum(1 for char in letters if char.isascii())
    return ascii_letters / len(letters) > 0.5


def field_type(raw: str) -> str:
    if raw == "float":
        return "float"
    if raw == "int":
        return "int"
    if raw == "bool":
        return "bool"
    if raw == "enum":
        return "enum"
    if raw in ("extruder", "optional_extruder"):
        return "extruder"
    return "text"


def main() -> None:
    po = load_po(CURA / "i18n" / "ru_RU" / "fdmextruder.def.json.po")
    po.update(load_po(CURA / "i18n" / "ru_RU" / "fdmprinter.def.json.po"))
    catalog: dict[str, dict] = {}
    for name in ("fdmprinter.def.json", "fdmextruder.def.json"):
        data = json.loads((CURA / "definitions" / name).read_text(encoding="utf-8"))
        walk(data.get("settings") or {}, "", catalog)

    basic = vis_keys("basic.cfg")
    advanced = vis_keys("advanced.cfg")
    expert = vis_keys("expert.cfg")

    def level_of(key: str) -> str:
        if key in basic:
            return "basic"
        if key in advanced:
            return "advanced"
        if key in expert:
            return "expert"
        return "all"

    known_cats = [item[0] for item in CATEGORIES]
    extra = []
    for item in catalog.values():
        cat = item["category"]
        if cat and cat not in known_cats and cat not in extra:
            extra.append(cat)
    categories = [{"id": key, "label": label} for key, label in CATEGORIES]
    categories.extend({"id": key, "label": key} for key in extra)

    fields = []
    hand = 0
    for key, item in catalog.items():
        label = po.get(f"{key} label") or item["label"]
        if key in HINTS:
            hint = HINTS[key]
            hand += 1
        else:
            ru = po.get(f"{key} description") or item["description"]
            hint = shorten(strip_html(ru)) or f"Пункт «{label}»."
            if mostly_english(hint):
                hint = f"{label}. Редкая настройка слайсера; на одном экструдере обычно не трогают."
        options = []
        for opt in item["options"]:
            options.append(
                {
                    "value": opt["value"],
                    "label": po.get(f"{key} option {opt['value']}") or opt["label"],
                }
            )
        kind = field_type(item["type"])
        if kind == "extruder" and not options:
            options = [{"value": "0", "label": "Экструдер 1"}]
            if item["type"] == "optional_extruder":
                options.insert(0, {"value": "-1", "label": "Как у остальных"})
        fields.append(
            {
                "key": key,
                "category": item["category"] or "machine_settings",
                "level": level_of(key),
                "label": label,
                "hint": hint,
                "unit": UNITS.get(item["unit"], item["unit"]),
                "type": kind,
                "options": options,
                "readonly": key in READONLY,
            }
        )

    order = {cat["id"]: index for index, cat in enumerate(categories)}
    fields.sort(key=lambda item: (order.get(item["category"], 99),))
    payload = {"categories": categories, "fields": fields}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    levels: dict[str, int] = {}
    for item in fields:
        levels[item["level"]] = levels.get(item["level"], 0) + 1
    empty = sum(1 for item in fields if not item["hint"])
    print(f"fields {len(fields)} hand {hand} empty {empty} levels {levels}")


if __name__ == "__main__":
    main()
