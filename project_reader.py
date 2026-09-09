"""project_reader.py — Read project ZIP, detect type, extract files."""
import json
import os
import zipfile
from pathlib import Path
from typing import Optional

import memory
from config import PROJECTS_FOLDER, MAX_FILE_SIZE_BYTES, MAX_UPLOAD_SIZE_BYTES

# ── Skip lists ────────────────────────────────────────────────────────────

SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
    ".ttf", ".otf", ".woff", ".woff2",
    ".mp3", ".mp4", ".avi", ".wav", ".ogg",
    ".bin", ".so", ".class", ".dex",
    ".gradle-wrapper.jar",
}

SKIP_DIRS = {
    "build", ".gradle", ".idea", "node_modules",
    ".git", "__pycache__", ".dart_tool",
    ".android", ".ios", "ios", ".cxx",
}

# ── Type detection ────────────────────────────────────────────────────────

def detect_project_type(paths: list[str]) -> str:
    p = set(paths)
    if any("pubspec.yaml" in f for f in p):
        return "flutter"
    if any("build.gradle.kts" in f or "build.gradle" in f for f in p):
        return "android-native"
    if any("package.json" in f for f in p):
        return "react-native"
    if any("CMakeLists.txt" in f for f in p):
        return "cpp-android"
    return "unknown"

# ── Path normalizer ───────────────────────────────────────────────────────

def _normalize(name: str) -> str:
    """Strip the leading top-level folder that zips usually add."""
    parts = Path(name).parts
    if len(parts) > 1:
        return "/".join(parts[1:])
    return name

# ── Core readers ──────────────────────────────────────────────────────────

def read_zip(zip_path: str) -> dict:
    """
    Read project ZIP, return {relative_path: str_content}.
    Saves project info to memory and writes an index JSON.
    """
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Zip not found: {zip_path}")

    project_name = Path(zip_path).stem
    files: dict[str, str] = {}

    print(f"[Reader] Opening: {zip_path}")

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            entries = zf.namelist()
            print(f"[Reader] Total entries in zip: {len(entries)}")

            for name in entries:
                info = zf.getinfo(name)
                if info.is_dir():
                    continue

                parts = Path(name).parts
                # Skip unwanted dirs
                if any(d in SKIP_DIRS for d in parts):
                    continue
                # Skip unwanted extensions
                if Path(name).suffix.lower() in SKIP_EXTS:
                    continue

                rel = _normalize(name)

                if info.file_size > MAX_FILE_SIZE_BYTES:
                    files[rel] = f"[SKIPPED — file too large: {info.file_size} bytes]"
                    continue

                try:
                    raw = zf.read(name)
                    try:
                        files[rel] = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        files[rel] = f"[BINARY: {len(raw)} bytes]"
                except Exception:
                    continue

    except zipfile.BadZipFile as e:
        raise RuntimeError(f"Invalid zip file: {e}")

    proj_type = detect_project_type(list(files.keys()))

    project_info = {
        "name":       project_name,
        "type":       proj_type,
        "zip_path":   zip_path,
        "file_count": len(files),
        "files":      list(files.keys()),
    }
    memory.set_project(project_info)

    # Persist index
    os.makedirs(PROJECTS_FOLDER, exist_ok=True)
    idx_path = os.path.join(PROJECTS_FOLDER, f"{project_name}_index.json")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(project_info, f, indent=2)

    print(f"[Reader] Type detected : {proj_type}")
    print(f"[Reader] Files loaded  : {len(files)}")
    print(f"[Reader] Index saved   : {idx_path}")

    return files


def load_files_as_bytes(zip_path: str) -> dict:
    """
    Return {relative_path: bytes} — for uploading to GitHub.
    Skips files >5 MB and skipped extensions.
    """
    files: dict[str, bytes] = {}

    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            info = zf.getinfo(name)
            if info.is_dir():
                continue

            parts = Path(name).parts
            if any(d in SKIP_DIRS for d in parts):
                continue
            if Path(name).suffix.lower() in SKIP_EXTS:
                continue
            if info.file_size > MAX_UPLOAD_SIZE_BYTES:
                continue

            rel = _normalize(name)
            try:
                files[rel] = zf.read(name)
            except Exception:
                continue

    return files
