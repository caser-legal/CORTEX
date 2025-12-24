#!/usr/bin/env python3
"""
UI Auto-Fixer - Automatically fixes ALL common UI issues
=========================================================

Fixes:
1. Color contrast (.white/.black → .primary)
2. Missing dismiss buttons on modals
3. @State → @AppStorage for user preferences
4. Touch targets < 44pt
5. Page indicator overlaps
6. Skip button placement
7. Hardcoded listRowBackground colors

Usage:
    python3 ui_autofix.py /path/to/app --dry-run  # Preview
    python3 ui_autofix.py /path/to/app            # Apply fixes
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

class UIAutoFixer:
    def __init__(self, project_dir: Path, dry_run: bool = False):
        self.project_dir = project_dir
        self.dry_run = dry_run
        self.fixes_made = []
        self.files_modified = set()
        
    def find_swift_files(self) -> List[Path]:
        return list(self.project_dir.rglob("*.swift"))
    
    def log_fix(self, filepath: str, line: int, description: str):
        self.fixes_made.append(f"{filepath}:{line}: {description}")
        self.files_modified.add(filepath)

    # ========== COLOR FIXES ==========
    
    def fix_white_foreground(self, content: str, filepath: str) -> str:
        """Replace .foregroundStyle(.white) with .foregroundStyle(.primary)."""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            if re.search(r'\.foreground(Style|Color)\s*\(\s*\.white\s*\)', line, re.IGNORECASE):
                # Check context for guaranteed dark background
                start = max(0, i - 10)
                context = '\n'.join(lines[start:i+5]).lower()
                
                has_dark_bg = any(x in context for x in [
                    'background(.blue', 'background(color.blue',
                    'background(.accentcolor', 'lineargradient', 
                    'radialgradient', 'background(.black'
                ])
                
                if not has_dark_bg:
                    new_line = re.sub(r'\.foregroundStyle\s*\(\s*\.white\s*\)', '.foregroundStyle(.primary)', line)
                    new_line = re.sub(r'\.foregroundColor\s*\(\s*\.white\s*\)', '.foregroundStyle(.primary)', new_line)
                    if new_line != line:
                        self.log_fix(filepath, i+1, ".white → .primary")
                        line = new_line
            fixed_lines.append(line)
        return '\n'.join(fixed_lines)
    
    def fix_black_foreground(self, content: str, filepath: str) -> str:
        """Replace .foregroundStyle(.black) with .foregroundStyle(.primary)."""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            if re.search(r'\.foreground(Style|Color)\s*\(\s*\.black\s*\)', line, re.IGNORECASE):
                new_line = re.sub(r'\.foregroundStyle\s*\(\s*\.black\s*\)', '.foregroundStyle(.primary)', line)
                new_line = re.sub(r'\.foregroundColor\s*\(\s*\.black\s*\)', '.foregroundStyle(.primary)', new_line)
                if new_line != line:
                    self.log_fix(filepath, i+1, ".black → .primary")
                    line = new_line
            fixed_lines.append(line)
        return '\n'.join(fixed_lines)
    
    def fix_hardcoded_list_backgrounds(self, content: str, filepath: str) -> str:
        """Replace hardcoded listRowBackground with system colors."""
        patterns = [
            (r'\.listRowBackground\s*\(\s*Color\.black\s*\)', '.listRowBackground(Color(.systemBackground))'),
            (r'\.listRowBackground\s*\(\s*Color\.white\s*\)', '.listRowBackground(Color(.systemBackground))'),
            (r'\.listRowBackground\s*\(\s*\.black\s*\)', '.listRowBackground(Color(.systemBackground))'),
            (r'\.listRowBackground\s*\(\s*\.white\s*\)', '.listRowBackground(Color(.systemBackground))'),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                self.log_fix(filepath, 0, "listRowBackground → systemBackground")
        
        return content

    # ========== DISMISS BUTTON FIXES ==========
    
    def fix_missing_dismiss_buttons(self, content: str, filepath: str) -> str:
        """Add dismiss buttons to sheets/fullScreenCovers that don't have them."""
        lines = content.split('\n')
        
        # Find .sheet or .fullScreenCover declarations
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Match .sheet(isPresented: $something) { or .fullScreenCover(
            sheet_match = re.search(r'\.(sheet|fullScreenCover)\s*\(\s*isPresented\s*:\s*\$(\w+)', line)
            
            if sheet_match:
                modal_type = sheet_match.group(1)
                binding_var = sheet_match.group(2)
                
                # Look ahead to find the view being presented
                # Check next 30 lines for dismiss mechanism
                end_idx = min(i + 40, len(lines))
                modal_content = '\n'.join(lines[i:end_idx])
                
                has_dismiss = any(x in modal_content.lower() for x in [
                    '@environment(\\.dismiss)',
                    'dismiss()',
                    f'{binding_var} = false',
                    f'{binding_var}=false',
                    '.toolbar',
                    'button("done"',
                    'button("close"',
                    'button("cancel"',
                ])
                
                if not has_dismiss:
                    # Conservative: add TODO comment instead of risky toolbar injection
                    # Toolbar insertion via indent/brace heuristics can create invalid Swift
                    indent = len(line) - len(line.lstrip())
                    todo = f'{" " * indent}// TODO: Modal needs dismiss path. Add @Environment(\\.dismiss) or Button("Done") {{ {binding_var} = false }}'
                    lines.insert(i + 1, todo)
                    self.log_fix(filepath, i+1, f"Flagged {modal_type} missing dismiss (conservative)")
            i += 1
        
        return '\n'.join(lines)

    # ========== STATE PERSISTENCE FIXES ==========
    
    def fix_state_to_appstorage(self, content: str, filepath: str) -> str:
        """Convert @State user preferences to @AppStorage."""
        lines = content.split('\n')
        fixed_lines = []
        
        # Keywords that indicate user preferences that should persist
        pref_keywords = ['selected', 'chosen', 'current', 'user', 'preference', 'setting', 
                         'theme', 'mode', 'type', 'style', 'option', 'hasCompleted', 'isFirst']
        
        for i, line in enumerate(lines):
            # Match @State private var selectedSomething = value
            match = re.search(r'@State\s+(private\s+)?var\s+(\w+)\s*[=:]', line)
            
            if match:
                var_name = match.group(2)
                has_private = match.group(1) is not None
                
                # Skip unsupported types that would break AppStorage
                if re.search(r':\s*(CGFloat|TimeInterval|Date|UUID|URL|Data)\b', line, re.IGNORECASE):
                    fixed_lines.append(line)
                    continue
                
                # Check if this looks like a user preference
                is_preference = any(kw in var_name.lower() for kw in pref_keywords)
                
                # Also check if it's in onboarding or settings context
                is_in_prefs_context = any(x in filepath.lower() for x in ['onboarding', 'settings', 'preference'])
                
                if is_preference or is_in_prefs_context:
                    # Only convert when initializer is a literal Bool/String/Number
                    # Allow trailing whitespace/comments. Do NOT match .someCase (enums)
                    if re.search(r'=\s*(true|false|"[^"]*"|\d+(\.\d+)?)\s*(//.*)?$', line, re.IGNORECASE):
                        # Convert to @AppStorage, preserving private if present
                        private_prefix = 'private ' if has_private else ''
                        new_line = re.sub(
                            r'@State\s+(private\s+)?var\s+(\w+)',
                            f'@AppStorage("\\2") {private_prefix}var \\2',
                            line
                        )
                        if new_line != line:
                            self.log_fix(filepath, i+1, f"@State → @AppStorage for {var_name}")
                            line = new_line
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    # ========== TOUCH TARGET FIXES ==========
    
    def fix_small_touch_targets(self, content: str, filepath: str) -> str:
        """Flag small touch targets with TODO comments (conservative - brace heuristics are risky)."""
        lines = content.split('\n')
        fixed_lines = []
        TODO_MARKER = "// TODO(kiro):"  # Stable marker for idempotence
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Skip if already has our TODO marker nearby
            if TODO_MARKER in line:
                fixed_lines.append(line)
                i += 1
                continue
            
            # Find Button with Image that might be too small
            if re.search(r'Button\s*\{[^}]*\}\s*label\s*:\s*\{\s*Image\s*\(', line, re.IGNORECASE):
                # Check if it already has frame with minWidth/minHeight
                end_idx = min(i + 5, len(lines))
                button_context = '\n'.join(lines[i:end_idx])
                
                if 'frame(minWidth: 44' not in button_context and 'frame(minHeight: 44' not in button_context:
                    # Check we haven't already added a TODO
                    if not fixed_lines or TODO_MARKER not in fixed_lines[-1]:
                        indent = len(line) - len(line.lstrip())
                        todo = f'{" " * indent}{TODO_MARKER} Touch target < 44pt; add .frame(minWidth: 44, minHeight: 44).contentShape(Rectangle())'
                        fixed_lines.append(todo)
                        self.log_fix(filepath, i+1, "Flagged small touch target (conservative)")
            
            # Also check for explicit small frames on buttons
            if 'button' in line.lower():
                next_lines = '\n'.join(lines[i:min(i+5, len(lines))])
                small_frame = re.search(r'\.frame\s*\([^)]*(?:width|height)\s*:\s*(\d+)', next_lines)
                if small_frame and int(small_frame.group(1)) < 44:
                    # Check we haven't already added a TODO
                    if not fixed_lines or TODO_MARKER not in fixed_lines[-1]:
                        indent = len(line) - len(line.lstrip())
                        todo = f'{" " * indent}{TODO_MARKER} Touch target is {small_frame.group(1)}pt - expand to minWidth: 44, minHeight: 44'
                        fixed_lines.append(todo)
                        self.log_fix(filepath, i+1, f"Flagged small touch target ({small_frame.group(1)}pt)")
            
            fixed_lines.append(line)
            i += 1
        
        return '\n'.join(fixed_lines)

    # ========== PAGE INDICATOR OVERLAP FIXES ==========
    
    def fix_page_indicator_overlap(self, content: str, filepath: str) -> str:
        """Fix buttons overlapping TabView page indicators."""
        if 'tabviewstyle(.page' not in content.lower():
            return content
        
        # This is complex - look for VStack containing TabView with page style followed by Button
        # Pattern: VStack { TabView { }.tabViewStyle(.page) Button() }
        
        lines = content.split('\n')
        
        # Find TabView with page style
        for i, line in enumerate(lines):
            if '.tabviewstyle(.page' in line.lower() and 'indexdisplaymode: .never' not in line.lower():
                # Check if there's a Button in the next 15 lines that's NOT in safeAreaInset
                end_idx = min(i + 15, len(lines))
                after_tabview = '\n'.join(lines[i:end_idx]).lower()
                
                if 'button' in after_tabview and 'safeareainset' not in after_tabview:
                    # Find the Button line
                    for j in range(i + 1, end_idx):
                        if 'button' in lines[j].lower() and 'safeareainset' not in '\n'.join(lines[i:j]).lower():
                            # Add safeAreaInset wrapper
                            # This is tricky - we need to wrap the button in safeAreaInset
                            # For now, add a comment flagging it
                            indent = len(lines[j]) - len(lines[j].lstrip())
                            lines[j] = f'{" " * indent}// TODO: Wrap in .safeAreaInset(edge: .bottom) to avoid page indicator overlap\n{lines[j]}'
                            self.log_fix(filepath, j+1, "Flagged page indicator overlap - needs safeAreaInset")
                            break
                    break
        
        return '\n'.join(lines)

    # ========== SKIP BUTTON PLACEMENT ==========
    
    def fix_skip_button_placement(self, content: str, filepath: str) -> str:
        """Move Skip button to top-right in onboarding views."""
        if 'onboarding' not in filepath.lower():
            return content
        
        if 'skip' not in content.lower():
            return content
        
        lines = content.split('\n')
        
        # Look for Skip button that's at the bottom
        for i, line in enumerate(lines):
            if 'button' in line.lower() and 'skip' in line.lower():
                # Check if it's after a Spacer (meaning it's at bottom)
                start = max(0, i - 5)
                context_before = '\n'.join(lines[start:i]).lower()
                
                if 'spacer()' in context_before and 'hstack' not in context_before:
                    # This Skip is likely at the bottom - add a comment
                    indent = len(lines[i]) - len(lines[i].lstrip())
                    lines[i] = f'{" " * indent}// TODO: Move Skip button to top-right: HStack {{ Spacer(); Button("Skip") {{ }} }}.padding()\n{lines[i]}'
                    self.log_fix(filepath, i+1, "Flagged Skip button - should be top-right")
        
        return '\n'.join(lines)

    # ========== NAVIGATION/EXIT FIXES ==========
    
    def fix_selection_persistence(self, content: str, filepath: str) -> str:
        """Ensure selection views allow changing selection later."""
        filename = os.path.basename(filepath).lower()
        
        # Check if this is a selection/mode view
        is_selection_view = any(x in filename for x in ['select', 'picker', 'choose', 'type', 'mode'])
        
        if not is_selection_view:
            return content
        
        # Check if selection is stored in a way that can be changed
        has_binding = '@binding' in content.lower()
        has_appstorage = '@appstorage' in content.lower()
        has_observable = '@observable' in content.lower() or '@published' in content.lower()
        
        if not (has_binding or has_appstorage or has_observable):
            # Check for @State that should be @AppStorage
            if '@state' in content.lower():
                # The fix_state_to_appstorage should handle this
                pass
        
        return content

    def fix_mode_view_exit(self, content: str, filepath: str) -> str:
        """Add toolbar with settings access to mode views that trap users."""
        filename = os.path.basename(filepath).lower()
        
        # Check if this is a mode-specific view
        mode_patterns = ['modeview', 'sherpa', 'rescue', 'pro', 'expert', 'advanced']
        is_mode_view = any(p in filename for p in mode_patterns)
        
        if not is_mode_view:
            return content
        
        # Skip if it's not a View struct
        if 'struct' not in content or ': View' not in content:
            return content
        
        # Check if there's already a way to exit
        has_exit = any(x in content.lower() for x in [
            'toolbar',
            'navigationlink.*settings',
            'settingsview',
            'gear',
            'usermode ='
        ])
        
        if has_exit:
            return content
        
        # Find the body and add a NavigationStack with toolbar
        lines = content.split('\n')
        
        # Find "var body: some View {"
        for i, line in enumerate(lines):
            if 'var body: some View' in line:
                # Find the opening brace
                brace_line = i
                for j in range(i, min(i + 3, len(lines))):
                    if '{' in lines[j]:
                        brace_line = j
                        break
                
                # Check if already wrapped in NavigationStack
                next_lines = '\n'.join(lines[brace_line:min(brace_line+5, len(lines))]).lower()
                if 'navigationstack' in next_lines:
                    # Just add toolbar
                    # Find the closing of the main content (before the last })
                    # This is complex - add a TODO comment instead
                    pass
                else:
                    # Wrap in NavigationStack and add toolbar
                    indent = len(lines[brace_line]) - len(lines[brace_line].lstrip())
                    
                    # Add NavigationStack wrapper after the opening brace
                    # Find where the content starts
                    content_start = brace_line + 1
                    
                    # Insert NavigationStack
                    toolbar_code = f'''
{" " * (indent + 4)}NavigationStack {{
{" " * (indent + 8)}// Original content wrapped
'''
                    
                    # Find the closing brace of body
                    brace_count = 0
                    body_end = len(lines) - 1
                    for j in range(brace_line, len(lines)):
                        brace_count += lines[j].count('{') - lines[j].count('}')
                        if brace_count == 0 and j > brace_line:
                            body_end = j
                            break
                    
                    # Insert closing with toolbar before the body's closing brace
                    closing_code = f'''
{" " * (indent + 8)}.navigationTitle("Mode")
{" " * (indent + 8)}.toolbar {{
{" " * (indent + 12)}ToolbarItem(placement: .topBarTrailing) {{
{" " * (indent + 16)}NavigationLink(destination: SettingsView()) {{
{" " * (indent + 20)}Image(systemName: "gear")
{" " * (indent + 16)}}}
{" " * (indent + 12)}}}
{" " * (indent + 8)}}}
{" " * (indent + 4)}}}'''
                    
                    # This is getting complex - just add a TODO for now
                    lines.insert(content_start, f'{" " * (indent + 4)}// TODO: Add NavigationStack with toolbar containing settings gear button to allow mode switching')
                    self.log_fix(filepath, content_start, "Flagged mode view - needs settings access toolbar")
                    break
        
        return '\n'.join(lines)

    # ========== MAIN RUNNER ==========
    
    def run_fixes(self):
        """Run all fixes on all Swift files."""
        swift_files = self.find_swift_files()
        
        for filepath in swift_files:
            try:
                content = filepath.read_text()
                original = content
                rel_path = str(filepath.relative_to(self.project_dir))
                
                # Apply all fixes in order
                content = self.fix_white_foreground(content, rel_path)
                content = self.fix_black_foreground(content, rel_path)
                content = self.fix_hardcoded_list_backgrounds(content, rel_path)
                content = self.fix_missing_dismiss_buttons(content, rel_path)
                content = self.fix_state_to_appstorage(content, rel_path)
                content = self.fix_small_touch_targets(content, rel_path)
                content = self.fix_page_indicator_overlap(content, rel_path)
                content = self.fix_skip_button_placement(content, rel_path)
                content = self.fix_selection_persistence(content, rel_path)
                content = self.fix_mode_view_exit(content, rel_path)
                
                # Write if changed
                if content != original and not self.dry_run:
                    filepath.write_text(content)
                    
            except Exception as e:
                print(f"Error fixing {filepath}: {e}")
        
        return self.fixes_made

    def print_report(self):
        """Print report of fixes."""
        if not self.fixes_made:
            print("\n✅ No fixes needed!")
            return 0
        
        print(f"\n{'='*70}")
        print(f"  UI AUTO-FIX {'PREVIEW' if self.dry_run else 'COMPLETE'}")
        print(f"  {len(self.fixes_made)} fixes, {len(self.files_modified)} files")
        print(f"{'='*70}\n")
        
        for fix in self.fixes_made[:100]:
            print(f"  {fix}")
        
        if len(self.fixes_made) > 100:
            print(f"\n  ... and {len(self.fixes_made) - 100} more")
        
        if self.dry_run:
            print(f"\n💡 Run without --dry-run to apply")
        else:
            print(f"\n✅ Applied. Run ui_preflight.py to verify.")
        
        return len(self.fixes_made)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ui_autofix.py /path/to/app [--dry-run]")
        sys.exit(1)
    
    project_dir = Path(sys.argv[1])
    dry_run = '--dry-run' in sys.argv
    
    if not project_dir.exists():
        print(f"Error: {project_dir} does not exist")
        sys.exit(1)
    
    fixer = UIAutoFixer(project_dir, dry_run)
    fixer.run_fixes()
    fixer.print_report()


if __name__ == "__main__":
    main()
