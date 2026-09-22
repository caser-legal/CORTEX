#!/bin/bash
# QA COMPLETED apps (300+ passing) - focuses on closest to 100% QA first

IOS_DIR="$HOME/Documents/iOS"

echo "=== AUTOQAGPT Batch QA (Verify completed apps) ==="

get_passing() {
  grep -c '"passes": true' "$1/feature_list.json" 2>/dev/null | tr -d '[:space:]' || echo 0
}

get_qa_progress() {
  local dir="$1"
  if [ -f "$dir/qa_checklist.json" ]; then
    local verified=$(grep -c '"verified": true' "$dir/qa_checklist.json" 2>/dev/null || echo 0)
    local total=$(grep -c '"verified":' "$dir/qa_checklist.json" 2>/dev/null || echo 0)
    echo "$verified $total"
  else
    echo "0 0"
  fi
}

while true; do
  # Find completed app that needs QA (check actual progress, not just marker)
  best_app=""
  best_pct=0
  
  for dir in "$IOS_DIR"/*/; do
    [ -f "$dir/feature_list.json" ] || continue
    
    passing=$(get_passing "$dir")
    [[ "$passing" =~ ^[0-9]+$ ]] || passing=0
    
    # Only QA apps with 300+ features
    [ "$passing" -lt 300 ] && continue
    
    read verified total <<< $(get_qa_progress "$dir")
    
    # Calculate percentage (handle no checklist = 0%)
    if [ "$total" -gt 0 ]; then
      pct=$((verified * 100 / total))
    else
      pct=0
    fi
    
    # Skip if already 100% QA verified (check actual progress, not just marker)
    [ "$pct" -ge 100 ] && continue
    
    # If marker exists but QA is not 100%, remove the premature marker
    if [ -f "$dir/.qa_verified" ] && [ "$pct" -lt 100 ]; then
      echo "⚠️  Removing premature .qa_verified from $(basename "$dir") (QA: $verified/$total = $pct%)"
      rm "$dir/.qa_verified"
    fi
    
    if [ "$pct" -gt "$best_pct" ]; then
      best_pct=$pct
      best_app="$dir"
    fi
  done
  
  if [ -z "$best_app" ]; then
    echo "✅ All completed apps are QA verified! Sleeping 60s..."
    sleep 60
    continue
  fi
  
  app_name=$(basename "$best_app")
  read verified total <<< $(get_qa_progress "$best_app")
  
  echo ""
  echo "🔍 QA: $app_name ($verified/$total = $best_pct%)"
  echo "================================================"
  
  # Run autonomous_qa.py
  python3 ~/.codex/scripts/autonomous_qa.py -p "$best_app"
  
  # Check actual QA progress after run
  read new_verified new_total <<< $(get_qa_progress "$best_app")
  if [ "$new_total" -gt 0 ]; then
    new_pct=$((new_verified * 100 / new_total))
  else
    new_pct=0
  fi
  
  echo "Result: $app_name now at $new_verified/$new_total ($new_pct%)"
  
  # Only mark verified if QA is actually 100%
  if [ "$new_pct" -ge 100 ] && [ ! -f "$best_app/.qa_verified" ]; then
    echo "🎉 $app_name QA complete! Creating verified marker..."
    echo "QA verified: $new_verified/$new_total checks passed" > "$best_app/.qa_verified"
    date >> "$best_app/.qa_verified"
  fi
  
  sleep 5
done
