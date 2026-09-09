#!/data/data/com.termux/files/usr/bin/bash
# Git-AI — Termux installer
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Git-AI Installer (Termux)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Update & install Python
echo "[1/4] Installing Python & pip..."
pkg update -y -q
pkg install -y python python-pip unzip curl zip -q

# pip install deps
echo "[2/4] Installing Python packages..."
pip install -q -r requirements.txt

# Create sdcard folder
echo "[3/4] Creating /sdcard/Git-gi folder..."
mkdir -p /sdcard/Git-gi/projects

# Move script files to sdcard folder (optional)
echo "[4/4] Copying Git-AI scripts to /sdcard/Git-gi/git-ai/ ..."
DEST="/sdcard/Git-gi/git-ai"
mkdir -p "$DEST"
cp main.py config.py memory.py ai.py github_client.py project_reader.py apk_builder.py requirements.txt "$DEST/"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  DONE! Next step:"
echo "  cd /sdcard/Git-gi/git-ai"
echo "  python main.py setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
