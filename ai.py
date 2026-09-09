"""ai.py — BluesMinds AI client with persistent memory context."""
import json
import requests

import memory
from config import BLUESMINDS_ENDPOINT, BLUESMINDS_KEY, AI_MODEL

SYSTEM_PROMPT = (
    "You are Git-AI, an expert Android/Flutter developer assistant running inside Termux. "
    "You help the user read project zips, create GitHub repos, build APKs via GitHub Actions, "
    "automatically fix build errors, and provide APK download links. "
    "Respond in Hinglish (Hindi + English mix) when talking to the user. "
    "For code/YAML/configs only, respond in plain English with no extra explanation."
)

# ── Core chat ─────────────────────────────────────────────────────────────

def chat(user_message: str, extra_context: str = "") -> str:
    """Send a message to the AI and return the response."""
    mem = memory.load()

    ctx = memory.get_context_string()
    if extra_context:
        ctx = (ctx + "\n" + extra_context).strip()

    system_content = SYSTEM_PROMPT
    if ctx:
        system_content += f"\n\n[Context]\n{ctx}"

    messages: list[dict] = [{"role": "system", "content": system_content}]
    messages.extend(mem.get("conversation", [])[-10:])
    messages.append({"role": "user", "content": user_message})

    try:
        resp = requests.post(
            BLUESMINDS_ENDPOINT,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {BLUESMINDS_KEY}",
            },
            json={
                "model":       AI_MODEL,
                "messages":    messages,
                "max_tokens":  4096,
                "temperature": 0.7,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data    = resp.json()
        answer  = data["choices"][0]["message"]["content"]

        memory.add_message("user",      user_message)
        memory.add_message("assistant", answer)
        return answer

    except requests.exceptions.Timeout:
        return "[AI Error] Request timed out. Dobara try karo."
    except requests.exceptions.HTTPError as e:
        return f"[AI Error] HTTP {e.response.status_code}: {e.response.text[:200]}"
    except (requests.RequestException, KeyError) as e:
        return f"[AI Error] {e}"

# ── Error analysis ─────────────────────────────────────────────────────────

def analyze_build_error(error_logs: str, file_list: list[str]) -> dict:
    """
    Ask the AI to analyze build logs and return a fix dict.
    Returns: {"analysis": str, "fixes": {path: content}, "action_changes": str}
    """
    prompt = (
        "GitHub Actions APK build FAILED. Analyze the logs below and return fixes.\n\n"
        f"ERROR LOGS (truncated):\n{error_logs[:4000]}\n\n"
        f"PROJECT FILES (top-level list):\n" + "\n".join(file_list[:40]) + "\n\n"
        "Return ONLY a JSON object — no markdown fences, no explanation — with this exact structure:\n"
        '{"analysis":"what went wrong","fixes":{"path/file.ext":"full fixed content"},'
        '"action_changes":"any changes needed in the workflow YAML or empty string"}'
    )

    raw = chat(prompt, extra_context="Task: Fix APK build error automatically")
    raw = raw.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: return raw analysis only
        return {"analysis": raw, "fixes": {}, "action_changes": ""}

# ── Project summary ────────────────────────────────────────────────────────

def summarize_project(proj_type: str, file_list: list[str]) -> str:
    file_sample = "\n".join(file_list[:30])
    return chat(
        f"Maine ek project load kiya hai.\n"
        f"Type: {proj_type}\n"
        f"Files (sample):\n{file_sample}\n\n"
        "Is project ka short summary do — kya hai, kaise build hoga."
    )
