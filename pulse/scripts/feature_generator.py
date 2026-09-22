#!/usr/bin/env python3
from file_lock import file_lock
"""
Feature Generator - Learns from successful apps to generate features
====================================================================

Capabilities:
1. Analyze completed apps to extract feature patterns
2. Generate feature_list.json entries based on app type
3. Ensure 300+ features with proper coverage

Usage:
    python3 feature_generator.py analyze /path/to/completed/app  # Learn patterns
    python3 feature_generator.py generate /path/to/new/app       # Generate features
    python3 feature_generator.py expand /path/to/app             # Expand to 300+
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

FEATURE_PATTERNS_FILE = Path.home() / ".codex" / "memory" / "feature_patterns.json"

# Core feature categories that every iOS app should have
CORE_CATEGORIES = {
    "navigation": [
        "App has TabView or NavigationStack",
        "Navigation between screens works",
        "Back navigation works correctly",
        "Deep linking supported",
    ],
    "ui_foundation": [
        "Main content view exists",
        "Empty state view exists",
        "Loading state indicator exists",
        "Error state handling exists",
    ],
    "accessibility": [
        "All buttons have 44pt minimum touch targets",
        "VoiceOver labels on interactive elements",
        "Dynamic Type supported",
        "Color contrast meets WCAG AA",
        "Reduce Motion respected",
    ],
    "data": [
        "Data persistence implemented",
        "Data loads on app launch",
        "Data saves automatically",
        "Data can be deleted",
        "Data can be edited",
    ],
    "settings": [
        "Settings screen exists",
        "Theme preference (light/dark/auto)",
        "App version displayed",
        "Privacy policy link",
        "Terms of service link",
    ],
    "onboarding": [
        "Onboarding flow exists",
        "Skip button in top right",
        "Onboarding completes correctly",
        "Onboarding only shows once",
    ],
    "subscription": [
        "Paywall screen exists",
        "Subscription tiers displayed",
        "Purchase flow works",
        "Restore purchases works",
        "Pro features gated correctly",
    ],
    "search": [
        "Search bar exists",
        "Search filters results",
        "Search handles empty results",
        "Search is case-insensitive",
    ],
    "list_management": [
        "Items can be created",
        "Items can be deleted",
        "Items can be edited",
        "Items can be reordered",
        "Swipe actions work",
    ],
    "visual_polish": [
        "Consistent spacing (Fibonacci)",
        "Consistent typography",
        "Animations are smooth",
        "Colors adapt to dark mode",
        "No hardcoded colors",
    ],
}

class FeatureGenerator:
    def __init__(self):
        self.patterns = self._load_patterns()
    
    def get_patterns_for_type(self, app_type: str, limit: int = 50) -> List[str]:
        """Retrieve feature patterns for a specific app type."""
        if app_type in self.patterns.get("app_types", {}):
            return self.patterns["app_types"][app_type][:limit]
        # Fallback to general patterns
        all_patterns = []
        for patterns in self.patterns.get("app_types", {}).values():
            all_patterns.extend(patterns)
        return list(set(all_patterns))[:limit]
    
    def query_patterns(self, keywords: List[str], limit: int = 20) -> List[str]:
        """Query patterns by keywords."""
        results = []
        all_patterns = []
        for patterns in self.patterns.get("app_types", {}).values():
            all_patterns.extend(patterns)
        
        for pattern in all_patterns:
            pattern_lower = pattern.lower()
            if any(kw.lower() in pattern_lower for kw in keywords):
                results.append(pattern)
                if len(results) >= limit:
                    break
        return results
    
    def _load_patterns(self) -> Dict:
        if FEATURE_PATTERNS_FILE.exists():
            try:
                with open(FEATURE_PATTERNS_FILE) as f:
                    return json.load(f)
            except:
                pass
        return {"app_types": {}, "common_features": [], "learned_from": []}
    
    def _save_patterns(self):
        FEATURE_PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with file_lock(FEATURE_PATTERNS_FILE):
            with open(FEATURE_PATTERNS_FILE, "w") as f:
                json.dump(self.patterns, f, indent=2)
    
    def analyze_app(self, project_dir: Path) -> Dict:
        """Analyze a completed app to extract feature patterns."""
        feature_list_path = project_dir / "feature_list.json"
        if not feature_list_path.exists():
            print(f"❌ No feature_list.json found in {project_dir}")
            return {}
        
        with open(feature_list_path) as f:
            data = json.load(f)
        
        # Handle test_suite structure
        if isinstance(data, dict) and "test_suite" in data:
            features = data["test_suite"]
        else:
            features = data
        
        # Extract feature descriptions
        descriptions = []
        for feature in features:
            if isinstance(feature, dict):
                desc = feature.get("description", feature.get("name", ""))
            else:
                desc = str(feature)
            if desc:
                descriptions.append(desc)
        
        # Detect app type from features
        app_type = self._detect_app_type(descriptions, project_dir)
        
        # Store patterns
        if app_type not in self.patterns["app_types"]:
            self.patterns["app_types"][app_type] = []
        
        self.patterns["app_types"][app_type].extend(descriptions)
        self.patterns["app_types"][app_type] = list(set(self.patterns["app_types"][app_type]))
        self.patterns["learned_from"].append(str(project_dir))
        
        self._save_patterns()
        
        print(f"✅ Analyzed {len(descriptions)} features from {project_dir.name}")
        print(f"   App type detected: {app_type}")
        
        return {"app_type": app_type, "feature_count": len(descriptions)}
    
    def _detect_app_type(self, descriptions: List[str], project_dir: Path) -> str:
        """Detect app type from features and code."""
        desc_text = " ".join(descriptions).lower()
        
        # Check for app type indicators
        if any(x in desc_text for x in ["recipe", "cooking", "ingredient", "meal"]):
            return "recipe_app"
        elif any(x in desc_text for x in ["workout", "exercise", "fitness", "gym"]):
            return "fitness_app"
        elif any(x in desc_text for x in ["note", "journal", "diary", "writing"]):
            return "notes_app"
        elif any(x in desc_text for x in ["task", "todo", "reminder", "checklist"]):
            return "task_app"
        elif any(x in desc_text for x in ["photo", "image", "gallery", "camera"]):
            return "photo_app"
        elif any(x in desc_text for x in ["finance", "budget", "expense", "money"]):
            return "finance_app"
        elif any(x in desc_text for x in ["weather", "forecast", "temperature"]):
            return "weather_app"
        elif any(x in desc_text for x in ["music", "audio", "playlist", "song"]):
            return "music_app"
        elif any(x in desc_text for x in ["social", "chat", "message", "friend"]):
            return "social_app"
        else:
            return "general_app"
    
    def generate_features(self, project_dir: Path, app_type: str = None) -> List[Dict]:
        """Generate feature list for a new app."""
        if app_type is None:
            app_type = self._detect_app_type_from_code(project_dir)
        
        features = []
        feature_id = 1
        
        # Add core features for all apps
        for category, items in CORE_CATEGORIES.items():
            for desc in items:
                features.append({
                    "id": feature_id,
                    "category": category,
                    "description": desc,
                    "passes": False
                })
                feature_id += 1
        
        # Add app-type specific features from learned patterns
        if app_type in self.patterns["app_types"]:
            for desc in self.patterns["app_types"][app_type][:100]:
                if not any(f["description"] == desc for f in features):
                    features.append({
                        "id": feature_id,
                        "category": "app_specific",
                        "description": desc,
                        "passes": False
                    })
                    feature_id += 1
        
        # Expand to 300+ if needed
        features = self._expand_features(features, app_type)
        
        return features
    
    def _detect_app_type_from_code(self, project_dir: Path) -> str:
        """Detect app type by analyzing Swift code."""
        swift_files = list(project_dir.rglob("*.swift"))
        code_text = ""
        for f in swift_files[:20]:  # Sample first 20 files
            try:
                code_text += f.read_text().lower()
            except:
                pass
        
        return self._detect_app_type([code_text], project_dir)
    
    def _expand_features(self, features: List[Dict], app_type: str) -> List[Dict]:
        """Expand feature list to 300+ with detailed sub-features."""
        if len(features) >= 300:
            return features
        
        feature_id = max(f["id"] for f in features) + 1
        
        # Expansion templates
        expansions = {
            "ui_states": [
                "{item} shows loading state",
                "{item} shows empty state",
                "{item} shows error state",
                "{item} shows success state",
            ],
            "interactions": [
                "{item} responds to tap",
                "{item} responds to long press",
                "{item} responds to swipe",
                "{item} has haptic feedback",
            ],
            "accessibility_detail": [
                "{item} has accessibility label",
                "{item} has accessibility hint",
                "{item} supports VoiceOver",
                "{item} has sufficient contrast",
            ],
            "animations": [
                "{item} has enter animation",
                "{item} has exit animation",
                "{item} respects reduce motion",
            ],
            "edge_cases": [
                "{item} handles empty input",
                "{item} handles long text",
                "{item} handles special characters",
                "{item} handles offline state",
            ],
        }
        
        # UI elements to expand
        ui_elements = [
            "Main list", "Detail view", "Settings screen", "Search bar",
            "Add button", "Delete button", "Edit button", "Save button",
            "Navigation bar", "Tab bar", "Modal sheet", "Alert dialog",
            "Text field", "Toggle switch", "Picker", "Slider",
            "Profile section", "Header view", "Footer view", "Empty view",
        ]
        
        for element in ui_elements:
            for category, templates in expansions.items():
                for template in templates:
                    if len(features) >= 300:
                        break
                    desc = template.format(item=element)
                    if not any(f["description"] == desc for f in features):
                        features.append({
                            "id": feature_id,
                            "category": category,
                            "description": desc,
                            "passes": False
                        })
                        feature_id += 1
        
        return features
    
    def expand_existing(self, project_dir: Path) -> int:
        """Expand existing feature_list.json to 300+."""
        feature_list_path = project_dir / "feature_list.json"
        if not feature_list_path.exists():
            print("❌ No feature_list.json found")
            return 0
        
        with open(feature_list_path) as f:
            data = json.load(f)
        
        # Handle test_suite structure
        if isinstance(data, dict) and "test_suite" in data:
            features = data["test_suite"]
            is_test_suite = True
        else:
            features = data
            is_test_suite = False
        
        original_count = len(features)
        if original_count >= 300:
            print(f"✅ Already has {original_count} features")
            return 0
        
        # Detect app type
        descriptions = [f.get("description", "") if isinstance(f, dict) else str(f) for f in features]
        app_type = self._detect_app_type(descriptions, project_dir)
        
        # Generate additional features
        expanded = self._expand_features(features, app_type)
        
        # Save
        if is_test_suite:
            data["test_suite"] = expanded
        else:
            data = expanded
        
        with open(feature_list_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        added = len(expanded) - original_count
        print(f"✅ Expanded from {original_count} to {len(expanded)} features (+{added})")
        
        return added


def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python3 feature_generator.py analyze /path/to/completed/app")
        print("  python3 feature_generator.py generate /path/to/new/app")
        print("  python3 feature_generator.py expand /path/to/app")
        sys.exit(1)
    
    command = sys.argv[1]
    project_dir = Path(sys.argv[2])
    
    fg = FeatureGenerator()
    
    if command == "analyze":
        fg.analyze_app(project_dir)
    elif command == "generate":
        features = fg.generate_features(project_dir)
        output_path = project_dir / "feature_list.json"
        with open(output_path, 'w') as f:
            json.dump({"test_suite": features}, f, indent=2)
        print(f"✅ Generated {len(features)} features to {output_path}")
    elif command == "expand":
        fg.expand_existing(project_dir)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
