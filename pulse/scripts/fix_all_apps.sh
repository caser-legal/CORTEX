#!/bin/bash
# Fix All iOS Apps - Runs preflight check and autofix on all apps
# Usage: ./fix_all_apps.sh [--fix]  (without --fix, just audits)

IOS_DIR="$HOME/Documents/iOS"
SCRIPTS_DIR="$HOME/.codex/scripts"

FIX_MODE=false
if [[ "$1" == "--fix" ]]; then
    FIX_MODE=true
    echo "🔧 FIX MODE - Will apply automatic fixes"
else
    echo "🔍 AUDIT MODE - Preview only (use --fix to apply)"
fi

echo ""
echo "========================================"
echo "  iOS App UI Audit & Fix"
echo "========================================"
echo ""

# Track totals
TOTAL_CRITICAL=0
TOTAL_WARNINGS=0
APPS_WITH_ISSUES=0

for app_dir in "$IOS_DIR"/*/; do
    app_name=$(basename "$app_dir")
    
    # Skip non-app directories
    if [[ ! -d "$app_dir" ]] || [[ "$app_name" == "dev-docs" ]] || [[ "$app_name" == "asc" ]]; then
        continue
    fi
    
    # Check if it has Swift files
    swift_count=$(find "$app_dir" -name "*.swift" 2>/dev/null | wc -l)
    if [[ $swift_count -eq 0 ]]; then
        continue
    fi
    
    echo "📱 $app_name"
    
    # Run preflight check with JSON output for robust parsing
    json_output=$(python3 "$SCRIPTS_DIR/ui_preflight.py" "$app_dir" --json 2>/dev/null)
    
    # Extract counts from JSON (fallback to 0 if parsing fails)
    critical=$(echo "$json_output" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('critical',0))" 2>/dev/null || echo "0")
    warnings=$(echo "$json_output" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('warnings',0))" 2>/dev/null || echo "0")
    
    if [[ -z "$critical" ]]; then critical=0; fi
    if [[ -z "$warnings" ]]; then warnings=0; fi
    
    if [[ $critical -gt 0 ]] || [[ $warnings -gt 0 ]]; then
        echo "   🔴 $critical critical, 🟡 $warnings warnings"
        TOTAL_CRITICAL=$((TOTAL_CRITICAL + critical))
        TOTAL_WARNINGS=$((TOTAL_WARNINGS + warnings))
        APPS_WITH_ISSUES=$((APPS_WITH_ISSUES + 1))
        
        # Apply fixes if in fix mode (for both critical AND warnings)
        if [[ "$FIX_MODE" == true ]] && ([[ $critical -gt 0 ]] || [[ $warnings -gt 0 ]]); then
            echo "   🔧 Applying automatic fixes..."
            python3 "$SCRIPTS_DIR/ui_autofix.py" "$app_dir" 2>&1 | tail -n 10
            
            # Re-check after fix using JSON
            new_json=$(python3 "$SCRIPTS_DIR/ui_preflight.py" "$app_dir" --json 2>/dev/null)
            new_critical=$(echo "$new_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('critical',0))" 2>/dev/null || echo "0")
            if [[ -z "$new_critical" ]]; then new_critical=0; fi
            
            fixed=$((critical - new_critical))
            if [[ $fixed -gt 0 ]]; then
                echo "   ✅ Fixed $fixed issues automatically"
            fi
        fi
    else
        echo "   ✅ No issues"
    fi
done

echo ""
echo "========================================"
echo "  SUMMARY"
echo "========================================"
echo ""
echo "Apps with issues: $APPS_WITH_ISSUES"
echo "Total critical:   $TOTAL_CRITICAL"
echo "Total warnings:   $TOTAL_WARNINGS"
echo ""

if [[ "$FIX_MODE" == false ]] && [[ $TOTAL_CRITICAL -gt 0 ]]; then
    echo "💡 Run with --fix to automatically fix color issues"
fi
