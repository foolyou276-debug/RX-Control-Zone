"""config.py — Git-AI global configuration."""
import os

# ── GitHub ──────────────────────────────────────────────────────────────
GITHUB_EMAIL  = "foolyou276@gmail.com"
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")   # set via .env or export
GITHUB_API    = "https://api.github.com"

# ── BluesMinds AI ───────────────────────────────────────────────────────
BLUESMINDS_ENDPOINT = "https://api.bluesminds.com/v1/chat/completions"
BLUESMINDS_KEY      = os.environ.get(
    "BLUESMINDS_KEY",
    "sk-HHKSdh22XmghMMxuE5HbZAjGCIRI7rqDYjkXnIG3GIUCp9VT"
)
AI_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"

# ── Paths (mobile sdcard) ────────────────────────────────────────────────
GIT_GI_FOLDER   = "/sdcard/Git-gi"
PROJECTS_FOLDER = os.path.join(GIT_GI_FOLDER, "projects")
MEMORY_FILE     = os.path.join(GIT_GI_FOLDER, "memory.json")
ENV_FILE        = os.path.join(GIT_GI_FOLDER, ".env")

# ── Limits ───────────────────────────────────────────────────────────────
MAX_CONVERSATION_HISTORY = 20
MAX_FILE_SIZE_BYTES      = 100 * 1024   # 100 KB per text file
MAX_UPLOAD_SIZE_BYTES    = 5  * 1024 * 1024  # 5 MB per binary file
MAX_FIX_ATTEMPTS         = 3
BUILD_MONITOR_TIMEOUT    = 600          # seconds
BUILD_POLL_INTERVAL      = 15          # seconds
