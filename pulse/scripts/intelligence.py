#!/usr/bin/env python3
"""
Intelligence Coordinator - Unified self-improving system
=========================================================

Orchestrates all intelligence components:
1. Build Intelligence - Error parsing and auto-fixing
2. Session Observer - Learning from agent behavior
3. Feature Generator - Learning from successful apps
4. Pattern Memory - Storing and retrieving learned patterns

Usage:
    python3 intelligence.py status              # Show system status
    python3 intelligence.py learn /path/to/app  # Learn from completed app
    python3 intelligence.py assist /path/to/app # Get assistance for current app
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Import our intelligence modules
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

MEMORY_DIR = Path.home() / ".codex" / "memory"

class IntelligenceCoordinator:
    def __init__(self):
        self.memory_files = {
            "build_patterns": MEMORY_DIR / "build_patterns.json",
            "feature_patterns": MEMORY_DIR / "feature_patterns.json",
            "session_observations": MEMORY_DIR / "session_observations.json",
            "learned_insights": MEMORY_DIR / "learned_insights.json",
        }
    
    def get_status(self) -> Dict:
        """Get status of all intelligence components."""
        status = {
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        for name, path in self.memory_files.items():
            if path.exists():
                try:
                    with open(path) as f:
                        data = json.load(f)
                    status["components"][name] = {
                        "exists": True,
                        "size_bytes": path.stat().st_size,
                        "entries": self._count_entries(data)
                    }
                except:
                    status["components"][name] = {"exists": True, "error": "parse_failed"}
            else:
                status["components"][name] = {"exists": False}
        
        return status
    
    def _count_entries(self, data: Dict) -> int:
        """Count entries in a data structure."""
        if isinstance(data, list):
            return len(data)
        elif isinstance(data, dict):
            total = 0
            for v in data.values():
                if isinstance(v, (list, dict)):
                    total += self._count_entries(v)
                else:
                    total += 1
            return total
        return 1
    
    def learn_from_app(self, project_dir: Path) -> Dict:
        """Learn from a completed app - extracts all patterns."""
        results = {"project": str(project_dir), "learned": {}}
        
        # 1. Learn feature patterns
        try:
            from feature_generator import FeatureGenerator
            fg = FeatureGenerator()
            result = fg.analyze_app(project_dir)
            results["learned"]["features"] = result
        except Exception as e:
            results["learned"]["features"] = {"error": str(e)}
        
        # 2. Analyze code patterns
        results["learned"]["code_patterns"] = self._analyze_code_patterns(project_dir)
        
        # 3. Record successful build configuration
        results["learned"]["build_config"] = self._extract_build_config(project_dir)
        
        return results
    
    def _analyze_code_patterns(self, project_dir: Path) -> Dict:
        """Extract reusable code patterns from Swift files."""
        patterns = {
            "view_modifiers": [],
            "common_imports": set(),
            "design_system_usage": False,
            "subscription_pattern": None,
        }
        
        swift_files = list(project_dir.rglob("*.swift"))
        
        for f in swift_files[:30]:  # Sample files
            try:
                content = f.read_text()
                
                # Check for design system
                if "DesignSystem" in content or "DS." in content:
                    patterns["design_system_usage"] = True
                
                # Extract imports
                for match in re.finditer(r'^import (\w+)', content, re.MULTILINE):
                    patterns["common_imports"].add(match.group(1))
                
                # Check subscription pattern
                if "SubscriptionManager" in content or "StoreKit" in content:
                    patterns["subscription_pattern"] = "storekit"
                elif "RevenueCat" in content:
                    patterns["subscription_pattern"] = "revenuecat"
                
            except:
                pass
        
        patterns["common_imports"] = list(patterns["common_imports"])
        return patterns
    
    def _extract_build_config(self, project_dir: Path) -> Dict:
        """Extract build configuration that worked."""
        config = {}
        
        # Check for xcodeproj
        xcodeprojs = list(project_dir.glob("*.xcodeproj"))
        if xcodeprojs:
            config["has_xcodeproj"] = True
            config["project_name"] = xcodeprojs[0].stem
        
        # Check for Info.plist settings
        info_plists = list(project_dir.rglob("Info.plist"))
        if info_plists:
            config["has_info_plist"] = True
        
        return config
    
    def get_assistance(self, project_dir: Path) -> Dict:
        """Get intelligent assistance for current project."""
        assistance = {
            "project": str(project_dir),
            "recommendations": [],
            "warnings": [],
            "next_steps": []
        }
        
        # Check feature count
        feature_list = project_dir / "feature_list.json"
        if feature_list.exists():
            with open(feature_list) as f:
                data = json.load(f)
            
            if isinstance(data, dict) and "test_suite" in data:
                features = data["test_suite"]
            else:
                features = data
            
            passing = sum(1 for f in features if isinstance(f, dict) and f.get("passes"))
            total = len(features)
            
            if total < 300:
                assistance["warnings"].append(f"Only {total} features - need 300+ for completion")
                assistance["next_steps"].append("Run: python3 ~/.codex/scripts/feature_generator.py expand .")
            
            if passing < total:
                failing = total - passing
                assistance["next_steps"].append(f"Implement {failing} failing features")
        else:
            assistance["warnings"].append("No feature_list.json found")
            assistance["next_steps"].append("Run: python3 ~/.codex/scripts/feature_generator.py generate .")
        
        # Check for common issues
        swift_files = list(project_dir.rglob("*.swift"))
        issues = self._quick_code_check(swift_files[:20])
        assistance["warnings"].extend(issues)
        
        # Load learned insights
        insights_file = MEMORY_DIR / "learned_insights.json"
        if insights_file.exists():
            with open(insights_file) as f:
                insights = json.load(f)
            assistance["recommendations"].extend(insights.get("recommendations", []))
        
        return assistance
    
    def _quick_code_check(self, swift_files: List[Path]) -> List[str]:
        """Quick check for common issues."""
        issues = []
        
        for f in swift_files:
            try:
                content = f.read_text()
                
                # Check for hardcoded colors
                if re.search(r'\.foregroundStyle\s*\(\s*\.white\s*\)', content):
                    if ".background" not in content[:content.find(".white") + 100]:
                        issues.append(f"{f.name}: Hardcoded .white without dark background")
                
                # Check for small touch targets
                if "Button" in content and ".frame(minWidth: 44" not in content:
                    if "Image(systemName:" in content:
                        issues.append(f"{f.name}: Icon buttons may need 44pt touch targets")
                
            except:
                pass
        
        return issues[:5]  # Limit to 5 issues
    
    def query_patterns(self, app_type: str = None, category: str = None) -> Dict:
        """Query feature patterns by app type or category."""
        patterns_file = self.memory_files["feature_patterns"]
        if not patterns_file.exists():
            return {"error": "feature_patterns.json not found"}
        
        with open(patterns_file) as f:
            data = json.load(f)
        
        results = {"query": {"app_type": app_type, "category": category}, "patterns": []}
        
        # Get app types
        app_types = data.get("app_types", {})
        common = data.get("common_features", [])
        
        if app_type and app_type in app_types:
            # app_types values can be lists or dicts
            type_data = app_types[app_type]
            if isinstance(type_data, list):
                results["patterns"] = type_data[:50]  # Limit to 50
                results["total_patterns"] = len(type_data)
            elif isinstance(type_data, dict):
                results["patterns"] = type_data.get("features", [])[:50]
                results["source_apps"] = type_data.get("source_apps", [])
        elif category:
            # Search across all app types for category keyword
            for atype, type_data in app_types.items():
                patterns = type_data if isinstance(type_data, list) else type_data.get("features", [])
                for feat in patterns:
                    if isinstance(feat, dict):
                        if category.lower() in feat.get("category", "").lower():
                            results["patterns"].append(feat)
                    elif isinstance(feat, str):
                        if category.lower() in feat.lower():
                            results["patterns"].append({"name": feat, "source": atype})
                if len(results["patterns"]) >= 50:
                    break
        else:
            # Return common features and available app types
            results["patterns"] = common[:50] if common else []
            results["app_types_available"] = list(app_types.keys())
            results["pattern_counts"] = {k: len(v) if isinstance(v, list) else len(v.get("features", [])) for k, v in app_types.items()}
        
        return results
    
    def print_status(self):
        """Print formatted status."""
        status = self.get_status()
        
        print("=" * 60)
        print("INTELLIGENCE SYSTEM STATUS")
        print("=" * 60)
        print(f"Timestamp: {status['timestamp']}")
        print()
        
        for name, info in status["components"].items():
            if info.get("exists"):
                if "error" in info:
                    print(f"  ❌ {name}: Error - {info['error']}")
                else:
                    print(f"  ✅ {name}: {info['entries']} entries ({info['size_bytes']} bytes)")
            else:
                print(f"  ⚪ {name}: Not initialized")
        
        print()
        print("To initialize: python3 intelligence.py learn /path/to/completed/app")


# Need this import for _analyze_code_patterns
import re


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 intelligence.py status")
        print("  python3 intelligence.py learn /path/to/app")
        print("  python3 intelligence.py assist /path/to/app")
        print("  python3 intelligence.py query [app_type] [--category CAT]")
        sys.exit(1)
    
    command = sys.argv[1]
    ic = IntelligenceCoordinator()
    
    if command == "status":
        ic.print_status()
    
    elif command == "learn":
        if len(sys.argv) < 3:
            print("Usage: python3 intelligence.py learn /path/to/app")
            sys.exit(1)
        project_dir = Path(sys.argv[2])
        results = ic.learn_from_app(project_dir)
        print(json.dumps(results, indent=2))
    
    elif command == "query":
        app_type = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
        category = None
        if "--category" in sys.argv:
            idx = sys.argv.index("--category")
            if idx + 1 < len(sys.argv):
                category = sys.argv[idx + 1]
        
        results = ic.query_patterns(app_type, category)
        print(json.dumps(results, indent=2))
    
    elif command == "assist":
        if len(sys.argv) < 3:
            print("Usage: python3 intelligence.py assist /path/to/app")
            sys.exit(1)
        project_dir = Path(sys.argv[2])
        assistance = ic.get_assistance(project_dir)
        
        print("=" * 60)
        print(f"ASSISTANCE FOR: {project_dir.name}")
        print("=" * 60)
        
        if assistance["warnings"]:
            print("\n⚠️  Warnings:")
            for w in assistance["warnings"]:
                print(f"  • {w}")
        
        if assistance["recommendations"]:
            print("\n💡 Recommendations:")
            for r in assistance["recommendations"]:
                print(f"  • {r}")
        
        if assistance["next_steps"]:
            print("\n📋 Next Steps:")
            for i, step in enumerate(assistance["next_steps"], 1):
                print(f"  {i}. {step}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
