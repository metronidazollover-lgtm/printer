"""Локальный настройщик параметров. Слушает только этот компьютер.

Запуск из любой папки:
  python tuner/server.py
Затем откройте http://127.0.0.1:8765
"""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cura_catalog import import_material, import_nozzle, list_materials, list_nozzles
from cura_machines import import_card, list_visible

ROOT = Path(__file__).resolve().parent.parent
WEB = Path(__file__).resolve().parent / "web"
FIELDS = Path(__file__).resolve().parent / "fields.json"
PRESETS = ROOT / "library" / "presets"
CATALOGS = {
    "machines": ROOT / "library" / "machines",
    "filaments": ROOT / "library" / "filaments",
    "nozzles": ROOT / "library" / "nozzles",
}
HOST = "127.0.0.1"
PORT = 8765
MAX_BODY = 2_000_000
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,80}$")
STATUSES = {"draft", "approved", "sliced", "printed"}

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


def _query_hits(query: str, *parts: object) -> bool:
    hay = " ".join(str(part) for part in parts).lower()
    return all(token in hay for token in query.lower().split())


def _nozzle_hits(query: str, item: dict) -> bool:
    text = str(item["nozzle_mm"])
    numeric = query.replace(".", "", 1).isdigit()
    if numeric:
        if not text.startswith(query):
            return False
        rest = text[len(query) :]
        return rest == "" or not rest[0].isdigit()
    return query in item["name"].lower()


