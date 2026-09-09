"""memory.py — Persistent JSON-based conversation & project memory."""
import json
import os
from typing import Optional

from config import MEMORY_FILE, GIT_GI_FOLDER, PROJECTS_FOLDER, MAX_CONVERSATION_HISTORY

# ── Internal helpers ─────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    os.makedirs(GIT_GI_FOLDER,   exist_ok=True)
    os.makedirs(PROJECTS_FOLDER, exist_ok=True)

def _default() -> dict:
    return {
        "conversation": [],
        "last_task":    None,
        "project":      {},
        "repo":         {},
    }

# ── Public API ───────────────────────────────────────────────────────────

def load() -> dict:
    _ensure_dirs()
    if not os.path.exists(MEMORY_FILE):
        return _default()
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Back-fill missing keys
        for k, v in _default().items():
            data.setdefault(k, v)
        return data
    except (json.JSONDecodeError, OSError):
        return _default()

def save(data: dict) -> None:
    _ensure_dirs()
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_message(role: str, content: str) -> None:
    data = load()
    data["conversation"].append({"role": role, "content": content})
    if len(data["conversation"]) > MAX_CONVERSATION_HISTORY:
        data["conversation"] = data["conversation"][-MAX_CONVERSATION_HISTORY:]
    save(data)

def set_task(task: str) -> None:
    data = load()
    data["last_task"] = task
    save(data)

def set_project(project_info: dict) -> None:
    data = load()
    data["project"] = project_info
    save(data)

def set_repo(repo_info: dict) -> None:
    data = load()
    data["repo"] = repo_info
    save(data)

def get_context_string() -> str:
    data = load()
    lines: list[str] = []
    if data.get("last_task"):
        lines.append(f"Last task: {data['last_task']}")
    proj = data.get("project", {})
    if proj:
        lines.append(
            f"Current project: {proj.get('name', '?')} "
            f"(type={proj.get('type', '?')}, files={proj.get('file_count', '?')})"
        )
    repo = data.get("repo", {})
    if repo:
        lines.append(f"GitHub repo: {repo.get('full_name', '')} → {repo.get('html_url', '')}")
    return "\n".join(lines)

def clear_conversation() -> None:
    data = load()
    data["conversation"] = []
    save(data)
    print("[Memory] Conversation cleared.")

def show_status() -> None:
    data = load()
    print("=== Git-AI Memory ===")
    print(f"  Last task : {data.get('last_task') or 'None'}")
    proj = data.get("project", {})
    if proj:
        print(f"  Project   : {proj.get('name')} ({proj.get('type')}) — {proj.get('file_count')} files")
    repo = data.get("repo", {})
    if repo:
        print(f"  Repo      : {repo.get('html_url')}")
    msgs = len(data.get("conversation", []))
    print(f"  Messages  : {msgs}")
