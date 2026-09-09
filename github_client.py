"""github_client.py — GitHub REST API v3 wrapper."""
import base64
import time
from typing import Optional

import requests

from config import GITHUB_API, GITHUB_TOKEN

# ── Auth header ────────────────────────────────────────────────────────────

def _h() -> dict:
    if not GITHUB_TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN not set! Run: python main.py setup"
        )
    return {
        "Authorization":        f"token {GITHUB_TOKEN}",
        "Accept":               "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

# ── User ───────────────────────────────────────────────────────────────────

def get_username() -> str:
    try:
        r = requests.get(f"{GITHUB_API}/user", headers=_h(), timeout=30)
        r.raise_for_status()
        return r.json()["login"]
    except requests.RequestException as e:
        raise RuntimeError(f"GitHub auth failed: {e}")

# ── Repo ───────────────────────────────────────────────────────────────────

def create_repo(name: str, private: bool = False, description: str = "") -> dict:
    import memory
    payload = {
        "name":        name,
        "description": description or f"Auto-built by Git-AI",
        "private":     private,
        "auto_init":   False,
    }
    try:
        r = requests.post(
            f"{GITHUB_API}/user/repos",
            headers=_h(), json=payload, timeout=30
        )
        r.raise_for_status()
        repo = r.json()
        memory.set_repo({
            "full_name": repo["full_name"],
            "html_url":  repo["html_url"],
            "name":      repo["name"],
        })
        return repo
    except requests.HTTPError as e:
        body = e.response.json() if e.response else {}
        msg  = body.get("message", str(e))
        # Repo already exists?
        if "already exists" in msg.lower():
            raise RuntimeError(f"Repo '{name}' already exists on your account.")
        raise RuntimeError(f"Create repo failed: {msg}")

# ── File upload ────────────────────────────────────────────────────────────

def _get_file_sha(owner: str, repo: str, path: str) -> Optional[str]:
    try:
        r = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            headers=_h(), timeout=20
        )
        if r.status_code == 200:
            return r.json().get("sha")
    except requests.RequestException:
        pass
    return None

def upload_file(
    owner:   str,
    repo:    str,
    path:    str,
    content: bytes,
    message: str = "chore: update file",
) -> bool:
    encoded = base64.b64encode(content).decode()
    payload: dict = {"message": message, "content": encoded}

    sha = _get_file_sha(owner, repo, path)
    if sha:
        payload["sha"] = sha

    try:
        r = requests.put(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            headers=_h(), json=payload, timeout=60
        )
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"    [WARN] upload failed for {path}: {e}")
        return False

def upload_all_files(
    owner:      str,
    repo:       str,
    files:      dict,      # {relative_path: bytes | str}
    commit_msg: str = "feat: initial upload by Git-AI",
) -> int:
    total   = len(files)
    success = 0
    for i, (path, content) in enumerate(files.items(), 1):
        print(f"  [{i:>3}/{total}] {path}")
        if isinstance(content, str):
            content = content.encode("utf-8")
        if upload_file(owner, repo, path, content, commit_msg):
            success += 1
        time.sleep(0.3)   # avoid secondary rate-limit
    print(f"  → Uploaded {success}/{total} files.")
    return success

# ── Actions ────────────────────────────────────────────────────────────────

def trigger_workflow(
    owner:         str,
    repo:          str,
    workflow_file: str = "build.yml",
    ref:           str = "main",
) -> bool:
    try:
        r = requests.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/actions/workflows/{workflow_file}/dispatches",
            headers=_h(), json={"ref": ref}, timeout=30
        )
        return r.status_code == 204
    except requests.RequestException as e:
        print(f"  [WARN] trigger_workflow: {e}")
        return False

def get_latest_run(owner: str, repo: str) -> Optional[dict]:
    try:
        r = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/actions/runs?per_page=1",
            headers=_h(), timeout=30
        )
        r.raise_for_status()
        runs = r.json().get("workflow_runs", [])
        return runs[0] if runs else None
    except requests.RequestException:
        return None

def get_run_jobs(owner: str, repo: str, run_id: int) -> list:
    try:
        r = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/actions/runs/{run_id}/jobs",
            headers=_h(), timeout=30
        )
        r.raise_for_status()
        return r.json().get("jobs", [])
    except requests.RequestException:
        return []

def get_job_logs(owner: str, repo: str, job_id: int) -> str:
    try:
        r = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/actions/jobs/{job_id}/logs",
            headers=_h(), allow_redirects=True, timeout=60
        )
        if r.status_code == 200:
            return r.text[:6000]
    except requests.RequestException:
        pass
    return ""

def get_artifacts(owner: str, repo: str, run_id: int) -> list:
    try:
        r = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts",
            headers=_h(), timeout=30
        )
        r.raise_for_status()
        return r.json().get("artifacts", [])
    except requests.RequestException:
        return []