def list_presets() -> list[dict]:
    PRESETS.mkdir(parents=True, exist_ok=True)
    items = []
    for path in sorted(PRESETS.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        items.append(
            {
                "id": path.stem,
                "title": data.get("title") or path.stem,
                "status": data.get("status") or "draft",
                "material": data.get("material") or "",
                "nozzle_mm": data.get("nozzle_mm"),
                "part": data.get("part") or "",
            }
        )
    return items


def read_preset(preset_id: str) -> dict | None:
    path = PRESETS / f"{preset_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("preset must be an object")
    return data


def list_cards(kind: str) -> list[dict]:
    folder = CATALOGS[kind]
    folder.mkdir(parents=True, exist_ok=True)
    items = []
    for path in sorted(folder.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        items.append(
            {
                "id": path.stem,
                "title": data.get("title") or path.stem,
                "warn": data.get("warn") or "",
                "verified": bool(data.get("verified")),
                "nozzle_mm": data.get("nozzle_mm"),
            }
        )
    return items


def read_card(kind: str, card_id: str) -> dict | None:
    path = CATALOGS[kind] / f"{card_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("card must be an object")
    return data


def write_card(kind: str, card_id: str, data: dict, *, overwrite_verified: bool = True) -> None:
    if data.get("id") != card_id:
        raise ValueError("id in the file must match the address")
    if not isinstance(data.get("settings"), dict):
        raise ValueError("settings must be an object")
    folder = CATALOGS[kind]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{card_id}.json"
    if path.is_file() and not overwrite_verified:
        current = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(current, dict) and current.get("verified"):
            raise ValueError("проверенная карточка уже есть, файл не затёрт")
    data["kind"] = {"machines": "machine", "filaments": "filament", "nozzles": "nozzle"}[kind]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_preset(preset_id: str, data: dict) -> None:
    if data.get("id") != preset_id:
        raise ValueError("id in the file must match the address")
    if data.get("status") not in STATUSES:
        raise ValueError("status must be draft, approved, sliced or printed")
    if not isinstance(data.get("settings"), dict) or not isinstance(data.get("baseline"), dict):
        raise ValueError("settings and baseline must be objects")
    if not isinstance(data.get("prints"), list):
        raise ValueError("prints must be a list")
    PRESETS.mkdir(parents=True, exist_ok=True)
    path = PRESETS / f"{preset_id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} {fmt % args}")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload, code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def _file(self, path: Path) -> None:
        if not path.is_file():
            self._json({"error": "not found"}, 404)
            return
        self._send(200, path.read_bytes(), MIME.get(path.suffix, "application/octet-stream"))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/fields":
            self._file(FIELDS)
            return
        if path == "/api/presets":
            self._json(list_presets())
            return
        if path == "/api/cura-machines":
            query = parse_qs(urlparse(self.path).query).get("q", [""])[0]
            items = list_visible()
            if query.strip():
                items = [
                    item
                    for item in items
                    if _query_hits(query, item["name"], item["id"], item["manufacturer"])
                ]
            self._json(items[:80])
            return
        if path == "/api/cura-materials":
            query = parse_qs(urlparse(self.path).query).get("q", [""])[0]
            items = list_materials()
            if query.strip():
                items = [
                    item
                    for item in items
                    if _query_hits(
                        query,
                        item["name"],
                        item["id"],
                        item.get("brand") or "",
                        item.get("material") or "",
                        str(item.get("diameter") or ""),
                    )
                ]
            self._json(items[:80])
            return
        if path == "/api/cura-nozzles":
            query = parse_qs(urlparse(self.path).query).get("q", [""])[0].strip().lower()
            items = list_nozzles()
            if query:
                items = [item for item in items if _nozzle_hits(query, item)]
            self._json(items)
            return
        for kind in CATALOGS:
            if path == f"/api/{kind}":
                self._json(list_cards(kind))
                return
            match = re.fullmatch(rf"/api/{kind}/([A-Za-z0-9][A-Za-z0-9_-]{{0,80}})", path)
            if match:
                self._read_json_card(kind, match.group(1))
                return
        match = re.fullmatch(r"/api/presets/([A-Za-z0-9][A-Za-z0-9_-]{0,80})", path)
        if match:
            preset_id = match.group(1)
            try:
                data = read_preset(preset_id)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                self._json({"error": str(exc)}, 400)
                return
            if data is None:
                self._json({"error": "preset not found"}, 404)
                return
            self._json(data)
            return
        if path in ("/", "/index.html"):
            self._file(WEB / "index.html")
            return
        if path in ("/app.js", "/style.css"):
            self._file(WEB / path.lstrip("/"))
            return
        self._json({"error": "not found"}, 404)

    def _read_json_card(self, kind: str, card_id: str) -> None:
        try:
            data = read_card(kind, card_id)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            self._json({"error": str(exc)}, 400)
            return
        if data is None:
            self._json({"error": "not found"}, 404)
            return
        self._json(data)

    def _read_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0 or length > MAX_BODY:
            self._json({"error": "body size is not allowed"}, 400)
            return None
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, 400)
            return None
        if not isinstance(data, dict):
            self._json({"error": "body must be an object"}, 400)
            return None
        return data

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        for kind in CATALOGS:
            match = re.fullmatch(rf"/api/{kind}/([A-Za-z0-9][A-Za-z0-9_-]{{0,80}})", path)
            if match and ID_RE.fullmatch(match.group(1)):
                data = self._read_body()
                if data is None:
                    return
                try:
                    write_card(kind, match.group(1), data)
                except (ValueError, OSError) as exc:
                    self._json({"error": str(exc)}, 400)
                    return
                self._json({"ok": True, "id": match.group(1)})
                return
        match = re.fullmatch(r"/api/presets/([A-Za-z0-9][A-Za-z0-9_-]{0,80})", path)
        if not match or not ID_RE.fullmatch(match.group(1)):
            self._json({"error": "bad preset id"}, 400)
            return
        data = self._read_body()
        if data is None:
            return
        try:
            write_preset(match.group(1), data)
        except (ValueError, OSError) as exc:
            self._json({"error": str(exc)}, 400)
            return
        self._json({"ok": True, "id": match.group(1), "status": data.get("status")})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        imports = (
            (r"/api/cura-machines/([A-Za-z0-9][A-Za-z0-9_-]{0,80})", "machines", import_card),
            (r"/api/cura-materials/([A-Za-z0-9][A-Za-z0-9_-]{0,80})", "filaments", import_material),
            (r"/api/cura-nozzles/([A-Za-z0-9][A-Za-z0-9_-]{0,80})", "nozzles", import_nozzle),
        )
        for pattern, kind, loader in imports:
            match = re.fullmatch(pattern, path)
            if not match:
                continue
            stem = match.group(1)
            try:
                card = loader(stem)
                write_card(kind, stem, card, overwrite_verified=False)
            except (ValueError, OSError, FileNotFoundError, json.JSONDecodeError) as exc:
                self._json({"error": str(exc)}, 400)
                return
            self._json(card)
            return
        self._json({"error": "not found"}, 404)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Настройщик: http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлен.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
