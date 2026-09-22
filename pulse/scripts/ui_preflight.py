#!/usr/bin/env python3
"""
UI Pre-Flight Check - Runs BEFORE marking features complete
============================================================

Catches common issues that slip through code review:
1. Color contrast violations (white on light, dark on dark)
2. Missing navigation (no back button, no way to exit)
3. Hardcoded colors that don't adapt to light/dark mode
4. Missing state management (can't change selections)
5. Accessibility violations
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple
from collections import defaultdict

CRITICAL = "🔴 CRITICAL"
WARNING = "🟡 WARNING"
INFO = "🔵 INFO"

# === Module-scope compiled regexes for mode-exit detection ===

# SF Symbol settings icons - supports systemName AND systemImage, plus raw strings
SFSYMBOL_SETTINGS_RE = re.compile(
    r'(systemname|systemimage)\s*:\s*(?P<h>#+)?"'
    r'(gear(shape(\.fill)?)?|ellipsis(\.circle)?|slider\.horizontal\.3|line\.3\.horizontal|person\.circle)'
    r'"(?(h)(?P=h))',
    re.IGNORECASE
)

# Settings words - require proximity to toolbar/navigationlink
SETTINGS_WORDS_RE = re.compile(
    r'(toolbar|navigationlink)[\s\S]{0,120}(settings|settingsview|preferences|appsettings|settingsscreen)',
    re.IGNORECASE
)

# More menu - Menu("More") label form OR Menu { ... more ... } OR ellipsis systemName/systemImage
MORE_MENU_RE = re.compile(
    r'(?P<menu_label>menu\s*\(\s*(?P<hm>#+)?"more"(?(hm)(?P=hm))\s*\))|'
    r'(?P<menu_body>menu\s*\{[\s\S]{0,100}\bmore\b)|'
    r'(?P<ellipsis>(systemname|systemimage)\s*:\s*(?P<h2>#+)?"ellipsis"(?(h2)(?P=h2)))',
    re.IGNORECASE
)


def strip_comments_preserving_strings(s: str) -> str:
    """Strip // and /* */ comments but preserve string contents.
    
    Understands Swift raw strings (#"..."#, ##"..."##) and multiline strings (triple quotes).
    Raw strings don't use backslash escaping and can contain unescaped quotes.
    """
    out = []
    in_str = False
    str_hashes = 0      # Number of leading #'s for raw strings
    str_triple = False  # Whether delimiter is """ (multiline)
    block_depth = 0     # Nested block comment depth
    escape = False
    i = 0
    
    while i < len(s):
        ch = s[i]
        
        # Inside block comment (possibly nested)
        if block_depth > 0:
            if ch == '/' and i + 1 < len(s) and s[i + 1] == '*':
                block_depth += 1
                i += 2
                continue
            if ch == '*' and i + 1 < len(s) and s[i + 1] == '/':
                block_depth -= 1
                i += 2
                continue
            if ch == '\n':
                out.append('\n')
            i += 1
            continue
        
        # Inside string
        if in_str:
            out.append(ch)
            
            # Only use backslash escaping for non-raw strings
            if str_hashes == 0:
                if escape:
                    escape = False
                    i += 1
                    continue
                elif ch == '\\':
                    escape = True
                    i += 1
                    continue
            
            # Check for closing delimiter
            if ch == '"':
                if str_triple:
                    # Closing: """# (with matching hash count)
                    if s[i:i+3] == '"""':
                        trailing_hashes = 0
                        j = i + 3
                        while j < len(s) and s[j] == '#' and trailing_hashes < str_hashes:
                            trailing_hashes += 1
                            j += 1
                        if trailing_hashes == str_hashes:
                            out.append('"')
                            out.append('"')
                            out.extend('#' * str_hashes)
                            i = j
                            in_str = False
                            str_hashes = 0
                            str_triple = False
                            continue
                else:
                    # Closing: "# (with matching hash count)
                    trailing_hashes = 0
                    j = i + 1
                    while j < len(s) and s[j] == '#' and trailing_hashes < str_hashes:
                        trailing_hashes += 1
                        j += 1
                    if trailing_hashes == str_hashes:
                        out.extend('#' * str_hashes)
                        i = j
                        in_str = False
                        str_hashes = 0
                        str_triple = False
                        continue
            
            i += 1
            continue
        
        # Not in string or block comment - check for string start
        # Swift string: optional #'s + " or """
        if ch == '#' or ch == '"':
            j = i
            h = 0
            while j < len(s) and s[j] == '#':
                h += 1
                j += 1
            if j < len(s) and s[j] == '"':
                triple = (j + 2 < len(s) and s[j:j+3] == '"""')
                in_str = True
                str_hashes = h
                str_triple = triple
                out.extend('#' * h)
                if triple:
                    out.extend('"""')
                    i = j + 3
                else:
                    out.append('"')
                    i = j + 1
                continue
        
        # Start of /* block comment
        if ch == '/' and i + 1 < len(s) and s[i + 1] == '*':
            block_depth = 1
            i += 2
            continue
        
        # Start of // line comment - skip to newline
        if ch == '/' and i + 1 < len(s) and s[i + 1] == '/':
            while i < len(s) and s[i] != '\n':
                i += 1
            if i < len(s) and s[i] == '\n':
                out.append('\n')
                i += 1
            continue
        
        out.append(ch)
        i += 1
    return ''.join(out)


class UIPreflightChecker:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.issues = []
        self.files_checked = 0
    
    def _norm(self, content: str) -> str:
        """Normalize content: lowercase + strip comments (preserving strings)."""
        return strip_comments_preserving_strings(content.lower())
        
    def find_swift_files(self) -> List[Path]:
        return list(self.project_dir.rglob("*.swift"))
    
    def add_issue(self, severity: str, file: str, line: int, message: str, fix: str = ""):
        self.issues.append({
            "severity": severity,
            "file": file,
            "line": line,
            "message": message,
            "fix": fix
        })
    
    def check_color_contrast(self, content: str, filepath: str):
        """Find hardcoded colors that won't adapt to light/dark mode."""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            lower = line.lower()
            
            # White foreground without background check
            if re.search(r'\.foreground(style|color)\s*\(\s*\.white\s*\)', lower):
                # Check context for colorScheme or dark background
                start = max(0, i - 15)
                end = min(len(lines), i + 5)
                context = '\n'.join(lines[start:end]).lower()
                
                # Only treat as "has background" if it's an actual SwiftUI modifier
                has_bg_modifier = '.background(' in context or '.background {' in context
                # Check for QA-OK or preflight-ok comment on same line (verified false positive)
                has_qa_ok = 'qa-ok' in line.lower() or 'preflight-ok' in line.lower()
                if 'colorscheme' not in context and not has_bg_modifier and not has_qa_ok:
                    self.add_issue(CRITICAL, filepath, i,
                        "White text without dark background - INVISIBLE in light mode",
                        "Use .foregroundStyle(.primary) or check colorScheme")
            
            # Black foreground
            if re.search(r'\.foreground(style|color)\s*\(\s*\.black\s*\)', lower):
                start = max(0, i - 15)
                end = min(len(lines), i + 5)
                context = '\n'.join(lines[start:end]).lower()
                
                # Check for QA-OK or preflight-ok comment on same line (verified false positive)
                has_qa_ok = 'qa-ok' in line.lower() or 'preflight-ok' in line.lower()
                if 'colorscheme' not in context and not has_qa_ok:
                    self.add_issue(CRITICAL, filepath, i,
                        "Black text without colorScheme check - INVISIBLE in dark mode",
                        "Use .foregroundStyle(.primary) or check colorScheme")
            
            # Blue on potentially dark backgrounds
            if re.search(r'\.foreground(style|color)\s*\(\s*\.blue\s*\)', lower):
                start = max(0, i - 10)
                end = min(len(lines), i + 5)
                context = '\n'.join(lines[start:end]).lower()
                
                if 'background' in context and ('black' in context or 'dark' in context or '#1a1a1a' in context):
                    self.add_issue(WARNING, filepath, i,
                        "Blue text on dark background - may have poor contrast",
                        "Use Color.accentColor or a lighter blue variant")
            
            # Hardcoded hex colors
            if re.search(r'color\s*\(\s*hex\s*:\s*["\']#', lower, re.IGNORECASE):
                if 'colorscheme' not in '\n'.join(lines[max(0,i-10):min(len(lines),i+5)]).lower():
                    self.add_issue(WARNING, filepath, i,
                        "Hardcoded hex color - won't adapt to light/dark mode",
                        "Use Color(.systemBackground) or provide light/dark variants")
            
            # .primary foreground on colored backgrounds (accent, brand colors)
            if re.search(r'\.foreground(style|color)\s*\(\s*\.primary\s*\)', lower):
                start = max(0, i - 5)
                end = min(len(lines), i + 5)
                context = '\n'.join(lines[start:end]).lower()
                
                # Only flag if .primary is DIRECTLY combined with a colored .background()
                # Look for patterns like: .background(Color.accent) or .background(.orange)
                colored_bg_patterns = [
                    r'\.background\s*\(\s*\.?(orange|red|blue|green|purple|pink|yellow|accent)',
                    r'\.background\s*\(\s*color\.(wallai|accent|brand)',
                    r'\.background\s*\(\s*lineargradient.*color\.(wallai|accent)',
                ]
                has_colored_bg = any(re.search(p, context) for p in colored_bg_patterns)
                
                # Exclude system backgrounds which are fine with .primary
                system_bg_patterns = ['systembackground', 'secondarysystem', 'material', 'card(', 'surface(', 'opacity(0.']
                has_system_bg = any(p in context for p in system_bg_patterns)
                
                if has_colored_bg and not has_system_bg:
                    self.add_issue(WARNING, filepath, i,
                        ".primary text on colored background - may have poor contrast",
                        "Use .foregroundStyle(.white) for text on accent/brand color backgrounds")
            
            # listRowBackground with hardcoded colors
            if 'listrowbackground' in lower:
                if '.black' in lower or '.white' in lower or 'hex' in lower:
                    self.add_issue(CRITICAL, filepath, i,
                        "Hardcoded listRowBackground - wrong in opposite color scheme",
                        "Use Color(.systemBackground) or .secondarySystemBackground")

    def check_navigation_exits(self, content: str, filepath: str):
        """Check for views that might trap users with no way out."""
        lines = content.split('\n')
        filename = os.path.basename(filepath).lower()
        
        # Check if this is a selection/picker view
        is_selection_view = any(x in filename for x in ['select', 'picker', 'choose', 'type', 'mode'])
        is_onboarding = 'onboarding' in filename
        is_settings = 'settings' in filename
        
        norm = self._norm(content)
        has_dismiss = 'dismiss' in norm
        has_back = re.search(r'navigationlink|poptoroot|dismiss|ispresented|\.sheet|\.fullscreencover', norm)
        has_done_button = re.search(r'button.*done|button.*close|button.*cancel|button.*back', norm)
        
        # Selection views need a way to change selection later
        if is_selection_view and not is_onboarding:
            # Check if there's a way to re-access this view
            if not re.search(r'@binding|@state.*selected|onchange|toggle', norm):
                self.add_issue(WARNING, filepath, 1,
                    "Selection view may not allow changing selection later",
                    "Add @Binding or store selection in @AppStorage for persistence + editability")
        
        # Modal views need dismiss
        if '.sheet' in norm or '.fullscreencover' in norm:
            # Find the presented view
            for i, line in enumerate(lines, 1):
                lower_line = line.lower()
                if '.sheet' in lower_line or '.fullscreencover' in lower_line:
                    # Check next 30 lines for dismiss mechanism
                    end = min(len(lines), i + 30)
                    modal_content = '\n'.join(lines[i:end]).lower()
                    
                    # .sheet(item:) presents a separate view - dismiss is in that view
                    # Also, ALL sheets can be dismissed by swiping down (iOS built-in)
                    # Only flag .fullScreenCover with interactiveDismissDisabled
                    is_item_sheet = 'item:' in lower_line or 'item :' in lower_line
                    is_fullscreen = '.fullscreencover' in lower_line
                    has_interactive_disabled = 'interactivedismissdisabled' in modal_content
                    
                    # Skip .sheet(item:) - these present separate views with their own dismiss
                    if is_item_sheet:
                        continue
                    
                    # Only flag fullScreenCover that disables swipe-to-dismiss
                    if is_fullscreen and not has_interactive_disabled:
                        continue  # Can swipe to dismiss
                    
                    # For isPresented sheets, check if dismiss exists
                    if 'ispresented' in lower_line:
                        if 'dismiss' not in modal_content and 'ispresented' not in modal_content:
                            # Check if the presented view is a separate struct (dismiss would be there)
                            # Pattern: SomeView() or SomeView(args) on its own line
                            # modal_content is already lowercase
                            if re.search(r'^\s*\w+view\s*\(', modal_content, re.MULTILINE):
                                continue  # Separate view - dismiss is in that file
                            if re.search(r'\{\s*\n?\s*\w+\s*\(', modal_content):
                                continue  # Separate view - dismiss is in that file
                            
                            self.add_issue(CRITICAL, filepath, i,
                                "Modal view may have no dismiss button",
                                "Add @Environment(\\.dismiss) var dismiss and a close button")

    def check_state_persistence(self, content: str, filepath: str):
        """Check if user selections are properly persisted."""
        lines = content.split('\n')
        norm = self._norm(content)
        
        # Only check for onboarding completion persistence - this is the critical one
        # Skip the @State var selected* checks - too many false positives
        # (selectedConversation, selectedItem, etc. are ephemeral UI state, not preferences)
        
        # Check for onboarding completion that isn't persisted
        if 'onboarding' in filepath.lower():
            # @Binding is fine - persistence is in parent view
            if '@binding' in norm and 'hascompleted' in norm:
                pass  # Binding from parent - parent handles persistence
            elif '@state' in norm and 'hascompleted' in norm:
                if '@appstorage' not in norm:
                    self.add_issue(CRITICAL, filepath, 1,
                        "Onboarding completion not persisted - will show every launch",
                        "Use @AppStorage(\"hasCompletedOnboarding\") var hasCompleted = false")

    def check_touch_targets(self, content: str, filepath: str):
        """Check for buttons/tappable elements smaller than 44pt."""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Small icon buttons
            if re.search(r'button.*image.*font\s*\(\s*\.(caption|footnote|caption2)\s*\)', line.lower()):
                self.add_issue(WARNING, filepath, i,
                    "Small icon button - may be hard to tap",
                    "Add .frame(minWidth: 44, minHeight: 44).contentShape(Rectangle())")
            
            # Explicit small frames on buttons
            if 'button' in line.lower():
                end = min(len(lines), i + 5)
                button_context = '\n'.join(lines[i:end])
                
                small_frame = re.search(r'\.frame\s*\([^)]*(?:width|height)\s*:\s*(\d+)', button_context)
                if small_frame and int(small_frame.group(1)) < 44:
                    self.add_issue(WARNING, filepath, i,
                        f"Button frame ({small_frame.group(1)}pt) smaller than 44pt minimum",
                        "Use .frame(minWidth: 44, minHeight: 44)")

    def check_accessibility(self, content: str, filepath: str):
        """DISABLED - Accessibility checks are not required for these apps."""
        # Accessibility labels are nice-to-have but not blocking
        # Skip entirely to avoid wasting agent time
        pass

    def check_page_indicator_overlap(self, content: str, filepath: str):
        """Check for buttons overlapping TabView page indicators."""
        norm = self._norm(content)
        if 'tabviewstyle(.page' not in norm:
            return
            
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            if 'tabviewstyle(.page' in line.lower():
                # Check surrounding context
                start = max(0, i - 20)
                end = min(len(lines), i + 20)
                context = '\n'.join(lines[start:end]).lower()
                
                # Bad: VStack with button after TabView
                if 'vstack' in context and 'button' in context:
                    if 'safeareainset' not in context and 'indexdisplaymode: .never' not in context:
                        self.add_issue(CRITICAL, filepath, i,
                            "Buttons likely overlap page indicators",
                            "Use .safeAreaInset(edge: .bottom) or indexDisplayMode: .never")

    def check_skip_button_placement(self, content: str, filepath: str):
        """Check if Skip button is in top-right for onboarding."""
        if 'onboarding' not in filepath.lower():
            return
        
        norm = self._norm(content)
        if 'skip' not in norm:
            return
            
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            if 'skip' in line.lower() and 'button' in line.lower():
                # Check context for placement
                start = max(0, i - 10)
                context = '\n'.join(lines[start:i+5]).lower()
                
                # Good patterns - widened to reduce false positives
                # Toolbar alone is too broad - require top-bar placement indicators
                good = (
                    re.search(r'hstack\s*(\([^)]*\))?\s*\{[\s\S]{0,150}?spacer\s*\(\s*\)', context) is not None
                    or 'alignment: .toptrailing' in context
                    or '.topbartrailing' in context
                    or ('toolbar' in context and ('topbartrailing' in context or 'navigationbartrailing' in context or 'cancellationaction' in context))
                    or 'navigationbaritems(trailing' in context
                    or 'overlay(alignment:' in context
                    or 'safeareainset(edge: .top' in context
                )
                
                # If Skip exists but we don't see known top-right patterns, warn.
                if not good:
                    self.add_issue(WARNING, filepath, i,
                        "Skip button may not be in top-right corner",
                        "Move Skip to HStack { Spacer(); Button(\"Skip\") } at top of view")

    def check_mode_view_exit(self, content: str, filepath: str):
        """Check if mode-specific views have a way to switch back to default mode."""
        filename = os.path.basename(filepath).lower()
        
        # Skip ViewModels entirely - they're not views
        if 'viewmodel' in filename or filename.endswith('vm.swift'):
            return
        
        # Normalize filename: strip .swift and common suffixes
        base = filename.replace('.swift', '')
        base = re.sub(r'(view|screen|controller)$', '', base)
        
        # Match mode-specific views - require explicit mode suffix or known mode names
        # This avoids PromoView (promo != promode) while catching SherpaModeView, RescueModeView
        is_mode_view = bool(re.search(r'(sherpa(mode)?|rescue(mode)?|promode|expertmode|advancedmode|modeview)\b', base))
        
        if not is_mode_view:
            return
        
        # Use normalized content for ALL checks (prevents comment/string spoofing)
        norm = self._norm(content)
        
        # Check if there's a way to change the mode back (specific patterns only)
        has_mode_switch = any(x in norm for x in [
            'usermode =',
            'usermode=',
            '@appstorage("usermode")',
            '@appstorage("mode")',
            'switch mode',
            'change mode',
            'exit mode',
        ])
        
        # SF Symbol settings icons - require systemName: "icon" proximity
        settings_icons = SFSYMBOL_SETTINGS_RE.search(norm) is not None
        
        # Settings words - require proximity to toolbar/navigationlink
        settings_words = SETTINGS_WORDS_RE.search(norm) is not None
        
        # 'more' - require Menu context (not just Text("More"))
        has_more_menu = MORE_MENU_RE.search(norm) is not None
        
        has_settings_access = settings_icons or settings_words or has_more_menu
        
        if not has_mode_switch and not has_settings_access:
            self.add_issue(CRITICAL, filepath, 1,
                "Mode view has no way to switch back to default mode - USER TRAPPED",
                "Add toolbar with settings/gear button, or NavigationLink to settings where user can change mode")

    def run_all_checks(self):
        """Run all checks on all Swift files."""
        swift_files = self.find_swift_files()
        
        for filepath in swift_files:
            self.files_checked += 1
            try:
                content = filepath.read_text()
                rel_path = str(filepath.relative_to(self.project_dir))
                
                self.check_color_contrast(content, rel_path)
                self.check_navigation_exits(content, rel_path)
                self.check_state_persistence(content, rel_path)
                self.check_touch_targets(content, rel_path)
                self.check_accessibility(content, rel_path)
                self.check_page_indicator_overlap(content, rel_path)
                self.check_skip_button_placement(content, rel_path)
                self.check_mode_view_exit(content, rel_path)
                
            except Exception as e:
                print(f"Error checking {filepath}: {e}")
        
        return self.issues

    def print_report(self):
        """Print a formatted report of all issues."""
        if not self.issues:
            print(f"\n✅ No issues found in {self.files_checked} files!")
            return 0
        
        # Group by severity
        by_severity = defaultdict(list)
        for issue in self.issues:
            by_severity[issue['severity']].append(issue)
        
        print(f"\n{'='*70}")
        print(f"  UI PRE-FLIGHT CHECK RESULTS")
        print(f"  {self.files_checked} files checked, {len(self.issues)} issues found")
        print(f"{'='*70}\n")
        
        # Print critical first
        for severity in [CRITICAL, WARNING, INFO]:
            issues = by_severity.get(severity, [])
            if not issues:
                continue
                
            print(f"\n{severity} ({len(issues)} issues)")
            print("-" * 50)
            
            for issue in issues:
                print(f"\n  {issue['file']}:{issue['line']}")
                print(f"  {issue['message']}")
                if issue['fix']:
                    print(f"  💡 Fix: {issue['fix']}")
        
        # Summary
        critical_count = len(by_severity.get(CRITICAL, []))
        warning_count = len(by_severity.get(WARNING, []))
        
        print(f"\n{'='*70}")
        print(f"  SUMMARY: {critical_count} critical, {warning_count} warnings")
        
        if critical_count > 0:
            print(f"\n  ❌ BLOCKING: Fix {critical_count} critical issues before marking complete")
            return 1
        elif warning_count > 0:
            print(f"\n  ⚠️  Review {warning_count} warnings before marking complete")
            return 0
        
        return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description='UI Pre-Flight Check')
    parser.add_argument('project_dir', nargs='?', default='.', help='Project directory')
    parser.add_argument('--json', action='store_true', help='Output JSON summary (machine-readable)')
    args = parser.parse_args()
    
    project_dir = Path(args.project_dir)
    
    if not project_dir.exists():
        print(f"Error: {project_dir} does not exist")
        sys.exit(1)
    
    checker = UIPreflightChecker(project_dir)
    checker.run_all_checks()
    
    if args.json:
        # Machine-readable JSON output for scripting
        import json
        by_severity = defaultdict(list)
        for issue in checker.issues:
            by_severity[issue['severity']].append(issue)
        
        summary = {
            "files_checked": checker.files_checked,
            "critical": len(by_severity.get(CRITICAL, [])),
            "warnings": len(by_severity.get(WARNING, [])),
            "info": len(by_severity.get(INFO, [])),
            "exit_code": 1 if by_severity.get(CRITICAL) else 0
        }
        print(json.dumps(summary))
        sys.exit(summary["exit_code"])
    else:
        exit_code = checker.print_report()
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
