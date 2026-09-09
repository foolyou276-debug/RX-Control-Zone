"""apk_builder.py — GitHub Actions workflow gen, build monitor, AI auto-fixer."""
import time
from typing import Optional

import ai
import github_client as gh
from config import BUILD_MONITOR_TIMEOUT, BUILD_POLL_INTERVAL, MAX_FIX_ATTEMPTS

# ── Workflow templates ────────────────────────────────────────────────────

def _flutter_workflow() -> str:
    return """\
name: Build Flutter APK

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Java 17
        uses: actions/setup-java@v4
        with:
          distribution: zulu
          java-version: '17'

      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.22.0'
          channel: stable

      - name: Get dependencies
        run: flutter pub get

      - name: Build release APK
        run: flutter build apk --release

      - name: Upload APK artifact
        uses: actions/upload-artifact@v4
        with:
          name: release-apk
          path: build/app/outputs/flutter-apk/app-release.apk
          retention-days: 7
"""

def _android_native_workflow() -> str:
    return """\
name: Build Android APK

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Java 17
        uses: actions/setup-java@v4
        with:
          distribution: zulu
          java-version: '17'

      - name: Setup Android SDK
        uses: android-actions/setup-android@v3

      - name: Make gradlew executable
        run: chmod +x gradlew

      - name: Build release APK
        run: ./gradlew assembleRelease

      - name: Upload APK artifact
        uses: actions/upload-artifact@v4
        with:
          name: release-apk
          path: app/build/outputs/apk/release/*.apk
          retention-days: 7
"""

def _react_native_workflow() -> str:
    return """\
name: Build React Native APK

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node 20
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Setup Java 17
        uses: actions/setup-java@v4
        with:
          distribution: zulu
          java-version: '17'

      - name: Setup Android SDK
        uses: android-actions/setup-android@v3

      - name: Install JS dependencies
        run: npm ci

      - name: Make gradlew executable
        run: chmod +x android/gradlew

      - name: Build release APK
        working-directory: android
        run: ./gradlew assembleRelease

      - name: Upload APK artifact
        uses: actions/upload-artifact@v4
        with:
          name: release-apk
          path: android/app/build/outputs/apk/release/*.apk
          retention-days: 7
"""

def generate_workflow(project_type: str) -> str:
    templates = {
        "flutter":        _flutter_workflow,
        "android-native": _android_native_workflow,
        "react-native":   _react_native_workflow,
    }
    builder = templates.get(project_type)
    if builder:
        return builder()

    print(f"[Builder] Unknown type '{project_type}' — asking AI to generate workflow...")
    prompt = (
        f"Generate a complete GitHub Actions YAML workflow to build an APK "
        f"for a '{project_type}' Android project. "
        "Return ONLY the raw YAML — no markdown fences, no explanation."
    )
    return ai.chat(prompt)

# ── Build monitor ────────────────────────────────────────────────────────

def monitor_build(owner: str, repo: str) -> dict:
    """
    Poll GitHub Actions until the latest run completes.
    Returns a result dict with success/failure info.
    """
    print("\n[Monitor] Waiting for run to register (10 s)...")
    time.sleep(10)

    deadline = time.time() + BUILD_MONITOR_TIMEOUT
    run_id: Optional[int] = None
    prev_step_statuses: dict = {}

    while time.time() < deadline:
        run = gh.get_latest_run(owner, repo)
        if not run:
            time.sleep(BUILD_POLL_INTERVAL)
            continue

        run_id  = run["id"]
        status  = run["status"]
        concl   = run.get("conclusion")
        elapsed = int(time.time() - (deadline - BUILD_MONITOR_TIMEOUT))

        # Print job steps only when they change
        jobs = gh.get_run_jobs(owner, repo, run_id)
        for job in jobs:
            for step in job.get("steps", []):
                key    = f"{job['name']}/{step['name']}"
                st     = step.get("conclusion") or step.get("status") or "waiting"
                if prev_step_statuses.get(key) != st:
                    prev_step_statuses[key] = st
                    print(f"  [t={elapsed:>3}s] {key} → {st}")

        print(f"  [t={elapsed:>3}s] Run status={status} conclusion={concl or '—'}", end="\r")

        if status == "completed":
            print()   # newline after \r
            if concl == "success":
                artifacts = gh.get_artifacts(owner, repo, run_id)
                apk = next(
                    (a for a in artifacts if "apk" in a["name"].lower()),
                    artifacts[0] if artifacts else None,
                )
                return {
                    "success":  True,
                    "run_id":   run_id,
                    "run_url":  run["html_url"],
                    "artifact": apk,
                    "jobs":     jobs,
                }
            else:
                return {
                    "success":    False,
                    "run_id":     run_id,
                    "conclusion": concl,
                    "run_url":    run["html_url"],
                    "jobs":       jobs,
                }

        time.sleep(BUILD_POLL_INTERVAL)

    print()
    return {
        "success":    False,
        "run_id":     run_id,
        "conclusion": "timeout",
        "run_url":    f"https://github.com/{owner}/{repo}/actions",
        "jobs":       [],
    }

# ── AI auto-fixer ────────────────────────────────────────────────────────

def fix_and_rebuild(
    owner:         str,
    repo:          str,
    result:        dict,
    project_files: dict,        # {path: str} text files from the zip
    attempt:       int = 1,
) -> dict:
    """
    Ask AI to fix build errors, upload fixes, re-trigger build.
    Recursively retries up to MAX_FIX_ATTEMPTS.
    """
    if attempt > MAX_FIX_ATTEMPTS:
        print(f"\n[Fixer] Max attempts ({MAX_FIX_ATTEMPTS}) reached. Stopping.")
        return {"success": False, "reason": "max_fix_attempts_reached"}

    print(f"\n{'─'*50}")
    print(f"[Fixer] Attempt {attempt}/{MAX_FIX_ATTEMPTS} — collecting error logs...")

    # Gather failure logs from failed jobs
    error_logs = ""
    for job in result.get("jobs", []):
        if job.get("conclusion") in ("failure", "cancelled"):
            log = gh.get_job_logs(owner, repo, job["id"])
            error_logs += f"\n=== Job: {job['name']} ===\n{log}\n"

    if not error_logs:
        error_logs = (
            f"Run URL  : {result.get('run_url')}\n"
            f"Conclusion: {result.get('conclusion', 'failed')}"
        )

    file_list = list(project_files.keys())
    print(f"[Fixer] Sending {len(error_logs)} chars of logs to AI...")
    fix_data = ai.analyze_build_error(error_logs, file_list)

    analysis        = fix_data.get("analysis", "No analysis available.")
    fixes           = fix_data.get("fixes", {})
    action_changes  = fix_data.get("action_changes", "")

    print(f"[Fixer] AI says: {analysis[:200]}")

    # Upload fixed project files
    if fixes:
        print(f"[Fixer] Uploading {len(fixes)} fixed file(s)...")
        for path, content in fixes.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            gh.upload_file(owner, repo, path, content, f"fix: auto-fix attempt {attempt}")

    # Apply workflow changes if any
    if action_changes and len(action_changes) > 50:
        print("[Fixer] Updating workflow YAML...")
        gh.upload_file(
            owner, repo,
            ".github/workflows/build.yml",
            action_changes.encode("utf-8"),
            f"ci: fix workflow attempt {attempt}",
        )

    # Re-trigger
    print(f"[Fixer] Re-triggering build...")
    time.sleep(3)
    gh.trigger_workflow(owner, repo)

    new_result = monitor_build(owner, repo)

    if new_result["success"]:
        return new_result
    return fix_and_rebuild(owner, repo, new_result, project_files, attempt + 1)
