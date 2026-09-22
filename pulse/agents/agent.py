"""
Codex Agent Session Logic
=========================

Core agent interaction functions for running autonomous coding sessions
using Codex CLI (like kiro-cli but for OpenAI GPT).
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

from progress import print_session_header, print_progress_summary, count_passing_tests
from prompts import copy_spec_to_project
from qa_checklist import reset_qa_checklist, run_auto_verification, count_qa_progress, mark_qa_check


# Configuration
AUTO_CONTINUE_DELAY_SECONDS = 3
MEMORY_SYNC_SCRIPT = Path.home() / ".codex" / "scripts" / "memory_sync.py"
SESSION_OBSERVER_SCRIPT = Path.home() / ".codex" / "scripts" / "session_observer.py"
PROMPTS_DIR = Path.home() / ".codex" / "prompts"


async def cleanup_project_files(project_dir: Path) -> None:
    """Clean up orphan/backup files before starting a session."""
    print("🧹 Cleaning up project files...")
    
    backup_patterns = ["*.backup", "*.bak", "*.old", "*.orig", "*.tmp"]
    deleted = 0
    for pattern in backup_patterns:
        for f in project_dir.rglob(pattern):
            try:
                f.unlink()
                deleted += 1
            except:
                pass
    
    if deleted > 0:
        print(f"   Deleted {deleted} backup/temp files")
    print("   ✅ Cleanup complete\n")


async def start_session_observer(project_dir: Path) -> None:
    """Start session observer for cross-session learning."""
    if SESSION_OBSERVER_SCRIPT.exists():
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", str(SESSION_OBSERVER_SCRIPT), "start", str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except Exception:
            pass


async def stop_session_observer(project_dir: Path) -> None:
    """Stop session observer and save insights."""
    if SESSION_OBSERVER_SCRIPT.exists():
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", str(SESSION_OBSERVER_SCRIPT), "stop", str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, _ = await proc.communicate()
            if out:
                print(out.decode().strip())
        except Exception:
            pass


async def sync_memory_pre_session(project_dir: Path) -> None:
    """Sync memory before session starts."""
    if MEMORY_SYNC_SCRIPT.exists():
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", str(MEMORY_SYNC_SCRIPT), "pre", str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except Exception:
            pass


async def sync_memory_post_session(project_dir: Path) -> None:
    """Sync memory after session ends."""
    if MEMORY_SYNC_SCRIPT.exists():
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", str(MEMORY_SYNC_SCRIPT), "post", str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except Exception:
            pass


async def update_finder_tag(project_dir: Path) -> None:
    """Update Finder tag based on completion status."""
    tag_script = project_dir / "update_tag.sh"
    if tag_script.exists():
        try:
            proc = await asyncio.create_subprocess_exec(
                "bash", str(tag_script),
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, _ = await proc.communicate()
            if out:
                print(out.decode().strip())
            return
        except Exception:
            pass
    
    # Fallback: Set tag directly based on feature count
    passing, total = count_passing_tests(project_dir)
    
    if passing >= 300:
        tag = "Green"
    elif passing >= 150:
        tag = "Orange"
    elif passing >= 30:
        tag = "Yellow"
    else:
        tag = "Red"
    
    try:
        import plistlib
        tag_data = plistlib.dumps([tag])
        proc = await asyncio.create_subprocess_exec(
            "xattr", "-wx", "com.apple.metadata:_kMDItemUserTags",
            tag_data.hex(),
            str(project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        print(f"   🏷️  Set Finder tag: {tag} ({passing}/300)")
    except Exception as e:
        print(f"   ⚠️  Could not set Finder tag: {e}")


async def build_and_install(project_dir: Path) -> bool:
    """Build and install the iOS app."""
    print("\n🔨 Building iOS app...")
    
    xcodeproj = list(project_dir.glob("*.xcodeproj"))
    if not xcodeproj:
        print("   ❌ No Xcode project found")
        return False
    
    scheme = xcodeproj[0].stem
    
    build_cmd = f'''xcodebuild -project "{xcodeproj[0]}" -scheme "{scheme}" \
        -destination 'generic/platform=iOS' \
        -configuration Release \
        -allowProvisioningUpdates \
        CODE_SIGN_STYLE=Automatic \
        DEVELOPMENT_TEAM=YOUR_TEAM_ID \
        build 2>&1'''
    
    proc = await asyncio.create_subprocess_shell(
        build_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=project_dir,
    )
    out, _ = await proc.communicate()
    build_output = out.decode(errors="ignore")
    
    if proc.returncode != 0:
        print("   ❌ Build failed:")
        lines = build_output.strip().split('\n')
        for line in lines[-20:]:
            print(f"   {line}")
        return False
    
    print("   ✅ Build succeeded!")
    
    # Find and install app
    app_path = None
    derived_data = Path.home() / "Library/Developer/Xcode/DerivedData"
    for app in derived_data.rglob("*.app"):
        if "Release-iphoneos" in str(app) and scheme in str(app.parent.parent.parent):
            app_path = app
            break
    
    if not app_path:
        apps = list(derived_data.rglob(f"*{scheme}*/Build/Products/Release-iphoneos/*.app"))
        if apps:
            app_path = apps[0]
    
    if not app_path:
        print("   ⚠️  Could not find .app to install")
        return True
    
    print(f"\n📱 Installing {app_path.name}...")
    
    device_cmd = '''xcrun devicectl list devices 2>/dev/null | grep -E "iPhone|iPad" | head -1 | awk '{for(i=1;i<=NF;i++) if($i ~ /^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$/) print $i}' '''
    result = subprocess.run(device_cmd, shell=True, capture_output=True, text=True)
    device_id = result.stdout.strip()
    
    if not device_id:
        print("   ⚠️  No device connected - build succeeded but couldn't install")
        return True
    
    install_cmd = f'xcrun devicectl device install app --device "{device_id}" "{app_path}"'
    proc = await asyncio.create_subprocess_shell(
        install_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    
    if proc.returncode == 0:
        print("   ✅ Installed on device!")
        return True
    else:
        print("   ⚠️  Install failed (device may be locked)")
        return True


def get_prompt_file_path(prompt_ref: str) -> Path:
    """Get path to prompt file from @N reference."""
    if prompt_ref.startswith("@"):
        num = prompt_ref[1:]
        prompt_file = PROMPTS_DIR / f"{num}.md"
    else:
        prompt_file = PROMPTS_DIR / prompt_ref
    
    if prompt_file.is_symlink():
        prompt_file = prompt_file.resolve()
    
    return prompt_file


async def run_agent_session(project_dir: Path, is_initializer: bool) -> Tuple[str, str]:
    """
    Run a single Codex CLI agent session.
    Codex uses positional prompt argument with -q for quiet mode.
    """
    # Kill any running simulators
    try:
        await asyncio.create_subprocess_shell(
            "killall Simulator 2>/dev/null || true",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except:
        pass
    
    await cleanup_project_files(project_dir)
    
    # Get prompt file and read content
    if is_initializer:
        prompt_file = get_prompt_file_path("@1")
        agent_type = "initializer"
    else:
        prompt_file = get_prompt_file_path("@2")
        agent_type = "coder"
    
    prompt_content = prompt_file.read_text()

    print(f"Starting codex ({agent_type} mode)...\n")

    try:
        # Codex CLI: positional prompt, --full-auto for autonomous mode
        # Write prompt to temp file to avoid shell escaping issues
        prompt_tmp = project_dir / ".codex_prompt.md"
        prompt_tmp.write_text(prompt_content)
        
        full_cmd = f'codex --full-auto "Follow instructions in .codex_prompt.md"'
        
        shell_cmd = f'''cd "{project_dir}" && {full_cmd}'''

        proc = await asyncio.create_subprocess_shell(
            shell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            executable="/bin/zsh",
        )

        response_text = ""
        
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            decoded = line.decode()
            response_text += decoded
            print(decoded, end="", flush=True)

        await proc.wait()

        print("\n" + "-" * 70 + "\n")
        
        response_tail = response_text[-2000:].lower() if len(response_text) > 2000 else response_text.lower()
        
        if any(phrase in response_tail for phrase in ["no device connected", "device not found"]):
            return ("blocked", response_text)
        elif any(phrase in response_tail for phrase in ["session complete", "end of session", "ending session", "context window", "context limit"]):
            return ("complete", response_text)
        else:
            return ("continue", response_text)

    except Exception as e:
        print(f"Error: {e}")
        return "error", str(e)


async def run_autonomous_agent(project_dir: Path, max_iterations: int = None) -> None:
    """Main autonomous agent loop using Codex CLI."""
    
    print("\n" + "="*60)
    print("  CODEX AUTONOMOUS iOS DEVELOPMENT AGENT")
    print("="*60)
    print(f"  Project: {project_dir}")
    print(f"  Model: gpt-5.2 (via Codex CLI)")
    print("="*60 + "\n")
    
    await cleanup_project_files(project_dir)
    await sync_memory_pre_session(project_dir)
    await start_session_observer(project_dir)
    
    iteration = 0
    is_first_run = True
    
    while True:
        iteration += 1
        if max_iterations and iteration > max_iterations:
            print(f"\n✅ Reached max iterations ({max_iterations})")
            break
        
        passing, total = count_passing_tests(project_dir)
        
        print(f"\n[Iteration {iteration}] Features: {passing}/{total}")
        
        # Check if 100% complete
        if passing >= 300 and passing == total:
            print("\n" + "🌟" * 35)
            print("✨ APP 100% COMPLETE! ✨")
            print("🌟" * 35)
            
            await build_and_install(project_dir)
            await update_finder_tag(project_dir)
            
            # Auto-transition to QA
            print("\n🔄 Auto-transitioning to QA agent...")
            qa_checklist_path = project_dir / "qa_checklist.json"
            if not qa_checklist_path.exists():
                print("📋 Initializing QA checklist...")
                reset_qa_checklist(project_dir)
            
            run_auto_verification(project_dir)
            qa_v, qa_t = count_qa_progress(project_dir)
            
            if qa_v < qa_t:
                print(f"\n🔍 QA: {qa_v}/{qa_t} - Starting automatic QA verification...")
                from agent_qa import _run_autonomous_agent_impl as run_qa_loop
                await run_qa_loop(project_dir, max_iterations=None)
            else:
                print(f"\n✅ QA: {qa_v}/{qa_t} - All checks verified!")
            
            print("\n" + "🌟" * 35)
            print("🎊 PROJECT FULLY COMPLETE! 🎊")
            print("🌟" * 35)
            break
        
        # Determine if initializer or coder
        if total < 150:
            is_first_run = True
        else:
            is_first_run = False
        
        print_session_header(iteration, is_first_run)
        
        status, response = await run_agent_session(project_dir, is_first_run)
        
        passing, total = count_passing_tests(project_dir)
        if total < 150:
            print(f"\n⚠️  Only {total} tests found - staying in initializer mode")
            is_first_run = True
        else:
            is_first_run = False
        
        if status == "blocked":
            print("\n🚫 BLOCKED - Cannot proceed")
            print_progress_summary(project_dir)
            break
        elif status == "error":
            print("\n❌ Error - retrying in 30s...")
            await asyncio.sleep(30)
        elif status == "complete":
            print("\n✅ Session complete")
            await update_finder_tag(project_dir)
            await asyncio.sleep(AUTO_CONTINUE_DELAY_SECONDS)
        else:
            print(f"\n⏳ Continuing in {AUTO_CONTINUE_DELAY_SECONDS}s...")
            await update_finder_tag(project_dir)
            await asyncio.sleep(AUTO_CONTINUE_DELAY_SECONDS)
    
    await stop_session_observer(project_dir)
    await sync_memory_post_session(project_dir)
    
    print("\n" + "="*60)
    print("  SESSION COMPLETE")
    print("="*60)
    print_progress_summary(project_dir)
