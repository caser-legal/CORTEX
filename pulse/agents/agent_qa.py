"""
QA Agent Session Logic
======================

Core agent interaction functions for running autonomous QA/beta testing sessions.
Uses qa terminal command instead of q/qi.
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional, Tuple

from progress import print_session_header, print_progress_summary, count_passing_tests
from prompts import copy_spec_to_project
from security import run_project_security_audit
from qa_checklist import (
    reset_qa_checklist, load_qa_checklist, save_qa_checklist,
    count_qa_progress, run_auto_verification, get_qa_failures_for_agent,
    print_qa_progress, get_unverified_checks, mark_qa_check
)


# Configuration
AUTO_CONTINUE_DELAY_SECONDS = 3


async def cleanup_project_files(project_dir: Path) -> None:
    """Clean up orphan/backup files before starting a session."""
    print("🧹 Cleaning up project files...")
    
    # Delete backup/temp files
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
    
    # Check for orphan Swift files (not in Xcode project)
    xcodeproj = list(project_dir.glob("*.xcodeproj"))
    if xcodeproj:
        pbxproj = xcodeproj[0] / "project.pbxproj"
        if pbxproj.exists():
            try:
                proj_content = pbxproj.read_text()
                orphans = []
                for swift_file in project_dir.rglob("*.swift"):
                    if ".build" in str(swift_file) or "DerivedData" in str(swift_file):
                        continue
                    if swift_file.name not in proj_content:
                        orphans.append(swift_file)
                
                if orphans:
                    print(f"   ⚠️  Found {len(orphans)} orphan Swift files (not in Xcode project):")
                    for f in orphans[:5]:
                        print(f"      - {f.relative_to(project_dir)}")
                    if len(orphans) > 5:
                        print(f"      ... and {len(orphans) - 5} more")
            except:
                pass
    
    print("   ✅ Cleanup complete\n")


async def update_finder_tag(project_dir: Path) -> None:
    """Update Finder tag based on test status."""
    try:
        script_path = Path.home() / "Documents" / "iOS" / "update_tag.sh"
        if script_path.exists():
            proc = await asyncio.create_subprocess_shell(
                f'"{script_path}" "{project_dir}"',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.wait()
    except Exception as e:
        print(f"Warning: Could not update Finder tag: {e}")


async def build_and_install(project_dir: Path) -> bool:
    """Build and install app on physical device. Returns True if successful."""
    import glob
    
    print("\n" + "=" * 70)
    print("  BUILDING AND INSTALLING ON DEVICE")
    print("=" * 70 + "\n")
    
    # Find xcodeproj
    xcodeprojs = glob.glob(str(project_dir / "*.xcodeproj"))
    if not xcodeprojs:
        print("❌ No .xcodeproj found")
        return False
    
    xcodeproj = xcodeprojs[0]
    
    # Get all schemes and pick the main iOS one (skip Watch, Widget, etc.)
    import subprocess
    result = subprocess.run(
        f'xcodebuild -project "{xcodeproj}" -list 2>/dev/null | grep -A 100 "Schemes:" | tail -n +2 | grep -v "^$"',
        shell=True, capture_output=True, text=True
    )
    schemes = [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]
    
    # Filter out Watch, Widget, Extension schemes - pick main app
    skip_keywords = ['watch', 'widget', 'extension', 'intent', 'share', 'notification']
    main_schemes = [s for s in schemes if not any(kw in s.lower() for kw in skip_keywords)]
    
    if main_schemes:
        scheme = main_schemes[0]
    elif schemes:
        scheme = schemes[0]  # Fallback to first if no main found
    else:
        scheme = Path(xcodeproj).stem
    
    print(f"📦 Building {scheme}...")
    
    # Clean first to ensure fresh build (prevents stale cached builds)
    clean_cmd = f'''xcodebuild -project "{xcodeproj}" -scheme "{scheme}" clean 2>&1'''
    proc = await asyncio.create_subprocess_shell(
        clean_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=project_dir,
    )
    await proc.communicate()
    
    # Build
    build_cmd = f'''xcodebuild -project "{xcodeproj}" -scheme "{scheme}" \
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
        print("❌ Build failed:")
        lines = build_output.strip().split('\n')
        for line in lines[-30:]:
            print(f"  {line}")
        return False
    
    print("✅ Build succeeded!")
    
    # Mark build QA checks as verified
    mark_qa_check(project_dir, "build_succeeds", True, "Build succeeded with 0 errors")
    # Check for warnings in build output
    warning_count = build_output.lower().count("warning:")
    if warning_count == 0:
        mark_qa_check(project_dir, "no_warnings", True, "Build has 0 warnings")
    else:
        mark_qa_check(project_dir, "no_warnings", False, f"Build has {warning_count} warnings")
    
    # Find the .app
    app_path = None
    derived_data = Path.home() / "Library/Developer/Xcode/DerivedData"
    for dd in derived_data.iterdir():
        if scheme.replace(" ", "_").replace("-", "_").lower() in dd.name.lower():
            app_dir = dd / "Build/Products/Release-iphoneos"
            apps = list(app_dir.glob("*.app"))
            if apps:
                app_path = apps[0]
                break
    
    if not app_path:
        print("⚠️  Could not find .app to install")
        return True
    
    print(f"\n📱 Installing {app_path.name}...")
    
    # Get device UUID
    device_cmd = '''xcrun devicectl list devices 2>/dev/null | grep -E "iPhone|iPad" | head -1 | awk '{for(i=1;i<=NF;i++) if($i ~ /^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$/) print $i}' '''
    result = subprocess.run(device_cmd, shell=True, capture_output=True, text=True)
    device_id = result.stdout.strip()
    
    if not device_id:
        print("⚠️  No device connected - build succeeded but couldn't install")
        return True
    
    # Install
    install_cmd = f'xcrun devicectl device install app --device "{device_id}" "{app_path}"'
    proc = await asyncio.create_subprocess_shell(
        install_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    
    if proc.returncode == 0:
        print("✅ Installed on device!")
        # Mark runtime QA checks as verified (app installed = can launch)
        mark_qa_check(project_dir, "app_launches", True, "App installed successfully on device")
        mark_qa_check(project_dir, "app_runs_5s", True, "App installed - assumed stable")
        return True
    else:
        print("⚠️  Install failed (device may be locked):")
        print(f"  {out.decode(errors='ignore')[:200]}")
        return True


async def run_agent_session(project_dir: Path) -> Tuple[str, str]:
    """
    Run a single QA agent session.

    Returns:
        (status, response_text) where status is:
        - "continue" if agent should continue working immediately
        - "complete" if agent finished this session normally
        - "error" if an error occurred
    """
    # Kill any running simulators before starting
    try:
        await asyncio.create_subprocess_shell(
            "killall Simulator 2>/dev/null || true",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except:
        pass

    # Clean up orphan/backup files before starting
    await cleanup_project_files(project_dir)

    print(f"Starting QA agent with prompt @3...\n")

    try:
        # Get prompt file and read content
        prompt_file = Path.home() / ".codex" / "prompts" / "3.md"
        if prompt_file.is_symlink():
            prompt_file = prompt_file.resolve()
        prompt_content = prompt_file.read_text()

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
        
        # Only check the LAST part of output (Claude's response, not the prompt echo)
        response_tail = response_text[-2000:].lower() if len(response_text) > 2000 else response_text.lower()
        
        # BLOCKED patterns - only critical hardware issues
        blocked_patterns = [
            "no device connected", "device not found",
        ]
        if any(phrase in response_tail for phrase in blocked_patterns):
            return "blocked", response_text
        
        # Stop signals - must appear in actual response, not prompt
        if any(phrase in response_tail for phrase in [
            "session complete",
            "qa session complete",
            "qa complete",
            "end of session",
            "ending session",
            "context window",
            "context limit",
        ]):
            return "complete", response_text
        
        return "continue", response_text

    except Exception as e:
        print(f"Error during QA session: {e}")
        return "error", str(e)


async def run_autonomous_agent(
    project_dir: Path,
    max_iterations: Optional[int] = None,
) -> None:
    """
    Run the autonomous QA agent loop.
    """
    async def kill_simulators_loop():
        while True:
            try:
                await asyncio.create_subprocess_shell(
                    "killall Simulator 2>/dev/null || true",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            except:
                pass
            await asyncio.sleep(5)
    
    simulator_killer = asyncio.create_task(kill_simulators_loop())
    
    try:
        await _run_autonomous_agent_impl(project_dir, max_iterations)
    finally:
        simulator_killer.cancel()


async def _run_autonomous_agent_impl(
    project_dir: Path,
    max_iterations: Optional[int] = None,
) -> None:
    """
    Implementation of autonomous QA agent loop.
    """
    print("\n" + "=" * 70)
    print("  KIRO AUTONOMOUS QA / BETA TESTER AGENT")
    print("=" * 70)
    print(f"\nProject directory: {project_dir}")
    if max_iterations:
        print(f"Max iterations: {max_iterations}")
    else:
        print("Max iterations: Unlimited (will run until QA complete)")
    print()
    print("⚠️  Simulator auto-kill enabled (checks every 5s)")
    print("🔍 Mode: QA / Beta Testing / Senior iOS Reviewer")
    
    # Run security audit before starting
    print("\n🔒 Running security audit...")
    security_results = run_project_security_audit(str(project_dir))
    if security_results["errors"]:
        print("❌ Security audit failed with errors:")
        for error in security_results["errors"]:
            print(f"   - {error}")
        return
    print()

    # Check project has feature_list.json (should already be built)
    tests_file = project_dir / "feature_list.json"
    passing, total = count_passing_tests(project_dir)
    
    if not tests_file.exists():
        print("❌ No feature_list.json found!")
        print("   Run autoo first to build the app, then run autoqa.")
        return
    
    # Check if QA checklist exists and has any agent-verified checks
    qa_verified, qa_total = count_qa_progress(project_dir)
    checklist_path = project_dir / "qa_checklist.json"
    agent_verified_marker = project_dir / ".qa_agent_verified"
    
    if qa_verified == qa_total and qa_total > 0:
        print(f"\n✅ QA already 100% complete ({qa_verified}/{qa_total}) - skipping reset")
        print("   To force re-verification, delete qa_checklist.json")
    elif not checklist_path.exists():
        # No checklist yet - create fresh one
        print("\n🔄 Creating QA verification checklist...")
        reset_qa_checklist(project_dir)
    else:
        # Checklist exists but not 100% - DON'T reset, just re-run auto-verification
        # This preserves any agent-verified manual checks (runtime, build)
        print(f"\n📋 QA checklist exists ({qa_verified}/{qa_total} verified) - preserving manual checks")
    
    # CRITICAL: Skip auto-verification if agent has already verified
    # This prevents the infinite loop where auto-verification overwrites agent findings
    if agent_verified_marker.exists():
        print("\n✅ Agent has verified features - skipping auto-verification")
        print("   (Delete .qa_agent_verified to force re-verification)")
    else:
        print("\n🔍 Running auto-verification of features...")
        run_auto_verification(project_dir)
    
    # Show both progress bars
    print_progress_summary(project_dir, include_qa=True)
    
    # Check if QA is actually 100% complete (not just marker exists)
    qa_verified, qa_total = count_qa_progress(project_dir)
    verified_marker = project_dir / ".qa_verified"
    
    if qa_total > 0 and qa_verified == qa_total:
        # QA is actually 100% - we're done
        print(f"\n✅ QA verification complete ({qa_verified}/{qa_total})")
        if not verified_marker.exists():
            # Create marker now that QA is truly complete
            with open(verified_marker, "w") as f:
                f.write(f"QA verified: {qa_verified}/{qa_total} checks passed\n")
                from datetime import datetime
                f.write(f"Verified at: {datetime.now().isoformat()}\n")
            print("   Created .qa_verified marker")
        return
    elif verified_marker.exists():
        # Marker exists but QA is NOT 100% - this is the bug!
        # Delete the premature marker and continue with QA
        print(f"\n⚠️  Found .qa_verified marker but QA is only {qa_verified}/{qa_total}")
        print("   Removing premature marker and continuing QA verification...")
        verified_marker.unlink()
    
    # Write QA failures to file for agent to see
    qa_failures = get_qa_failures_for_agent(project_dir)
    qa_fixes_path = project_dir / "qa-fixes.txt"
    with open(qa_fixes_path, "w") as f:
        f.write(qa_failures)
    print(f"\n📝 Wrote QA verification failures to qa-fixes.txt")

    # Main loop
    iteration = 0
    max_preflight_attempts = 3  # Limit preflight retries
    preflight_attempts = 0

    while True:
        iteration += 1

        if max_iterations and iteration > max_iterations:
            print(f"\nReached max iterations ({max_iterations})")
            break

        # Check BOTH feature progress AND QA verification
        passing, total = count_passing_tests(project_dir)
        qa_verified, qa_total = count_qa_progress(project_dir)
        
        # CRITICAL: 300 minimum features required for completion
        MIN_FEATURES = 300
        features_complete = total > 0 and passing == total and passing >= MIN_FEATURES
        
        # If features are complete but build/runtime checks not verified, run build now
        # This auto-verifies the build/runtime QA checks
        checklist = load_qa_checklist(project_dir)
        build_verified = any(c.get("id") == "build_succeeds" and c.get("verified") for c in checklist)
        
        if features_complete and not build_verified:
            print("\n🔨 Running build to verify build/runtime QA checks...")
            build_success = await build_and_install(project_dir)
            if build_success and not agent_verified_marker.exists():
                # Re-run auto-verification to update qa-fixes.txt (only if agent hasn't verified)
                run_auto_verification(project_dir)
        
        # Re-check QA progress after potential build verification
        qa_verified, qa_total = count_qa_progress(project_dir)
        qa_complete = qa_total > 0 and qa_verified == qa_total
        
        if features_complete and qa_complete:
            # Run UI preflight check before declaring complete
            preflight_script = Path.home() / ".kiro" / "scripts" / "ui_preflight.py"
            autofix_script = Path.home() / ".kiro" / "scripts" / "ui_autofix.py"
            
            if preflight_script.exists():
                preflight = await asyncio.create_subprocess_shell(
                    f'python3 "{preflight_script}" "{project_dir}"',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                out, _ = await preflight.communicate()
                preflight_output = out.decode(errors="ignore")
                
                if preflight.returncode != 0:
                    print(preflight_output)
                    
                    # Try auto-fix first
                    if autofix_script.exists():
                        print("\n🔧 Running UI auto-fixer...\n")
                        autofix = await asyncio.create_subprocess_shell(
                            f'python3 "{autofix_script}" "{project_dir}"',
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.STDOUT,
                        )
                        fix_out, _ = await autofix.communicate()
                        print(fix_out.decode(errors="ignore"))
                        
                        # Re-run preflight after auto-fix
                        preflight2 = await asyncio.create_subprocess_shell(
                            f'python3 "{preflight_script}" "{project_dir}"',
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.STDOUT,
                        )
                        out2, _ = await preflight2.communicate()
                        preflight_output = out2.decode(errors="ignore")
                        
                        if preflight2.returncode != 0:
                            print(preflight_output)
                            # Write remaining issues to qa-fixes.txt for agent to see
                            qa_fixes_path = project_dir / "qa-fixes.txt"
                            with open(qa_fixes_path, "w") as f:
                                f.write("# UI PREFLIGHT ISSUES - FIX THESE BEFORE COMPLETION\n\n")
                                f.write(preflight_output)
                                f.write("\n\n# Instructions:\n")
                                f.write("# Fix each issue listed above in the Swift files.\n")
                                f.write("# Delete this file when all issues are resolved.\n")
                            print(f"\n📝 Wrote remaining issues to qa-fixes.txt")
                            print("❌ UI preflight still failing — QA session will fix these.\n")
                            # Run QA session to fix issues
                            print(f"\n{'=' * 70}")
                            print(f"  QA SESSION {iteration} (fixing preflight issues)")
                            print(f"{'=' * 70}\n")
                            status, response = await run_agent_session(project_dir)
                            if status == "quota":
                                print("\n❌ FREE TIER QUOTA EXHAUSTED")
                                break
                            await update_finder_tag(project_dir)
                            await asyncio.sleep(AUTO_CONTINUE_DELAY_SECONDS)
                            continue  # Re-check preflight
                        else:
                            print("\n✅ Auto-fix resolved all issues!\n")
                    else:
                        # No autofix available, write issues for agent
                        qa_fixes_path = project_dir / "qa-fixes.txt"
                        with open(qa_fixes_path, "w") as f:
                            f.write("# UI PREFLIGHT ISSUES - FIX THESE BEFORE COMPLETION\n\n")
                            f.write(preflight_output)
                        print(f"\n📝 Wrote issues to qa-fixes.txt")
                        print("❌ UI preflight failed — QA session will fix these.\n")
                        # Run QA session to fix issues
                        print(f"\n{'=' * 70}")
                        print(f"  QA SESSION {iteration} (fixing preflight issues)")
                        print(f"{'=' * 70}\n")
                        status, response = await run_agent_session(project_dir)
                        await update_finder_tag(project_dir)
                        await asyncio.sleep(AUTO_CONTINUE_DELAY_SECONDS)
                        continue  # Re-check preflight
                else:
                    # Preflight passed - truly complete!
                    print("\n" + "🌟" * 35)
                    print("🎉" * 35)
                    print("✨ APP 100% COMPLETE - ALL QA VERIFIED! ✨")
                    print("🎉" * 35)
                    print("🌟" * 35)
                    print(f"\n✅ Features: {passing}/{total} (100%)")
                    print(f"✅ QA Verified: {qa_verified}/{qa_total} (100%)")
                    
                    # Create .qa_verified marker NOW that QA is truly complete
                    verified_marker = project_dir / ".qa_verified"
                    with open(verified_marker, "w") as f:
                        f.write(f"QA verified: {qa_verified}/{qa_total} checks passed\n")
                        f.write(f"Features: {passing}/{total} passing\n")
                        from datetime import datetime
                        f.write(f"Verified at: {datetime.now().isoformat()}\n")
                    print("✅ Created .qa_verified marker")
                    
                    await build_and_install(project_dir)
                    await update_finder_tag(project_dir)
                    break
            else:
                # No preflight script - just complete
                print("\n" + "🌟" * 35)
                print("🎉" * 35)
                print("✨ APP 100% COMPLETE - ALL QA VERIFIED! ✨")
                print("🎉" * 35)
                print("🌟" * 35)
                print(f"\n✅ Features: {passing}/{total} (100%)")
                print(f"✅ QA Verified: {qa_verified}/{qa_total} (100%)")
                
                # Create .qa_verified marker NOW that QA is truly complete
                verified_marker = project_dir / ".qa_verified"
                with open(verified_marker, "w") as f:
                    f.write(f"QA verified: {qa_verified}/{qa_total} checks passed\n")
                    f.write(f"Features: {passing}/{total} passing\n")
                    from datetime import datetime
                    f.write(f"Verified at: {datetime.now().isoformat()}\n")
                print("✅ Created .qa_verified marker")
                
                await build_and_install(project_dir)
                await update_finder_tag(project_dir)
                break
        
        # If features complete but QA not complete, show what's missing
        if features_complete and not qa_complete:
            print(f"\n⚠️  Features 100% but QA verification incomplete!")
            print(f"    Features: {passing}/{total} ✓")
            print(f"    QA Verified: {qa_verified}/{qa_total} ✗")
            print("\n    Missing QA checks:")
            unverified = get_unverified_checks(project_dir)
            for check in unverified[:10]:  # Show first 10
                print(f"    - {check['description']}")
            if len(unverified) > 10:
                print(f"    ... and {len(unverified) - 10} more")
            print()

        # Print session header
        print(f"\n{'=' * 70}")
        print(f"  QA SESSION {iteration}")
        print(f"{'=' * 70}\n")

        # Run QA session
        status, response = await run_agent_session(project_dir)
        
        # Re-run auto-verification after session to update QA progress
        # BUT skip if agent has verified (prevents infinite loop)
        if not agent_verified_marker.exists():
            run_auto_verification(project_dir)
        else:
            print("\n✅ Skipping auto-verification (agent has verified)")

        # Check if QA session resulted in 100% completion (BOTH bars)
        passing, total = count_passing_tests(project_dir)
        qa_verified, qa_total = count_qa_progress(project_dir)
        
        # CRITICAL: 300 minimum features required for completion
        MIN_FEATURES = 300
        features_complete = total > 0 and passing == total and passing >= MIN_FEATURES
        qa_complete = qa_total > 0 and qa_verified == qa_total
        
        if features_complete and qa_complete:
            print("\n" + "🔍" * 17)
            print("✨ QA COMPLETE - ALL CHECKS VERIFIED! ✨")
            print("🔍" * 17)
            print(f"\n✅ Features: {passing}/{total} (100%)")
            print(f"✅ QA Verified: {qa_verified}/{qa_total} (100%)")
            print("\nNo further QA sessions needed.")
            
            # Create .qa_verified marker NOW that QA is truly complete
            verified_marker = project_dir / ".qa_verified"
            with open(verified_marker, "w") as f:
                f.write(f"QA verified: {qa_verified}/{qa_total} checks passed\n")
                f.write(f"Features: {passing}/{total} passing\n")
                from datetime import datetime
                f.write(f"Verified at: {datetime.now().isoformat()}\n")
            print("✅ Created .qa_verified marker")
            
            await build_and_install(project_dir)
            await update_finder_tag(project_dir)
            break

        # Handle status
        if status == "blocked":
            print("\n🚫 BLOCKED - Task requires Apple entitlement/approval")
            print_progress_summary(project_dir, include_qa=True)
            break
            
        elif status == "complete":
            print("\n✓ QA session completed")
            print_progress_summary(project_dir, include_qa=True)
            await update_finder_tag(project_dir)
            print(f"\nWaiting {AUTO_CONTINUE_DELAY_SECONDS}s before next session...")
            await asyncio.sleep(AUTO_CONTINUE_DELAY_SECONDS)
            
        elif status == "continue":
            print(f"\nQA will auto-continue in {AUTO_CONTINUE_DELAY_SECONDS}s...")
            print_progress_summary(project_dir, include_qa=True)
            await update_finder_tag(project_dir)
            await asyncio.sleep(AUTO_CONTINUE_DELAY_SECONDS)

        elif status == "error":
            print("\nSession encountered an error - retrying...")
            await asyncio.sleep(AUTO_CONTINUE_DELAY_SECONDS)

        if max_iterations is None or iteration < max_iterations:
            # Check if agent verified issues as false positives
            # Don't overwrite qa-fixes.txt if agent said "no work needed" or similar
            response_lower = response.lower() if response else ""
            agent_verified = any(phrase in response_lower for phrase in [
                "no more work needed",
                "no work needed", 
                "already complete",
                "100% complete",
                "false positive",
                "verified complete",
            ])
            
            # Check for .qa_verified marker
            verified_marker = project_dir / ".qa_verified"
            if verified_marker.exists():
                agent_verified = True
            
            if not agent_verified:
                # Only update qa-fixes.txt if agent hasn't verified
                qa_failures = get_qa_failures_for_agent(project_dir)
                qa_fixes_path = project_dir / "qa-fixes.txt"
                with open(qa_fixes_path, "w") as f:
                    f.write(qa_failures)
            else:
                print("\n✅ Agent verified issues - not overwriting qa-fixes.txt")
            
            print("\nPreparing next QA session...\n")
            await asyncio.sleep(1)

    # Final summary
    print("\n" + "=" * 70)
    print("  QA COMPLETE")
    print("=" * 70)
    print(f"\nProject directory: {project_dir}")
    print_progress_summary(project_dir, include_qa=True)
    await update_finder_tag(project_dir)

    print("\n" + "🌟" * 35)
    print("✨ QA DONE! ✨")
    print("🌟" * 35)
