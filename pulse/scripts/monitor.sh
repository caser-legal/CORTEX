#!/bin/bash
# PULSE System Monitor - smooth refresh

progress_bar() {
    local pct=$1
    local width=20
    local filled=$((pct * width / 100))
    local empty=$((width - filled))
    printf "["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "]"
}

project_cache=""
process_cache=""

cleanup() {
    tput cnorm
    if [ -n "$project_cache" ] && [ -f "$project_cache" ]; then
        rm -f "$project_cache"
    fi
    if [ -n "$process_cache" ] && [ -f "$process_cache" ]; then
        rm -f "$process_cache"
    fi
    exit
}

# Hide cursor, clear screen once
tput civis
tput clear
trap cleanup INT TERM

while true; do
    # Move cursor to top-left instead of clearing
    tput cup 0 0

    project_cache=$(mktemp)
    python3 - "$project_cache" <<'PY'
import json
import sys
from pathlib import Path

MIN_FEATURES = 300
output_path = Path(sys.argv[1])
projects: list[dict] = []
base = Path.home() / "Documents" / "iOS"


def count_features(file_path: Path) -> tuple[int, int]:
    passing = 0
    total = 0
    if not file_path.exists():
        return passing, total
    try:
        with open(file_path) as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            if isinstance(data.get("test_suite"), list):
                tests = data["test_suite"]
            elif isinstance(data.get("features"), list):
                tests = data["features"]
            else:
                tests = []
        elif isinstance(data, list):
            tests = data
        else:
            tests = []
        total = len(tests)
        passing = sum(1 for test in tests if isinstance(test, dict) and test.get("passes"))
    except Exception:
        pass
    return passing, total


def count_qa(file_path: Path) -> tuple[int, int]:
    verified = 0
    total = 0
    if not file_path.exists():
        return verified, total
    try:
        with open(file_path) as fh:
            data = json.load(fh)
        if isinstance(data, list):
            total = len(data)
            verified = sum(1 for check in data if isinstance(check, dict) and check.get("verified"))
    except Exception:
        pass
    return verified, total


