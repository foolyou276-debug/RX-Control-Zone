# Git-AI — Automated GitHub APK Builder

> Termux pe chalao, ZIP do, GitHub pe repo bane ga, APK build ho ga, errors AI fix karega, download link mile ga.

---

## File Structure

```
git-ai/
├── main.py           ← CLI entry point (all commands yahan)
├── config.py         ← Paths, API endpoints, constants
├── memory.py         ← JSON memory (conversation + project + repo)
├── ai.py             ← BluesMinds AI client (error analysis, chat)
├── github_client.py  ← GitHub REST API (repo create, upload, Actions)
├── project_reader.py ← ZIP reader, type detector
├── apk_builder.py    ← Workflow generator, build monitor, AI auto-fixer
├── requirements.txt
└── install.sh        ← One-click Termux setup
```

---

## Quick Start (Termux)

```bash
# 1. Install
bash install.sh

# 2. Go to script folder
cd /sdcard/Git-gi/git-ai

# 3. Setup GitHub token
python main.py setup
# Enter your GitHub Personal Access Token
# (Settings → Developer settings → Personal access tokens → Fine-grained)
# Scopes needed: Contents (read/write), Actions (read/write)

# 4. Full auto — one command does everything
python main.py full-auto /sdcard/Git-gi/MyApp.zip MyRepoName
```

---

## Commands

| Command | Description |
|---|---|
| `setup` | GitHub token + BluesMinds key save karo |
| `read <zip>` | Project ZIP padho, type detect karo |
| `create-repo <name>` | GitHub repo banao + files upload karo |
| `build-apk` | Workflow banao + trigger karo + monitor karo |
| `full-auto <zip> <name>` | Upar ke sab ek command me |
| `status` | Current memory dekho |
| `chat` | AI se baat karo |
| `clear-memory` | Conversation history clear karo |

---

## Full Auto Flow

```
ZIP file
  │
  ├─[1]─ project_reader.read_zip()
  │       └─ type detect (Flutter / Android / React Native)
  │
  ├─[2]─ github_client.create_repo()
  │       └─ files upload (all non-binary)
  │
  ├─[3]─ apk_builder.generate_workflow()
  │       └─ upload .github/workflows/build.yml
  │
  ├─[4]─ github_client.trigger_workflow()
  │
  ├─[5]─ apk_builder.monitor_build()
  │       └─ poll every 15s, print step status
  │
  ├─[Success]─ Print APK download link + curl command
  │
  └─[Failure]─ apk_builder.fix_and_rebuild()
                  └─ ai.analyze_build_error() → fix files → re-trigger
                  └─ Retry up to 3 times
                  └─ Print result
```

---

## Memory Location

All memory + project index files saved at:
```
/sdcard/Git-gi/
├── .env                    ← GitHub token
├── memory.json             ← Conversation + project + repo state
└── projects/
    └── MyApp_index.json    ← Per-project file index
```

---

## Notes

- GitHub password se login nahi hota — **Personal Access Token** use hota hai
- APK artifact download karne ke liye token chahiye (curl command automatically print hoga)
- AI model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` via BluesMinds
- Max 3 auto-fix attempts; agar phir bhi fail ho toh Actions page check karo
