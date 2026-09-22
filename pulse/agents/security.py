"""
Security Hooks for iOS Autonomous Coding Agent
===============================================

Pre-tool-use hooks that validate bash commands for security.
Uses an allowlist approach - only explicitly permitted commands can run.
"""

import os
import shlex


# Allowed commands for iOS development tasks
ALLOWED_COMMANDS = {
    # File inspection
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "grep",
    "find",
    "file",
    "du",
    "diff",
    # File operations
    "cp",
    "mv",
    "rm",
    "mkdir",
    "touch",
    "chmod",
    "ln",
    # Directory
    "pwd",
    "cd",
    # Text processing
    "echo",
    "printf",
    "sed",
    "awk",
    "sort",
    "uniq",
    "tr",
    "cut",
    # iOS/Xcode development
    "xcodebuild",
    "xcrun",
    "xcode-select",
    "devicectl",
    "simctl",
    "codesign",
    "security",
    "plutil",
    "defaults",
    "open",
    # Swift/iOS tools
    "swift",
    "swiftc",
    "swift-format",
    "swiftlint",
    "xcpretty",
    # Package managers
    "brew",
    "pod",
    "carthage",
    "mint",
    # Version control
    "git",
    # Process management
    "ps",
    "lsof",
    "sleep",
    "pkill",
    "kill",
    "killall",
    # Script execution
    "bash",
    "sh",
    "zsh",
    "init.sh",
    # Utilities
    "which",
    "whereis",
    "type",
    "date",
    "whoami",
    "hostname",
    "uname",
    "env",
    "export",
    "source",
    "true",
    "false",
    "test",
    "[",
    # Archive/compression
    "zip",
    "unzip",
    "tar",
    "gzip",
    "gunzip",
    # Network (for API testing)
    "curl",
    "wget",
    # JSON processing
    "jq",
    # Make
    "make",
}

# Commands that need additional validation even when in the allowlist
COMMANDS_NEEDING_EXTRA_VALIDATION = {"pkill", "killall", "rm"}


def split_command_segments(command_string: str) -> list[str]:
    """
    Split a compound command into individual command segments.
    """
    import re
    segments = re.split(r"\s*(?:&&|\|\|)\s*", command_string)
    result = []
    for segment in segments:
        sub_segments = re.split(r'(?<!["\'])\s*;\s*(?!["\'])', segment)
        for sub in sub_segments:
            sub = sub.strip()
            if sub:
                result.append(sub)
    return result


def extract_commands(command_string: str) -> list[str]:
    """
    Extract command names from a shell command string.
    """
    commands = []
    import re
    segments = re.split(r'(?<!["\'])\s*;\s*(?!["\'])', command_string)

    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

        try:
            tokens = shlex.split(segment)
        except ValueError:
            return []

        if not tokens:
            continue

        expect_command = True

        for token in tokens:
            if token in ("|", "||", "&&", "&"):
                expect_command = True
                continue

            if token in (
                "if", "then", "else", "elif", "fi", "for", "while", "until",
                "do", "done", "case", "esac", "in", "!", "{", "}", "[[", "]]",
            ):
                continue

            if token.startswith("-"):
                continue

            if "=" in token and not token.startswith("="):
                continue

            if expect_command:
                cmd = os.path.basename(token)
                commands.append(cmd)
                expect_command = False

    return commands


def validate_pkill_command(command_string: str) -> tuple[bool, str]:
    """
    Validate pkill commands - only allow killing dev-related processes.
    """
    allowed_process_names = {
        "Xcode",
        "Simulator",
        "xcodebuild",
        "swift",
        "lldb",
        "IBAgent",
        "SourceKitService",
    }

    try:
        tokens = shlex.split(command_string)
    except ValueError:
        return False, "Could not parse pkill command"

    if not tokens:
        return False, "Empty pkill command"

    args = []
    for token in tokens[1:]:
        if not token.startswith("-"):
            args.append(token)

    if not args:
        return False, "pkill requires a process name"

    target = args[-1]
    if " " in target:
        target = target.split()[0]

    if target in allowed_process_names:
        return True, ""
    return False, f"pkill only allowed for dev processes: {allowed_process_names}"


def validate_rm_command(command_string: str) -> tuple[bool, str]:
    """
    Validate rm commands - block dangerous patterns.
    """
    try:
        tokens = shlex.split(command_string)
    except ValueError:
        return False, "Could not parse rm command"

    dangerous_patterns = ["/", "~", "$HOME", "*", ".."]
    
    for token in tokens[1:]:
        if token.startswith("-"):
            continue
        # Block rm on root, home, or with wildcards at root level
        for pattern in dangerous_patterns:
            if token == pattern or token.startswith("/*") or token == "~/*":
                return False, f"rm blocked for safety: {token}"
    
    return True, ""