if base.exists():
    for proj in sorted(base.iterdir()):
        if not proj.is_dir():
            continue
        feature_file = proj / "feature_list.json"
        qa_file = proj / "qa_checklist.json"
        passing, total = count_features(feature_file)
        qa_verified, qa_total = count_qa(qa_file)
        feature_pct = min((passing * 100) // MIN_FEATURES, 100) if passing > 0 else 0
        feature_pct = 100 if passing >= MIN_FEATURES else feature_pct
        qa_pct = (qa_verified * 100) // qa_total if qa_total > 0 else 0
        state_path = proj / ".codex" / "memory" / "session_state.json"
        session_start = ""
        current_task = ""
        active_session = False
        if state_path.exists():
            try:
                with open(state_path) as fh:
                    state = json.load(fh)
                session_start = state.get("session_start", "")
                current_task = state.get("current_task", "")
                active_session = not state.get("session_end")
            except Exception:
                pass
        stage = "qa" if (qa_total > 0 and qa_verified < qa_total and passing >= MIN_FEATURES) else "coder"
        projects.append({
            "name": proj.name,
            "path": str(proj),
            "passing": passing,
            "total": total,
            "feature_pct": feature_pct,
            "qa_verified": qa_verified,
            "qa_total": qa_total,
            "qa_pct": qa_pct,
            "has_features": feature_file.exists(),
            "active_session": active_session,
            "session_start": session_start,
            "current_task": current_task,
            "stage": stage
        })

with open(output_path, "w") as fh:
    json.dump(projects, fh)
PY
    
    process_cache=$(mktemp)
    python3 - "$project_cache" "$process_cache" <<'PY'
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

project_cache = Path(sys.argv[1])
process_cache = Path(sys.argv[2])

projects = json.load(project_cache.open())
projects_by_path = {proj["path"].rstrip("/"): proj for proj in projects}
projects_by_name = {proj["name"]: proj for proj in projects}

lsof_cmd = shutil.which("lsof") or "/usr/sbin/lsof"
keywords = ("codex ", "codex-chat", "autonomous.py", "autonomous_qa.py", "autoo.py")


def normalize_project_path(raw_path: str):
    if not raw_path:
        return None
    p = Path(raw_path.strip())
    if str(p).startswith("~"):
        p = Path(os.path.expanduser(str(p)))
    if p.exists():
        try:
            p = p.resolve()
        except Exception:
            pass
    parts = p.parts
    if "iOS" in parts:
        idx = parts.index("iOS")
        proj = Path(*parts[: idx + 2])
        return proj
    return p


def lookup_project(raw_path: str):
    proj_path = normalize_project_path(raw_path)
    if proj_path is None:
        return None, ""
    key = str(proj_path).rstrip("/")
    if key in projects_by_path:
        return projects_by_path[key], key
    name = proj_path.name
    if name in projects_by_name:
        candidate = projects_by_name[name]
        return candidate, candidate["path"]
    return None, key


def get_cwd(pid: str) -> str:
    if not lsof_cmd:
        return ""
    try:
        output = subprocess.check_output(
            [lsof_cmd, "-a", "-d", "cwd", "-Fn", "-p", str(pid)],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        for line in output.splitlines():
            if line.startswith("n"):
                return line[1:]
    except Exception:
        return ""
    return ""


entries: list[dict] = []
try:
    ps_output = subprocess.check_output(["ps", "-axo", "pid=,command="], text=True)
except Exception:
    ps_output = ""

for raw in ps_output.splitlines():
    raw = raw.strip()
    if not raw:
        continue
    if not any(keyword in raw for keyword in keywords):
        continue
    parts = raw.split(None, 1)
    if len(parts) < 2:
        continue
    pid, cmd = parts
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        tokens = cmd.split()
    label = ""
    stage = "CODER"
    for idx, arg in enumerate(tokens):
        if arg == "--agent" and idx + 1 < len(tokens):
            label = tokens[idx + 1].split("/")[-1]
            break
    if not label:
        if "autonomous_qa.py" in cmd:
            label = "autonomous-qa"
        elif "autonomous.py" in cmd:
            label = "autonomous"
        elif "autoo.py" in cmd:
            label = "autoo"
    label_lower = label.lower()
    if "qa" in label_lower:
        stage = "QA"
    elif "init" in label_lower:
        stage = "INIT"
    project = ""
    for idx, arg in enumerate(tokens):
        if arg in ("-p", "--project-dir", "--project") and idx + 1 < len(tokens):
            project = tokens[idx + 1]
            break
    if not project:
        for arg in tokens:
            if "/Documents/iOS/" in arg:
                project = arg
                break
    if not project:
        project = get_cwd(pid)
    metrics, normalized_path = lookup_project(project)
    project_name = ""
    if metrics:
        project_name = metrics["name"]
    elif normalized_path:
        project_name = Path(normalized_path).name
    entries.append(
        {
            "label": label.upper() if label else ("QA" if stage == "QA" else "CODER"),
            "stage": stage.upper(),
            "pid": pid,
            "project_path": normalized_path,
            "project_name": project_name,
            "feature_pct": metrics.get("feature_pct") if metrics else None,
            "passing": metrics.get("passing") if metrics else None,
            "qa_pct": metrics.get("qa_pct") if metrics else None,
            "qa_verified": metrics.get("qa_verified") if metrics else None,
            "qa_total": metrics.get("qa_total") if metrics else None,
            "command": cmd if len(cmd) <= 180 else f"{cmd[:177]}...",
        }
    )

with process_cache.open("w") as fh:
    json.dump(entries, fh)
PY
    
    echo ""
    echo "        ██████╗ ██╗   ██╗██╗     ███████╗███████╗"
    echo "        ██╔══██╗██║   ██║██║     ██╔════╝██╔════╝"
    echo "        ██████╔╝██║   ██║██║     ███████╗█████╗  "
    echo "        ██╔═══╝ ██║   ██║██║     ╚════██║██╔══╝  "
    echo "        ██║     ╚██████╔╝███████╗███████║███████╗"
    echo "        ╚═╝      ╚═════╝ ╚══════╝╚══════╝╚══════╝"
    echo ""
    echo "       Persistent Unified Learning Session Engine"
    echo ""
    echo "╭──────────────────────────────────────────────────────────────────────────╮"
    echo "│  🤖 ACTIVE AGENTS                                                        │"
    echo "╰──────────────────────────────────────────────────────────────────────────╯"
    
    active_agents=$(python3 - "$process_cache" <<'PY'
import json
import sys
from collections import defaultdict, Counter

entries = json.load(open(sys.argv[1]))
groups = defaultdict(list)

for entry in entries:
    key = entry.get("project_path") or entry.get("project_name") or f"pid:{entry['pid']}"
    groups[key].append(entry)


def sort_key(item):
    group = item[1]
    best_pct = 0
    for entry in group:
        qa_total = entry.get("qa_total") or 0
        pct = entry.get("qa_pct") if qa_total else entry.get("feature_pct")
        pct = pct or 0
        if pct > best_pct:
            best_pct = pct
    return best_pct


for key, group in sorted(groups.items(), key=sort_key, reverse=True):
    name = group[0].get("project_name") or group[0].get("project_path") or group[0]["pid"]
    path = group[0].get("project_path") or ""
    qa_entries = [g for g in group if (g.get("qa_total") or 0) > 0]
    if qa_entries:
        qa_entry = max(qa_entries, key=lambda e: e.get("qa_pct") or 0)
        bar_kind = "QA"
        bar_pct = qa_entry.get("qa_pct") or 0
        qa_verified = qa_entry.get("qa_verified") or 0
        qa_total = qa_entry.get("qa_total") or 0
    else:
        qa_entry = None
        bar_kind = "FEAT"
        bar_pct = max((g.get("feature_pct") or 0) for g in group)
        qa_verified = 0
        qa_total = 0
    passing = max((g.get("passing") or 0) for g in group)
    feature_pct = max((g.get("feature_pct") or 0) for g in group)
    label_counts = Counter(g.get("label", "UNKNOWN") for g in group)
    label_summary = "|".join(
        f"{label}×{count}" if count > 1 else label
        for label, count in sorted(label_counts.items())
    )
    pid_list = ",".join(g["pid"] for g in group)
    print(
        f"{label_summary}\t{name}\t{path}\t{bar_kind}\t{bar_pct}\t"
        f"{qa_verified}\t{qa_total}\t{feature_pct}\t{passing}\t{pid_list}"
    )
PY
)

    if [ -z "$active_agents" ]; then
        echo "    None running                                                    "
        echo "    python3 ~/.codex/autoo.py -p /Users/home/Documents/iOS/<project> "
    else
        while IFS=$'\t' read -r labels name path bar_kind bar_pct qa_verified qa_total feature_pct passing pid_list; do
            [ -z "$labels" ] && continue
            name_display="$name"
            [ -z "$name_display" ] && name_display="(unknown)"
            path_display="$path"
            [ -z "$path_display" ] && path_display="[cwd unknown]"
            pct_display=${bar_pct:-0}
            if [ "$pct_display" = "None" ] || [ -z "$pct_display" ]; then
                pct_display=0
            fi
            bar=$(progress_bar "$pct_display")
            if [ "$bar_kind" = "QA" ] && [ "${qa_total:-0}" -gt 0 ] 2>/dev/null; then
                printf "    🔄 [%s] %-18s %s %3d%%  QA %s/%s │ Feat %3d%% (%s/300)\n" \
                    "$labels" "${name_display:0:18}" "$bar" "$pct_display" "$qa_verified" "$qa_total" "$feature_pct" "$passing"
            else
                printf "    🔄 [%s] %-18s %s %3d%%  Feat %s/300\n" \
                    "$labels" "${name_display:0:18}" "$bar" "$pct_display" "$passing"
            fi
            printf "       PID %s │ %s\n" "$pid_list" "$path_display"
        done <<< "$active_agents"
    fi
    
    
    echo ""
    echo "╭──────────────────────────────────────────────────────────────────────────╮"
    echo "│  🧠 MEMORY                                                               │"
    echo "╰──────────────────────────────────────────────────────────────────────────╯"
    if [ -f ~/.codex/memory/learned_insights.json ]; then
        sessions=$(grep -o '"total_sessions": *[0-9]*' ~/.codex/memory/learned_insights.json | grep -o '[0-9]*')
        features=$(grep -o '"total_features_completed": *[0-9]*' ~/.codex/memory/learned_insights.json | grep -o '[0-9]*')
        [ -z "$sessions" ] && sessions=0
        [ -z "$features" ] && features=0
        if [ "$sessions" -gt 0 ]; then
            avg=$((features / sessions))
        else
            avg=0
        fi
        echo "    Sessions: $sessions  │  Features: $features  │  Avg: $avg/session"
    fi
    if [ -f ~/.codex/memory/semantic.json ]; then
        rules=$(grep -c '"impossible_features"' ~/.codex/memory/semantic.json 2>/dev/null || echo 0)
        echo "    Learned: 8 impossible features blocked                     "
    fi
    
    echo ""
    echo "╭──────────────────────────────────────────────────────────────────────────╮"
    echo "│  📊 IN PROGRESS                                                          │"
    echo "╰──────────────────────────────────────────────────────────────────────────╯"
    
    inprogress_rows=$(python3 - "$project_cache" <<'PY'
import json
import sys

rows = []
for proj in json.load(open(sys.argv[1])):
    if proj.get("has_features") and proj.get("feature_pct", 0) < 100:
        rows.append((proj["feature_pct"], proj["passing"], proj["name"], proj["path"]))

rows.sort(key=lambda row: (row[0], row[1]), reverse=True)
for pct, passing, name, path in rows[:15]:
    print(f"{pct}\t{passing}\t{name}\t{path}")
PY
)
    if [ -z "$inprogress_rows" ]; then
        echo "    Waiting for initializer to finish generating tests               "
    else
        while IFS=$'\t' read -r pct passing name proj; do
            [ -z "$pct" ] && continue
            bar=$(progress_bar "$pct")
            icon="🔴"
            [ "$pct" -ge 50 ] && icon="🟡"
            printf "    %s %-22s %s %3d%%\n" "$icon" "${name:0:22}" "$bar" "$pct"
            printf "       %s\n" "$proj"
        done <<< "$inprogress_rows"
    fi
    
    echo ""
    echo "╭──────────────────────────────────────────────────────────────────────────╮"
    echo "│  ✅ COMPLETED                                                            │"
    echo "╰──────────────────────────────────────────────────────────────────────────╯"
    
    completed_rows=$(python3 - "$project_cache" <<'PY'
import json
import sys

rows = []
for proj in json.load(open(sys.argv[1])):
    if proj.get("feature_pct", 0) >= 100:
        if proj.get("qa_total", 0) > 0 and proj.get("qa_pct", 0) >= 100:
            continue
        rows.append((
            proj["name"],
            proj["path"],
            proj.get("qa_pct", 0),
            proj.get("qa_verified", 0),
            proj.get("qa_total", 0),
            proj.get("feature_pct", 0),
            proj.get("passing", 0)
        ))

rows.sort(key=lambda row: (row[2], row[3], row[6]), reverse=True)
for row in rows[:12]:
    print("\t".join(str(part) for part in row))
PY
)
    if [ -z "$completed_rows" ]; then
        echo "    None yet                                                        "
    else
        while IFS=$'\t' read -r name path qa_pct qa_verified qa_total feature_pct passing; do
            [ -z "$name" ] && continue
            qa_total=${qa_total:-0}
            qa_pct=${qa_pct:-0}
            if [ "$qa_total" -gt 0 ]; then
                bar=$(progress_bar "$qa_pct")
                printf "    %-30s QA: %s %3d%% (%s/%s)\n" "${name:0:30}" "$bar" "$qa_pct" "$qa_verified" "$qa_total"
            else
                printf "    %-30s QA: awaiting (0 checks)\n" "${name:0:30}"
            fi
            printf "       Features: %3d%% (%s/300) │ %s\n" "$feature_pct" "$passing" "$path"
        done <<< "$completed_rows"
    fi
    
    echo ""
    echo "                         $(date '+%H:%M:%S')  │  Ctrl+C to exit           "
    
    rm -f "$project_cache" "$process_cache"
    project_cache=""
    process_cache=""
    sleep 2
done
