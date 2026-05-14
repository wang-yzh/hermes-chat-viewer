#!/usr/bin/env python3
"""Local Hermes session viewer server.

This intentionally serves only localhost and only reads known Hermes session
directories, so the browser can browse sessions without broad filesystem access.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sqlite3
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
HOME = Path.home()
HERMES_ROOT = HOME / ".hermes"
SESSION_ID_RE = re.compile(r"(\d{8}_\d{6}_[a-f0-9]+)", re.I)


@dataclass(frozen=True)
class ProfileRoot:
    name: str
    path: Path


def profile_roots() -> list[ProfileRoot]:
    roots = [ProfileRoot("default", HERMES_ROOT / "sessions")]
    profiles_dir = HERMES_ROOT / "profiles"
    if profiles_dir.is_dir():
        for profile in sorted(profiles_dir.iterdir()):
            sessions = profile / "sessions"
            if sessions.is_dir():
                roots.append(ProfileRoot(profile.name, sessions))
    return [root for root in roots if root.path.is_dir()]


def infer_session_id(path: Path) -> str:
    match = SESSION_ID_RE.search(path.name)
    if match:
        return match.group(1)
    return path.stem.removeprefix("session_")


def safe_read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def read_head(path: Path, limit: int = 262_144) -> str:
    try:
        with path.open("rb") as handle:
            return handle.read(limit).decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_string_field(text: str, field: str) -> str:
    match = re.search(rf'"{re.escape(field)}"\s*:\s*"((?:\\.|[^"\\])*)"', text)
    if not match:
        return ""
    try:
        return json.loads(f'"{match.group(1)}"')
    except Exception:
        return match.group(1)


def extract_number_field(text: str, field: str) -> int:
    match = re.search(rf'"{re.escape(field)}"\s*:\s*(\d+)', text)
    return int(match.group(1)) if match else 0


def load_state_titles() -> dict[str, dict]:
    """Read lightweight session metadata from each profile's SQLite state DB."""
    titles: dict[str, dict] = {}
    db_paths = [("default", HERMES_ROOT / "state.db")]
    profiles_dir = HERMES_ROOT / "profiles"
    if profiles_dir.is_dir():
        for profile in sorted(profiles_dir.iterdir()):
            db_paths.append((profile.name, profile / "state.db"))

    for profile, db_path in db_paths:
        if not db_path.is_file():
            continue
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=1)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                select id, title, source, model, message_count, started_at, ended_at, parent_session_id, end_reason
                from sessions
                """
            ).fetchall()
            conn.close()
        except Exception:
            continue
        for row in rows:
            titles[f"{profile}:{row['id']}"] = {
                "title": row["title"] or "",
                "source": row["source"] or "",
                "model": row["model"] or "",
                "message_count": row["message_count"] or 0,
                "started_at": row["started_at"] or 0,
                "ended_at": row["ended_at"] or 0,
                "parent_session_id": row["parent_session_id"] or "",
                "end_reason": row["end_reason"] or "",
            }
    return titles


def lineage_superseded_ids(db_meta: dict[str, dict]) -> dict[str, str]:
    """Return profile:session_id -> latest descendant for compressed/resumed chains.

    Hermes splits long conversations into parent/child sessions during
    compression/resume. For browsing, the latest leaf is usually the useful row;
    older ancestors are still on disk but their context is represented by the
    descendant chain.
    """
    children: dict[str, list[str]] = {}
    for key, meta in db_meta.items():
        profile, _, sid = key.partition(":")
        parent = meta.get("parent_session_id") or ""
        if parent:
            children.setdefault(f"{profile}:{parent}", []).append(key)

    def newest_leaf(key: str) -> str:
        stack = list(children.get(key, []))
        if not stack:
            return key
        best = key
        best_started = float(db_meta.get(key, {}).get("started_at") or 0)
        while stack:
            current = stack.pop()
            started = float(db_meta.get(current, {}).get("started_at") or 0)
            if started >= best_started:
                best = current
                best_started = started
            stack.extend(children.get(current, []))
        return newest_leaf(best) if children.get(best) else best

    superseded = {}
    for key in db_meta:
        leaf = newest_leaf(key)
        if leaf != key:
            superseded[key] = leaf
    return superseded


def read_jsonl_preview(path: Path, max_lines: int = 6) -> tuple[int, str, str]:
    count = 0
    first_text = ""
    last_ts = ""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                count += 1
                if count <= max_lines or not last_ts:
                    try:
                        item = json.loads(line)
                    except Exception:
                        continue
                    if not first_text:
                        first_text = str(item.get("content") or item.get("text") or "")[:160]
                    last_ts = str(item.get("timestamp") or item.get("created_at") or last_ts)
    except Exception:
        pass
    return count, first_text, last_ts


def session_summary(
    profile: ProfileRoot,
    path: Path,
    db_meta: dict[str, dict],
    superseded: dict[str, str],
) -> dict:
    stat = path.stat()
    sid = infer_session_id(path)
    meta = db_meta.get(f"{profile.name}:{sid}", {})
    superseded_by_key = superseded.get(f"{profile.name}:{sid}", "")
    superseded_by_id = superseded_by_key.partition(":")[2] if superseded_by_key else ""
    summary = {
        "profile": profile.name,
        "file": path.name,
        "session_id": sid,
        "title": meta.get("title", ""),
        "model": meta.get("model", ""),
        "platform": meta.get("source", ""),
        "message_count": int(meta.get("message_count", 0) or 0),
        "preview": "",
        "last_updated": "",
        "mtime": stat.st_mtime,
        "size": stat.st_size,
        "kind": path.suffix.lower().lstrip("."),
        "parent_session_id": meta.get("parent_session_id", ""),
        "end_reason": meta.get("end_reason", ""),
        "superseded": bool(superseded_by_id),
        "superseded_by": superseded_by_id,
    }

    if path.suffix.lower() == ".json":
        head = read_head(path)
        preview = ""
        preview_match = re.search(r'"messages"\s*:\s*\[\s*\{.*?"content"\s*:\s*"((?:\\.|[^"\\])*)"', head, re.S)
        if preview_match:
            try:
                preview = json.loads(f'"{preview_match.group(1)}"')[:180]
            except Exception:
                preview = preview_match.group(1)[:180]
        summary.update(
            session_id=sid,
            title=extract_string_field(head, "title") or summary["title"],
            model=extract_string_field(head, "model") or summary["model"],
            platform=extract_string_field(head, "platform") or extract_string_field(head, "source") or summary["platform"],
            message_count=extract_number_field(head, "message_count") or summary["message_count"] or head.count('"role"'),
            preview=preview,
            last_updated=extract_string_field(head, "last_updated") or extract_string_field(head, "ended_at") or extract_string_field(head, "session_start"),
        )
    else:
        count, preview, last_ts = read_jsonl_preview(path)
        summary.update(message_count=count, preview=preview, last_updated=last_ts)

    return summary


def first_message_preview(messages: list) -> str:
    for message in messages:
        if not isinstance(message, dict):
            continue
        text = message.get("content")
        if isinstance(text, str) and text.strip():
            return text.strip()[:180]
    return ""


def find_session_file(profile_name: str, file_name: str) -> Path | None:
    for root in profile_roots():
        if root.name != profile_name:
            continue
        candidate = (root.path / file_name).resolve()
        try:
            candidate.relative_to(root.path.resolve())
        except ValueError:
            return None
        if candidate.is_file() and candidate.suffix.lower() in {".json", ".jsonl"}:
            return candidate
    return None


def load_session(profile_name: str, file_name: str) -> dict:
    path = find_session_file(profile_name, file_name)
    if not path:
        raise FileNotFoundError(f"Session not found: {profile_name}/{file_name}")
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".jsonl":
        sid = infer_session_id(path)
        meta = load_state_titles().get(f"{profile_name}:{sid}", {})
        messages = []
        for index, line in enumerate(text.splitlines()):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    messages.append(item)
            except Exception as exc:
                messages.append({"role": "system", "content": f"JSONL parse error on line {index + 1}: {exc}"})
        return {
            "session_id": sid,
            "file": path.name,
            "profile": profile_name,
            "title": meta.get("title", ""),
            "model": meta.get("model", ""),
            "platform": meta.get("source", ""),
            "kind": "jsonl",
            "messages": messages,
        }

    data = json.loads(text)
    if not isinstance(data, dict):
        data = {"messages": data if isinstance(data, list) else []}
    data["file"] = path.name
    data["profile"] = profile_name
    data["kind"] = "json"
    meta = load_state_titles().get(f"{profile_name}:{data.get('session_id') or infer_session_id(path)}", {})
    data["title"] = data.get("title") or meta.get("title", "")
    data["model"] = data.get("model") or meta.get("model", "")
    data["platform"] = data.get("platform") or data.get("source") or meta.get("source", "")
    return data


def list_sessions() -> dict:
    items = []
    seen = set()
    db_meta = load_state_titles()
    superseded = lineage_superseded_ids(db_meta)
    for root in profile_roots():
        for path in root.path.iterdir():
            if path.suffix.lower() not in {".json", ".jsonl"}:
                continue
            if path.name == "sessions.json":
                continue
            key = (root.name, path.name)
            if key in seen:
                continue
            seen.add(key)
            items.append(session_summary(root, path, db_meta, superseded))
    items.sort(key=lambda item: (item.get("last_updated") or "", item.get("mtime") or 0), reverse=True)
    return {"profiles": [root.name for root in profile_roots()], "sessions": items}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print("%s - %s" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/shutdown":
                self.send_json({"ok": True, "message": "Hermes Chat Viewer is shutting down."})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if parsed.path == "/api/sessions":
                self.send_json(list_sessions())
                return
            if parsed.path == "/api/session":
                qs = parse_qs(parsed.query)
                profile = qs.get("profile", [""])[0]
                file_name = qs.get("file", [""])[0]
                self.send_json(load_session(profile, file_name))
                return
            self.serve_static(parsed.path)
        except FileNotFoundError as exc:
            self.send_json({"error": str(exc)}, status=404)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def serve_static(self, request_path: str) -> None:
        rel = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        target = (ROOT / rel).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError:
            self.send_error(403)
            return
        if not target.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes local chat viewer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8765")))
    parser.add_argument("--open", action="store_true", help="Open the viewer in the default browser")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"Hermes Chat Viewer: {url}")
    print("Press Ctrl+C to stop.")
    if args.open:
        webbrowser.open(url)
    server.serve_forever()


if __name__ == "__main__":
    main()
