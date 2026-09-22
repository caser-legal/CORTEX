#!/usr/bin/env python3
"""
iOS SwiftUI UI Audit Script
===========================

Scans Swift files for common UI issues:
- Skip button placement (should be top-right)
- Text contrast issues (light on light, dark on dark)
- Settings bubble color issues
- Touch target sizes
- Non-Fibonacci spacing
- Page indicator overlaps

Usage:
    python ui_audit.py /path/to/app
    python ui_audit.py  # Current directory
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Issue severity
CRITICAL = "🔴 CRITICAL"
WARNING = "🟡 WARNING"
INFO = "🔵 INFO"


def find_swift_files(directory: Path) -> List[Path]:
    """Find all Swift files in directory."""
    return list(directory.rglob("*.swift"))


def check_skip_button_placement(content: str, filepath: str) -> List[Tuple[str, str, int]]:
    """Check if Skip buttons are in top-right position."""
    issues = []
    lines = content.split('\n')
    
    in_onboarding = False
    skip_line = None
    skip_context = []
    
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        
        # Track if we're in an onboarding view
        if 'onboardingview' in lower or 'onboarding' in lower:
            in_onboarding = True
        
        # Look for Skip buttons
        if 'button' in lower and 'skip' in lower:
            skip_line = i
            # Get surrounding context
            start = max(0, i - 10)
            end = min(len(lines), i + 5)
            skip_context = lines[start:end]
            context_str = '\n'.join(skip_context)
            
            # Check if Skip is at bottom (bad patterns)
            bad_patterns = [
                r'spacer\(\).*\n.*skip',  # Spacer before Skip
                r'\.padding\(\.bottom',    # Bottom padding near Skip
                r'vstack.*\{[^}]*button.*skip[^}]*\}[^}]*$',  # Skip at end of VStack
            ]
            
            # Check if Skip is at top-right (good patterns)
            good_patterns = [
                r'hstack\s*\{[^}]*spacer\(\)[^}]*button.*skip',  # HStack { Spacer() Skip }
                r'\.topbartrailing',  # Toolbar placement
                r'alignment:\s*\.toptrailing',  # ZStack alignment
            ]
            
            is_good = any(re.search(p, context_str, re.IGNORECASE | re.DOTALL) for p in good_patterns)
            is_bad = any(re.search(p, context_str, re.IGNORECASE | re.DOTALL) for p in bad_patterns)
            
            if is_bad and not is_good:
                issues.append((
                    CRITICAL,
                    f"Skip button may not be in top-right position",
                    i
                ))
    
    return issues


def check_text_contrast(content: str, filepath: str) -> List[Tuple[str, str, int]]:
    """Check for potential text contrast issues."""
    issues = []
    lines = content.split('\n')
    
    # Patterns that suggest light text on potentially light background
    light_text_patterns = [
        (r'\.foregroundstyle\(\.white\)', "White text without dark background check"),
        (r'\.foregroundcolor\(\.white\)', "White text without dark background check"),
        (r'\.foregroundstyle\(color\.white\)', "White text without dark background check"),
        (r'foregroundstyle\(\.secondary\).*background\(\.white', "Secondary text on white background"),
    ]
    
    # Patterns that suggest dark text on potentially dark background
    dark_text_patterns = [
        (r'\.foregroundstyle\(\.black\)', "Black text - verify background is light"),
        (r'\.foregroundcolor\(\.black\)', "Black text - verify background is light"),
        (r'\.foregroundstyle\(\.primary\).*background.*dark', "Primary text on dark background"),
    ]
    
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        
        # Check for hardcoded white text without colorScheme check
        if '.white' in lower and 'foreground' in lower:
            # Look for colorScheme in surrounding context
            start = max(0, i - 20)
            end = min(len(lines), i + 5)
            context = '\n'.join(lines[start:end]).lower()
            
            if 'colorscheme' not in context and 'dark' not in context:
                issues.append((
                    WARNING,
                    f"White foreground without colorScheme check - may be invisible in light mode",
                    i
                ))
        
        # Check for hardcoded black text
        if '.black' in lower and 'foreground' in lower:
            start = max(0, i - 20)
            end = min(len(lines), i + 5)
            context = '\n'.join(lines[start:end]).lower()
            
            if 'colorscheme' not in context:
                issues.append((
                    WARNING,
                    f"Black foreground without colorScheme check - may be invisible in dark mode",
                    i
                ))
        
        # Check for .secondary on white/light backgrounds
        if '.secondary' in lower and 'foreground' in lower:
            start = max(0, i - 5)
            end = min(len(lines), i + 5)
            context = '\n'.join(lines[start:end]).lower()
            
            if 'background(.white' in context or 'background(color.white' in context:
                issues.append((
                    INFO,
                    f"Secondary text near white background - verify contrast",
                    i
                ))
    
    return issues


def check_settings_bubble_colors(content: str, filepath: str) -> List[Tuple[str, str, int]]:
    """Check for settings/list row color issues."""
    issues = []
    lines = content.split('\n')
    
    # Look for settings-related views
    settings_indicators = ['settingsview', 'settings', 'form', 'list', 'section']
    
    in_settings = any(ind in content.lower() for ind in settings_indicators)
    
    if not in_settings:
        return issues
    
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        
        # Check for hardcoded background colors in settings context
        if 'background' in lower:
            # Black background in settings (might be wrong in light mode)
            if '.black' in lower or 'color.black' in lower:
                start = max(0, i - 10)
                context = '\n'.join(lines[start:i+5]).lower()
                if 'colorscheme' not in context:
                    issues.append((
                        WARNING,
                        f"Black background in settings - verify it adapts to light mode",
                        i
                    ))
            
            # White background in settings (might be wrong in dark mode)
            if '.white' in lower or 'color.white' in lower:
                start = max(0, i - 10)
                context = '\n'.join(lines[start:i+5]).lower()
                if 'colorscheme' not in context:
                    issues.append((
                        WARNING,
                        f"White background in settings - verify it adapts to dark mode",
                        i
                    ))
        
        # Check for hardcoded row/cell colors
        if ('listrowbackground' in lower or 'listrow' in lower) and ('.black' in lower or '.white' in lower):
            issues.append((
                WARNING,
                f"Hardcoded list row color - should adapt to color scheme",
                i
            ))
    
    return issues


def check_touch_targets(content: str, filepath: str) -> List[Tuple[str, str, int]]:
    """Check for touch targets smaller than 44pt."""
    issues = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        
        # Look for small frame sizes on buttons
        if 'button' in lower or 'image(systemname' in lower:
            # Check next few lines for frame
            for j in range(i, min(i + 5, len(lines))):
                frame_line = lines[j-1].lower()
                
                # Check for explicit small frames
                frame_match = re.search(r'\.frame\([^)]*(?:width|height)\s*:\s*(\d+)', frame_line)
                if frame_match:
                    size = int(frame_match.group(1))
                    if size < 44:
                        issues.append((
                            CRITICAL,
                            f"Touch target may be smaller than 44pt ({size}pt found)",
                            j
                        ))
                        break
    
    return issues


def check_non_fibonacci_spacing(content: str, filepath: str) -> List[Tuple[str, str, int]]:
    """Check for non-Fibonacci spacing values."""
    issues = []
    lines = content.split('\n')
    
    fibonacci = {2, 3, 4, 5, 8, 13, 21, 34, 55, 89}
    non_fib_common = {10, 12, 15, 16, 18, 20, 24, 25, 30, 32, 40, 48, 50, 60, 64}
    
    for i, line in enumerate(lines, 1):
        # Look for padding/spacing with numeric values
        matches = re.findall(r'(?:padding|spacing|cornerradius)\s*[:\(]\s*(\d+)', line.lower())
        
        for match in matches:
            value = int(match)
            if value in non_fib_common and value not in fibonacci:
                issues.append((
                    INFO,
                    f"Non-Fibonacci spacing value: {value} (consider 8, 13, 21, 34)",
                    i
                ))
    
    return issues


def check_page_indicator_overlap(content: str, filepath: str) -> List[Tuple[str, str, int]]:
    """Check for potential page indicator overlap issues."""
    issues = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        
        # Check for overlay on bottom with TabView nearby
        if '.overlay' in lower and 'bottom' in lower:
            start = max(0, i - 20)
            context = '\n'.join(lines[start:i+10]).lower()
            
            if 'tabview' in context and '.page' in context:
                issues.append((
                    WARNING,
                    f"Bottom overlay near TabView - may overlap page indicators. Use .safeAreaInset instead",
                    i
                ))
    
    return issues


def audit_file(filepath: Path) -> List[Tuple[str, str, str, int]]:
    """Run all audits on a single file."""
    try:
        content = filepath.read_text()
    except Exception as e:
        return [(WARNING, str(filepath), f"Could not read file: {e}", 0)]
    
    all_issues = []
    
    checks = [
        check_skip_button_placement,
        check_text_contrast,
        check_settings_bubble_colors,
        check_touch_targets,
        check_non_fibonacci_spacing,
        check_page_indicator_overlap,
    ]
    
    for check in checks:
        issues = check(content, str(filepath))
        for severity, message, line in issues:
            all_issues.append((severity, str(filepath), message, line))
    
    return all_issues


def main():
    """Main entry point."""
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    
    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print(f"  UI AUDIT: {directory.name}")
    print(f"{'='*70}\n")
    
    swift_files = find_swift_files(directory)
    
    if not swift_files:
        print("No Swift files found.")
        sys.exit(0)
    
    print(f"Scanning {len(swift_files)} Swift files...\n")
    
    all_issues = []
    
    for filepath in swift_files:
        issues = audit_file(filepath)
        all_issues.extend(issues)
    
    if not all_issues:
        print("✅ No issues found!")
        sys.exit(0)
    
    # Group by severity
    critical = [i for i in all_issues if CRITICAL in i[0]]
    warnings = [i for i in all_issues if WARNING in i[0]]
    info = [i for i in all_issues if INFO in i[0]]
    
    # Print results
    if critical:
        print(f"\n{CRITICAL} CRITICAL ISSUES ({len(critical)})")
        print("-" * 50)
        for severity, filepath, message, line in critical:
            rel_path = Path(filepath).relative_to(directory) if directory in Path(filepath).parents else filepath
            print(f"  {rel_path}:{line}")
            print(f"    {message}\n")
    
    if warnings:
        print(f"\n{WARNING} WARNINGS ({len(warnings)})")
        print("-" * 50)
        for severity, filepath, message, line in warnings:
            rel_path = Path(filepath).relative_to(directory) if directory in Path(filepath).parents else filepath
            print(f"  {rel_path}:{line}")
            print(f"    {message}\n")
    
    if info:
        print(f"\n{INFO} INFO ({len(info)})")
        print("-" * 50)
        for severity, filepath, message, line in info:
            rel_path = Path(filepath).relative_to(directory) if directory in Path(filepath).parents else filepath
            print(f"  {rel_path}:{line}")
            print(f"    {message}\n")
    
    print(f"\n{'='*70}")
    print(f"  SUMMARY: {len(critical)} critical, {len(warnings)} warnings, {len(info)} info")
    print(f"{'='*70}\n")
    
    # Exit with error code if critical issues found
    sys.exit(1 if critical else 0)


if __name__ == "__main__":
    main()
