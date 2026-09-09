#!/usr/bin/env python3
"""
Git-AI — Automated GitHub APK Builder (Termux)
===============================================
Commands:
  setup                        — Set GitHub token & BluesMinds key
  read      <zip>              — Read project zip, detect type, save to memory
  create-repo <name>           — Create GitHub repo & upload project files
  build-apk                    — Generate workflow, trigger build, monitor
  full-auto <zip> <repo-name>  — One command: read → repo → upload → build → fix
  status                       — Show current memory (project / repo / task)
  chat                         — Interactive AI chat (Hinglish)
  clear-memory                 — Clear conversation history from memory
  help                         — Show this message

Example full flow in Termux:
  python main.py setup
  python main.py full-auto /sdcard/MyApp.zip MyAwesomeApp
"""

import os
import sys

# ── .env loader ───────────────────────────────────────────────────────────

def _load_env() -> None:
    """Load /sdcard/Git-gi/.env into os.environ before importing config."""
    env_path = "/sdcard/Git-gi/.env"
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

_load_env()   # must run before any local import that uses config

# ── Imports (after env loaded) ────────────────────────────────────────────

import memory
import ai
import github_client as gh
import project_reader
import apk_builder
from config import GIT_GI_FOLDER, GITHUB_TOKEN

# ── Helpers ───────────────────────────────────────────────────────────────

def _sep(char: str = "═", width: int = 54) -> None:
    print(char * width)

def _resolve_owner_repo() -> tuple[str, str]:
    mem   = memory.load()
    repo  = mem.get("repo", {})
    if not repo:
        print("[Error] No repo in memory. Run 'create-repo' or 'full-auto' first.")
        sys.exit(1)
    owner, name = repo["full_name"].split("/", 1)
    return owner, name

def _print_apk_result(result: dict, owner: str, repo: str) -> None:
    """Print final build result — download link or failure summary."""
    _sep()
    if result.get("success"):
        print("  BUILD SUCCESSFUL!")
        print(f"  Run URL : {result.get('run_url')}")
        artifact = result.get("artifact")
        if artifact:
            dl_url = artifact.get("archive_download_url", "")
            print(f"\n  APK Artifact : {artifact['name']}")
            print(f"  Download URL : {dl_url}")
            print()
            print("  ── Termux download command ──")
            print(f"  curl -L -o apk.zip \\")
            print(f"    -H 'Authorization: token {GITHUB_TOKEN}' \\")
            print(f"    '{dl_url}'")
            print("  unzip apk.zip && ls *.apk")
        else:
            print("  No APK artifact found. Check the Actions page.")
    else:
        reason = result.get("reason") or result.get("conclusion") or "failed"
        print(f"  BUILD FAILED — {reason}")
        print(f"  Run URL : {result.get('run_url')}")
        print("  AI tried to auto-fix but could not resolve all errors.")
        print("  Check the Actions page for full logs.")
    _sep()

# ── Commands ──────────────────────────────────────────────────────────────

def cmd_setup() -> None:
    _sep()
    print("  Git-AI Setup")
    _sep()
    print("GitHub Personal Access Token (needs: repo, workflow, actions scopes):")
    token = input("  Token: ").strip()
    if not token:
        print("[Setup] No token entered. Aborted.")
        return

    print("\nBluesMinds API Key (press Enter to keep default):")
    key = input("  Key: ").strip()

    os.makedirs(GIT_GI_FOLDER, exist_ok=True)
    env_path = os.path.join(GIT_GI_FOLDER, ".env")
    lines = [f"GITHUB_TOKEN={token}\n"]
    if key:
        lines.append(f"BLUESMINDS_KEY={key}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n[Setup] Saved → {env_path}")
    print("[Setup] Restart script for changes to take effect.")


def cmd_read(zip_path: str) -> None:
    if not os.path.exists(zip_path):
        print(f"[Error] File not found: {zip_path}")
        sys.exit(1)

    files = project_reader.read_zip(zip_path)

    mem   = memory.load()
    proj  = mem.get("project", {})
    print(f"\n  Project : {proj.get('name')}  |  Type : {proj.get('type')}  |  Files : {proj.get('file_count')}")

    memory.set_task(f"Read project from {zip_path}")

    print("\n[AI] Generating project summary...")
    summary = ai.summarize_project(proj.get("type", "?"), list(files.keys()))
    print(f"\n{summary}\n")


def cmd_create_repo(repo_name: str) -> None:
    print(f"[GitHub] Verifying token...")
    try:
        username = gh.get_username()
        print(f"[GitHub] Logged in as: {username}")
    except RuntimeError as e:
        print(f"[Error] {e}")
        sys.exit(1)

    print(f"[GitHub] Creating repo: {repo_name}...")
    try:
        repo = gh.create_repo(repo_name, private=False)
        print(f"[GitHub] Repo created: {repo['html_url']}")
    except RuntimeError as e:
        print(f"[Error] {e}")
        sys.exit(1)

    mem  = memory.load()
    proj = mem.get("project", {})

    if not proj:
        print("[Warn] No project in memory. Run 'read <zip>' first.")
        return

    zip_path = proj.get("zip_path", "")
    if not zip_path or not os.path.exists(zip_path):
        zip_path = input("Enter path to project zip: ").strip()

    if os.path.exists(zip_path):
        print(f"\n[GitHub] Uploading files to {repo_name}...")
        files_bytes = project_reader.load_files_as_bytes(zip_path)
        gh.upload_all_files(username, repo_name, files_bytes)
    else:
        print("[Warn] Zip not found. Skipping file upload.")

    memory.set_task(f"Created repo {repo_name} on GitHub")
    print(f"\n[Done] {repo['html_url']}")


