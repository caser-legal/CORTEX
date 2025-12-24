#!/bin/bash
# Build IN-PROGRESS apps (<300 passing) - focuses on closest to 300 first

IOS_DIR="/Users/home/Documents/iOS"

echo "=== AUTOOGPT Batch Builder (Build apps to 300+ features) ==="

get_passing() {
  grep -c '"passes": true' "$1/feature_list.json" 2>/dev/null | tr -d '[:space:]' || echo 0
}

while true; do
  # Find app closest to 300 (highest passing < 300)
  best_app=""
  best_passing=0
  
  for dir in "$IOS_DIR"/*/; do
    [ -f "$dir/feature_list.json" ] || continue
    passing=$(get_passing "$dir")
    [[ "$passing" =~ ^[0-9]+$ ]] || passing=0
    
    if [ "$passing" -lt 300 ] && [ "$passing" -gt "$best_passing" ]; then
      best_passing=$passing
      best_app="$dir"
    fi
  done
  
  if [ -z "$best_app" ]; then
    echo "✅ All apps have 300+ features! Sleeping 60s..."
    sleep 60
    continue
  fi
  
  app_name=$(basename "$best_app")
  echo ""
  echo "🔨 Building: $app_name ($best_passing/300)"
  echo "================================================"
  
  # Run autonomous.py until this app reaches 300+
  python3 ~/.codex/scripts/autonomous.py -p "$best_app"
  
  new_passing=$(get_passing "$best_app")
  if [ "$new_passing" -ge 300 ]; then
    echo "✅ $app_name complete! ($new_passing/300)"
  fi
  
  sleep 5
done