def get_command_for_validation(cmd: str, segments: list[str]) -> str:
    """Find the specific command segment that contains the given command."""
    for segment in segments:
        segment_commands = extract_commands(segment)
        if cmd in segment_commands:
            return segment
    return ""


async def bash_security_hook(input_data, tool_use_id=None, context=None):
    """
    Pre-tool-use hook that validates bash commands using an allowlist.
    """
    if input_data.get("tool_name") != "Bash":
        return {}

    command = input_data.get("tool_input", {}).get("command", "")
    if not command:
        return {}

    commands = extract_commands(command)

    if not commands:
        return {
            "decision": "block",
            "reason": f"Could not parse command for security validation: {command}",
        }

    segments = split_command_segments(command)

    for cmd in commands:
        if cmd not in ALLOWED_COMMANDS:
            return {
                "decision": "block",
                "reason": f"Command '{cmd}' is not in the allowed commands list",
            }

        if cmd in COMMANDS_NEEDING_EXTRA_VALIDATION:
            cmd_segment = get_command_for_validation(cmd, segments)
            if not cmd_segment:
                cmd_segment = command

            if cmd == "pkill" or cmd == "killall":
                allowed, reason = validate_pkill_command(cmd_segment)
                if not allowed:
                    return {"decision": "block", "reason": reason}
            elif cmd == "rm":
                allowed, reason = validate_rm_command(cmd_segment)
                if not allowed:
                    return {"decision": "block", "reason": reason}

    return {}


def run_project_security_audit(project_dir: str) -> dict:
    """
    Run a security audit on the project directory.
    Checks for potentially dangerous patterns in scripts and code.
    
    Args:
        project_dir: Path to the project directory
        
    Returns:
        dict with 'passed', 'warnings', and 'errors' keys
    """
    import subprocess
    from pathlib import Path
    import re
    
    results = {
        "passed": True,
        "warnings": [],
        "errors": [],
        "scanned_files": 0,
    }
    
    project_path = Path(project_dir)
    if not project_path.exists():
        results["errors"].append(f"Project directory does not exist: {project_dir}")
        results["passed"] = False
        return results
    
    # Dangerous patterns to check for in shell scripts
    # Patterns are specific to catch truly dangerous commands, not safe ones like ~/Library/...
    dangerous_patterns = [
        (r"rm\s+-rf\s+/\s", "Dangerous rm -rf / pattern"),
        (r"rm\s+-rf\s+/\*", "Dangerous rm -rf /* pattern"),
        (r"rm\s+-rf\s+~\s", "Dangerous rm -rf ~ pattern"),
        (r"rm\s+-rf\s+~/\s", "Dangerous rm -rf ~/ pattern"),
        (r"rm\s+-rf\s+~/\*", "Dangerous rm -rf ~/* pattern"),
        (r"rm\s+-rf\s+\$HOME\s", "Dangerous rm -rf $HOME pattern"),
        (r"rm\s+-rf\s+\$HOME/\s", "Dangerous rm -rf $HOME/ pattern"),
        (r"rm\s+-rf\s+\$HOME/\*", "Dangerous rm -rf $HOME/* pattern"),
        (r"curl.*\|\s*bash", "Curl pipe to bash pattern"),
        (r"wget.*\|\s*bash", "Wget pipe to bash pattern"),
        (r"eval\s+\$\(", "Eval with command substitution"),
        (r">\s*/dev/sd", "Writing to disk device"),
        (r"mkfs\.", "Filesystem format command"),
        (r"dd\s+if=", "dd command (potentially dangerous)"),
    ]
    
    # Find all shell scripts and check them
    shell_extensions = [".sh", ".bash", ".zsh"]
    for ext in shell_extensions:
        for script_file in project_path.rglob(f"*{ext}"):
            results["scanned_files"] += 1
            try:
                content = script_file.read_text()
                for pattern, description in dangerous_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        results["warnings"].append(
                            f"{script_file.relative_to(project_path)}: {description}"
                        )
            except Exception as e:
                results["warnings"].append(f"Could not read {script_file}: {e}")
    
    # Check for suspicious file permissions (world-writable in sensitive locations)
    try:
        result = subprocess.run(
            ["find", str(project_path), "-type", "f", "-perm", "-002", "-name", "*.sh"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                if line:
                    results["warnings"].append(f"World-writable script: {line}")
    except Exception:
        pass  # Not critical if this check fails
    
    if results["warnings"]:
        print(f"\n⚠️  Security Audit: {len(results['warnings'])} warning(s) found")
        for warning in results["warnings"][:5]:  # Show first 5
            print(f"   - {warning}")
        if len(results["warnings"]) > 5:
            print(f"   ... and {len(results['warnings']) - 5} more")
    else:
        print(f"\n✅ Security Audit: Passed ({results['scanned_files']} files scanned)")
    
    return results