def cmd_build_apk() -> None:
    owner, repo = _resolve_owner_repo()

    mem       = memory.load()
    proj_type = mem.get("project", {}).get("type", "android-native")

    print(f"[Builder] Detected type : {proj_type}")
    workflow  = apk_builder.generate_workflow(proj_type)
    wf_path   = ".github/workflows/build.yml"

    print(f"[Builder] Uploading workflow: {wf_path}")
    gh.upload_file(owner, repo, wf_path, workflow.encode(), "ci: add APK build workflow")

    print("[Builder] Triggering workflow_dispatch...")
    if not gh.trigger_workflow(owner, repo):
        print("[Warn] Could not dispatch — workflow will run on the push above.")

    memory.set_task(f"Building APK — {owner}/{repo}")

    result = apk_builder.monitor_build(owner, repo)

    if not result["success"]:
        project_files = {}   # text files for AI fixer
        proj = mem.get("project", {})
        zp   = proj.get("zip_path", "")
        if os.path.exists(zp):
            project_files = project_reader.read_zip(zp)
        result = apk_builder.fix_and_rebuild(owner, repo, result, project_files)

    _print_apk_result(result, owner, repo)


def cmd_full_auto(zip_path: str, repo_name: str) -> None:
    _sep()
    print("  GIT-AI — FULL AUTO MODE")
    _sep()

    # Step 1 — Read zip
    print("\n[1/4] Reading project zip...")
    files_text  = project_reader.read_zip(zip_path)
    files_bytes = project_reader.load_files_as_bytes(zip_path)
    mem         = memory.load()
    proj        = mem.get("project", {})
    print(f"      Name={proj.get('name')}  Type={proj.get('type')}  Files={proj.get('file_count')}")

    # Step 2 — Create repo & upload
    print("\n[2/4] Creating GitHub repo & uploading files...")
    try:
        username = gh.get_username()
        print(f"      User: {username}")
    except RuntimeError as e:
        print(f"[Error] {e}")
        sys.exit(1)

    try:
        repo = gh.create_repo(repo_name, private=False)
        print(f"      Repo: {repo['html_url']}")
    except RuntimeError as e:
        print(f"[Error] {e}")
        sys.exit(1)

    gh.upload_all_files(username, repo_name, files_bytes)

    # Step 3 — Generate & upload workflow
    print("\n[3/4] Setting up GitHub Actions workflow...")
    proj_type = proj.get("type", "android-native")
    workflow  = apk_builder.generate_workflow(proj_type)
    gh.upload_file(username, repo_name, ".github/workflows/build.yml",
                   workflow.encode(), "ci: add APK build workflow")

    # Step 4 — Build, monitor, auto-fix
    print("\n[4/4] Triggering APK build...")
    gh.trigger_workflow(username, repo_name)
    memory.set_task(f"Full-auto build: {repo_name}")

    result = apk_builder.monitor_build(username, repo_name)

    if not result["success"]:
        result = apk_builder.fix_and_rebuild(username, repo_name, result, files_text)

    _print_apk_result(result, username, repo_name)


def cmd_status() -> None:
    memory.show_status()


def cmd_chat() -> None:
    print("=== Git-AI Chat (type 'exit' to quit) ===\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[Exit]")
            break
        if user_input.lower() in ("exit", "quit", "q"):
            break
        if not user_input:
            continue
        response = ai.chat(user_input)
        print(f"\nAI: {response}\n")


# ── Entry point ───────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("help", "--help", "-h"):
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "setup":
        cmd_setup()
    elif cmd == "read":
        if len(sys.argv) < 3:
            print("Usage: python main.py read <zip_path>")
            sys.exit(1)
        cmd_read(sys.argv[2])
    elif cmd == "create-repo":
        if len(sys.argv) < 3:
            print("Usage: python main.py create-repo <repo_name>")
            sys.exit(1)
        cmd_create_repo(sys.argv[2])
    elif cmd == "build-apk":
        cmd_build_apk()
    elif cmd == "full-auto":
        if len(sys.argv) < 4:
            print("Usage: python main.py full-auto <zip_path> <repo_name>")
            sys.exit(1)
        cmd_full_auto(sys.argv[2], sys.argv[3])
    elif cmd == "status":
        cmd_status()
    elif cmd == "chat":
        cmd_chat()
    elif cmd == "clear-memory":
        memory.clear_conversation()
    else:
        print(f"Unknown command: {cmd}\nRun 'python main.py help' for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()
