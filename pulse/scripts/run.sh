#!/bin/bash
# Kiro iOS Autonomous Coder
# Usage: ~/.codex/run.sh [project_dir]
# Example: ~/.codex/run.sh ~/Documents/iOS/MyApp

set -e

KIRO_DIR="$HOME/.codex"
AGENTS_DIR="$KIRO_DIR/agents"
PROJECT_DIR="${1:-$(pwd)}"

mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Kiro iOS Autonomous Coder                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Use Python utilities for status display
python3 << 'PYTHON_STATUS'
import sys
import json
from pathlib import Path

project = Path.cwd()
app_name = project.name

print(f"📁 Project: {project}")
print(f"📱 App: {app_name}")
print("")

# Check for key files
files_status = []
if (project / "DESIGN_GUIDE.md").exists():
    files_status.append("✅ DESIGN_GUIDE.md")
else:
    files_status.append("⚠️  No DESIGN_GUIDE.md")

if (project / "app_spec.txt").exists():
    files_status.append("✅ app_spec.txt")
else:
    files_status.append("⚠️  No app_spec.txt")

# Check for Xcode project
xcodeproj = list(project.glob("*.xcodeproj"))
if xcodeproj:
    files_status.append(f"✅ {xcodeproj[0].name}")
else:
    files_status.append("⚠️  No .xcodeproj")

for status in files_status:
    print(f"   {status}")

# Check feature_list.json and show progress
feature_file = project / "feature_list.json"
if feature_file.exists():
    try:
        with open(feature_file) as f:
            features = json.load(f)
        total = len(features)
        passing = sum(1 for f in features if f.get("passes", False))
        if total > 0:
            pct = (passing / total) * 100
            bar_len = 30
            filled = int(bar_len * passing / total)
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"\n📊 Progress: [{bar}] {passing}/{total} ({pct:.1f}%)")
            if passing == total:
                print("🎉 All features complete!")
    except:
        print("\n⚠️  Could not read feature_list.json")
else:
    print("\n⚠️  No feature_list.json (will be created by @1)")

print("")
PYTHON_STATUS

# Determine which agent to use
if [ -f "feature_list.json" ]; then
    TOTAL=$(grep -c '"passes"' feature_list.json 2>/dev/null || echo "0")
    DONE=$(grep -c '"passes": true' feature_list.json 2>/dev/null || echo "0")
    
    echo "▶️  Starting coder agent (opus-4.5, fallback: sonnet-4.5)..."
    echo "   Type @2 to continue building"
    echo ""
    exec /Users/home/.local/bin/codex chat --agent /Users/home/.codex/agents/coder
else
    if [ ! -f "app_spec.txt" ] && [ ! -f "DESIGN_GUIDE.md" ]; then
        echo "❌ Need app_spec.txt or DESIGN_GUIDE.md to start"
        echo ""
        echo "Create one of these files describing your app, then run again."
        exit 1
    fi
    
    echo "▶️  Starting initializer agent (opus-4.5, fallback: sonnet-4.5)..."
    echo "   Type @1 to create app_spec.txt and feature_list.json"
    echo ""
    exec /Users/home/.local/bin/codex chat --agent /Users/home/.codex/agents/initializer
fi
