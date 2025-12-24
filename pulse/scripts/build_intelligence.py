#!/usr/bin/env python3
"""
Build Intelligence - Self-improving build error resolution
==========================================================

Capabilities:
1. Parse and classify build errors
2. Generate fixes based on error patterns
3. Learn from successful fixes (update pattern memory)
4. Adaptive retry loop

Usage:
    python3 build_intelligence.py /path/to/app          # Analyze + fix
    python3 build_intelligence.py /path/to/app --learn  # Update patterns from success
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from file_lock import file_lock

# Pattern memory file
PATTERN_MEMORY = Path.home() / ".codex" / "memory" / "build_patterns.json"

# Known error patterns and their fixes
DEFAULT_PATTERNS = {
    "missing_import": {
        "regex": r"cannot find '(\w+)' in scope",
        "fix_type": "add_import",
        "description": "Missing type - needs import"
    },
    "type_mismatch": {
        "regex": r"cannot convert value of type '(\w+)' to expected argument type '(\w+)'",
        "fix_type": "type_conversion",
        "description": "Type mismatch"
    },
    "missing_argument": {
        "regex": r"missing argument for parameter '(\w+)'",
        "fix_type": "add_argument",
        "description": "Missing required argument"
    },
    "undefined_member": {
        "regex": r"value of type '(\w+)' has no member '(\w+)'",
        "fix_type": "check_api",
        "description": "Undefined member access"
    },
    "ambiguous_reference": {
        "regex": r"ambiguous use of '(\w+)'",
        "fix_type": "disambiguate",
        "description": "Ambiguous reference"
    },
    "protocol_conformance": {
        "regex": r"type '(\w+)' does not conform to protocol '(\w+)'",
        "fix_type": "add_conformance",
        "description": "Missing protocol conformance"
    },
    "immutable_value": {
        "regex": r"cannot assign to property: '(\w+)' is a '(let|get-only)' property",
        "fix_type": "make_mutable",
        "description": "Trying to mutate immutable value"
    },
    "optional_unwrap": {
        "regex": r"value of optional type '(\w+)\?' must be unwrapped",
        "fix_type": "unwrap_optional",
        "description": "Optional needs unwrapping"
    },
    "missing_return": {
        "regex": r"missing return in (closure|function) expected to return '(\w+)'",
        "fix_type": "add_return",
        "description": "Missing return statement"
    },
    "duplicate_definition": {
        "regex": r"invalid redeclaration of '(\w+)'",
        "fix_type": "remove_duplicate",
        "description": "Duplicate definition"
    }
}

class BuildIntelligence:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.patterns = self._load_patterns()
        self.errors: List[Dict] = []
        self.fixes_applied: List[Dict] = []
        
    def _load_patterns(self) -> Dict:
        """Load patterns from memory, merge with defaults."""
        patterns = DEFAULT_PATTERNS.copy()
        if PATTERN_MEMORY.exists():
            try:
                with open(PATTERN_MEMORY) as f:
                    learned = json.load(f)
                    # Merge learned patterns (they take priority)
                    patterns.update(learned.get("patterns", {}))
            except:
                pass
        return patterns
    
    def _save_patterns(self):
        """Save updated patterns to memory."""
        PATTERN_MEMORY.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "patterns": self.patterns,
            "last_updated": datetime.now().isoformat(),
            "total_fixes": len(self.fixes_applied)
        }
        with file_lock(PATTERN_MEMORY):
            with open(PATTERN_MEMORY, 'w') as f:
                json.dump(data, f, indent=2)
    
    def build(self) -> Tuple[bool, str]:
        """Run xcodebuild and capture output."""
        xcodeproj = list(self.project_dir.glob("*.xcodeproj"))
        if not xcodeproj:
            return False, "No .xcodeproj found"
        
        # Get scheme
        result = subprocess.run(
            f'xcodebuild -project "{xcodeproj[0]}" -list 2>/dev/null | grep -A 100 "Schemes:" | tail -n +2 | head -5',
            shell=True, capture_output=True, text=True, cwd=self.project_dir
        )
        schemes = [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]
        scheme = schemes[0] if schemes else xcodeproj[0].stem
        
        # Build
        cmd = f'xcodebuild -project "{xcodeproj[0]}" -scheme "{scheme}" -destination "generic/platform=iOS" build 2>&1'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=self.project_dir)
        
        success = result.returncode == 0 or "BUILD SUCCEEDED" in result.stdout
        return success, result.stdout
    
    def parse_errors(self, build_output: str) -> List[Dict]:
        """Extract and classify errors from build output."""
        self.errors = []
        
        # Match error lines: /path/file.swift:line:col: error: message
        error_pattern = r'([^:\s]+\.swift):(\d+):(\d+): error: (.+)'
        
        for match in re.finditer(error_pattern, build_output):
            filepath, line, col, message = match.groups()
            
            error = {
                "file": filepath,
                "line": int(line),
                "col": int(col),
                "message": message,
                "category": "unknown",
                "fix_type": None
            }
            
            # Classify error
            for name, pattern in self.patterns.items():
                if re.search(pattern["regex"], message, re.IGNORECASE):
                    error["category"] = name
                    error["fix_type"] = pattern["fix_type"]
                    error["pattern_match"] = re.search(pattern["regex"], message, re.IGNORECASE).groups()
                    break
            
            self.errors.append(error)
        
        return self.errors
    
    def generate_fix_prompt(self, error: Dict) -> str:
        """Generate a prompt for the agent to fix this error."""
        prompts = {
            "add_import": f"Add missing import for '{error.get('pattern_match', ['unknown'])[0]}' in {error['file']}",
            "type_conversion": f"Fix type mismatch at {error['file']}:{error['line']} - convert types appropriately",
            "add_argument": f"Add missing argument '{error.get('pattern_match', ['unknown'])[0]}' at {error['file']}:{error['line']}",
            "check_api": f"Check API usage at {error['file']}:{error['line']} - member doesn't exist",
            "unwrap_optional": f"Safely unwrap optional at {error['file']}:{error['line']}",
            "add_conformance": f"Add protocol conformance at {error['file']}:{error['line']}",
            "make_mutable": f"Change let to var or use @State at {error['file']}:{error['line']}",
            "add_return": f"Add return statement at {error['file']}:{error['line']}",
            "remove_duplicate": f"Remove duplicate definition at {error['file']}:{error['line']}",
        }
        return prompts.get(error.get("fix_type"), f"Fix error at {error['file']}:{error['line']}: {error['message']}")
    
    def auto_fix_simple(self, error: Dict) -> bool:
        """Attempt automatic fix for simple patterns."""
        if error["fix_type"] == "unwrap_optional":
            return self._fix_optional_unwrap(error)
        elif error["fix_type"] == "make_mutable":
            return self._fix_immutable(error)
        return False
    
    def _fix_optional_unwrap(self, error: Dict) -> bool:
        """Add optional chaining or nil coalescing."""
        filepath = self.project_dir / error["file"]
        if not filepath.exists():
            # Try finding file
            matches = list(self.project_dir.rglob(Path(error["file"]).name))
            if matches:
                filepath = matches[0]
            else:
                return False
        
        lines = filepath.read_text().split('\n')
        line_idx = error["line"] - 1
        if line_idx >= len(lines):
            return False
        
        line = lines[line_idx]
        # Simple fix: add ? for optional chaining
        # This is a heuristic - complex cases need agent intervention
        if '.' in line and '?' not in line:
            # Find the variable being accessed
            fixed = re.sub(r'(\w+)\.(\w+)', r'\1?.\2', line, count=1)
            if fixed != line:
                lines[line_idx] = fixed
                filepath.write_text('\n'.join(lines))
                self.fixes_applied.append({"error": error, "fix": "optional_chaining"})
                return True
        return False
    
    def _fix_immutable(self, error: Dict) -> bool:
        """Change let to var."""
        filepath = self.project_dir / error["file"]
        if not filepath.exists():
            matches = list(self.project_dir.rglob(Path(error["file"]).name))
            if matches:
                filepath = matches[0]
            else:
                return False
        
        content = filepath.read_text()
        if error.get("pattern_match"):
            var_name = error["pattern_match"][0]
            # Find and fix the declaration
            fixed = re.sub(rf'\blet\s+{var_name}\b', f'var {var_name}', content, count=1)
            if fixed != content:
                filepath.write_text(fixed)
                self.fixes_applied.append({"error": error, "fix": "let_to_var"})
                return True
        return False
    
    def run_adaptive_loop(self, max_iterations: int = 5) -> bool:
        """Build → Parse → Fix → Rebuild loop."""
        print(f"🔄 Starting adaptive build loop (max {max_iterations} iterations)")
        
        pending_fixes = []  # Track fixes to learn from if build succeeds
        
        for i in range(max_iterations):
            print(f"\n--- Iteration {i+1} ---")
            
            success, output = self.build()
            if success:
                print("✅ Build succeeded!")
                # Learn from fixes that worked
                for fix in pending_fixes:
                    self.learn_from_success(fix["error"], fix["fix"])
                self._save_patterns()
                return True
            
            errors = self.parse_errors(output)
            if not errors:
                print("❌ Build failed but no parseable errors")
                print(output[-2000:])  # Show last 2000 chars
                return False
            
            print(f"Found {len(errors)} errors:")
            fixed_count = 0
            
            for error in errors[:10]:  # Process up to 10 errors per iteration
                print(f"  • [{error['category']}] {error['file']}:{error['line']}: {error['message'][:60]}...")
                
                if self.auto_fix_simple(error):
                    print(f"    ✓ Auto-fixed")
                    fixed_count += 1
                    # Track this fix to learn from if build succeeds
                    pending_fixes.append({
                        "error": f"{error['category']}: {error['message'][:100]}",
                        "fix": f"auto_fix_{error['category']}"
                    })
                else:
                    print(f"    → {self.generate_fix_prompt(error)}")
            
            if fixed_count == 0:
                print("\n⚠️ No auto-fixes possible. Agent intervention needed.")
                print("\nFix prompts for agent:")
                for error in errors[:5]:
                    print(f"  • {self.generate_fix_prompt(error)}")
                return False
            
            print(f"\n🔧 Applied {fixed_count} auto-fixes, rebuilding...")
        
        print(f"\n❌ Max iterations ({max_iterations}) reached")
        return False
    
    def learn_from_success(self, error_message: str, fix_description: str):
        """Record a successful fix pattern for future use."""
        # Extract a regex pattern from the error message
        # This is simplified - a real implementation would be more sophisticated
        pattern_name = f"learned_{len(self.patterns)}"
        self.patterns[pattern_name] = {
            "regex": re.escape(error_message[:50]),
            "fix_type": "learned",
            "description": fix_description,
            "learned_at": datetime.now().isoformat()
        }
        self._save_patterns()
        print(f"📚 Learned new pattern: {pattern_name}")
    
    def get_error_summary(self) -> Dict:
        """Get summary of errors by category."""
        summary = {}
        for error in self.errors:
            cat = error["category"]
            summary[cat] = summary.get(cat, 0) + 1
        return summary


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 build_intelligence.py /path/to/app [--learn]")
        sys.exit(1)
    
    project_dir = Path(sys.argv[1])
    learn_mode = "--learn" in sys.argv
    
    bi = BuildIntelligence(project_dir)
    
    if learn_mode:
        print("📚 Learning mode - recording successful patterns")
        # In learn mode, we just build and record what worked
        success, _ = bi.build()
        if success:
            print("✅ Build succeeded - patterns saved")
            bi._save_patterns()
    else:
        success = bi.run_adaptive_loop()
        
        if not success:
            print("\n📊 Error Summary:")
            for cat, count in bi.get_error_summary().items():
                print(f"  {cat}: {count}")
        
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
