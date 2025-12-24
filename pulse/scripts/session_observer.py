#!/usr/bin/env python3
"""
Session Observer - Tracks agent sessions and learns patterns
============================================================

Reads actual session data from:
- session_state.json (features completed, build results)
- Build logs (errors encountered)
- Git history (files modified)

Usage:
    python3 session_observer.py start <project_dir>   # Begin session
    python3 session_observer.py stop <project_dir>    # End and record
    python3 session_observer.py report                # Show patterns
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from file_lock import file_lock

OBSERVATIONS_FILE = Path.home() / ".codex" / "memory" / "session_observations.json"
INSIGHTS_FILE = Path.home() / ".codex" / "memory" / "learned_insights.json"


class SessionObserver:
    def __init__(self):
        self.observations = self._load_observations()
    
    def _load_observations(self) -> Dict:
        if OBSERVATIONS_FILE.exists():
            try:
                with file_lock(OBSERVATIONS_FILE):
                    with open(OBSERVATIONS_FILE) as f:
                        return json.load(f)
            except:
                pass
        return {"sessions": [], "patterns": {}}
    
    def _save_observations(self):
        OBSERVATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with file_lock(OBSERVATIONS_FILE):
            with open(OBSERVATIONS_FILE, 'w') as f:
                json.dump(self.observations, f, indent=2)
    
    def start_session(self, project_dir: Path) -> Dict:
        """Record session start. Returns session dict."""
        session = {
            "project": project_dir.name,
            "project_path": str(project_dir),
            "start_time": datetime.now().isoformat(),
            "files_modified": [],
            "errors_encountered": [],
            "fixes_applied": [],
            "features_completed": 0,
            "build_success": None
        }
        return session
    
    def end_session(self, project_dir: Path) -> Dict:
        """End session by reading actual data from project."""
        session = {
            "project": project_dir.name,
            "project_path": str(project_dir),
            "end_time": datetime.now().isoformat(),
        }
        
        # Read session_state.json for actual metrics
        state_path = project_dir / ".codex" / "memory" / "session_state.json"
        if state_path.exists():
            try:
                with open(state_path) as f:
                    state = json.load(f)
                session["start_time"] = state.get("session_start", session["end_time"])
                session["features_at_start"] = state.get("features_at_start", 0)
                session["features_at_end"] = state.get("features_at_end", 0)
                session["features_completed"] = state.get("features_completed_count", 0)
                session["build_results"] = state.get("build_results", [])
                session["build_success"] = any(b.get("success") for b in session["build_results"])
            except Exception as e:
                session["error"] = f"Failed to read session_state: {e}"
        
        # Get files modified from git
        session["files_modified"] = self._get_git_changes(project_dir)
        
        # Extract errors from build results
        session["errors_encountered"] = self._extract_errors(project_dir)
        
        # Calculate metrics
        session["metrics"] = {
            "features_completed": session.get("features_completed", 0),
            "files_touched": len(session.get("files_modified", [])),
            "errors_count": len(session.get("errors_encountered", [])),
            "build_success": session.get("build_success", False)
        }
        
        # Record patterns from this session
        self._record_patterns(session)
        
        # Save session
        self.observations["sessions"].append(session)
        self._save_observations()
        
        # Generate insights
        self._generate_insights()
        
        return session
    
    def _get_git_changes(self, project_dir: Path) -> List[str]:
        """Get list of files modified in recent commits."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split("\n") if f]
        except:
            pass
        return []
    
    def _extract_errors(self, project_dir: Path) -> List[Dict]:
        """Extract error patterns from build logs or session state."""
        errors = []
        state_path = project_dir / ".codex" / "memory" / "session_state.json"
        
        if state_path.exists():
            try:
                with open(state_path) as f:
                    state = json.load(f)
                for err in state.get("errors_encountered", []):
                    errors.append({
                        "type": err.get("type", "unknown"),
                        "message": err.get("message", "")[:200],
                        "resolved": err.get("resolved", False)
                    })
            except:
                pass
        
        return errors
    
    def _record_patterns(self, session: Dict):
        """Record patterns from session for future learning."""
        # Track feature velocity by project type
        project = session.get("project", "unknown")
        features = session.get("features_completed", 0)
        
        if "velocity" not in self.observations["patterns"]:
            self.observations["patterns"]["velocity"] = {}
        
        if project not in self.observations["patterns"]["velocity"]:
            self.observations["patterns"]["velocity"][project] = []
        
        self.observations["patterns"]["velocity"][project].append(features)
        
        # Track common errors
        if "errors" not in self.observations["patterns"]:
            self.observations["patterns"]["errors"] = {}
        
        for err in session.get("errors_encountered", []):
            err_type = err.get("type", "unknown")
            if err_type not in self.observations["patterns"]["errors"]:
                self.observations["patterns"]["errors"][err_type] = {"count": 0, "resolved": 0}
            self.observations["patterns"]["errors"][err_type]["count"] += 1
            if err.get("resolved"):
                self.observations["patterns"]["errors"][err_type]["resolved"] += 1
    
    def _generate_insights(self):
        """Generate insights from all sessions."""
        sessions = self.observations["sessions"]
        
        total_features = sum(s.get("features_completed", 0) for s in sessions)
        total_errors = sum(len(s.get("errors_encountered", [])) for s in sessions)
        
        insights = {
            "generated_at": datetime.now().isoformat(),
            "total_sessions": len(sessions),
            "total_features_completed": total_features,
            "total_errors_encountered": total_errors,
            "avg_features_per_session": total_features / max(len(sessions), 1),
            "recommendations": []
        }
        
        # Add recommendations based on patterns
        avg = insights["avg_features_per_session"]
        if avg < 10:
            insights["recommendations"].append("Low feature velocity - consider breaking down tasks")
        elif avg > 50:
            insights["recommendations"].append("High velocity - maintain current approach")
        
        if total_errors > total_features:
            insights["recommendations"].append("High error rate - review common error patterns")
        
        # Save insights
        INSIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with file_lock(INSIGHTS_FILE):
            with open(INSIGHTS_FILE, 'w') as f:
                json.dump(insights, f, indent=2)
        
        return insights
    
    def print_report(self):
        """Print summary report."""
        print("=" * 60)
        print("SESSION OBSERVER REPORT")
        print("=" * 60)
        
        sessions = self.observations["sessions"]
        print(f"\nTotal sessions: {len(sessions)}")
        
        if sessions:
            total_features = sum(s.get("features_completed", 0) for s in sessions)
            print(f"Total features completed: {total_features}")
            print(f"Avg per session: {total_features / len(sessions):.1f}")
            
            # Recent sessions
            print("\n--- Recent Sessions ---")
            for s in sessions[-5:]:
                proj = s.get("project", "unknown")
                feat = s.get("features_completed", 0)
                build = "✅" if s.get("build_success") else "❌"
                print(f"  {proj}: {feat} features {build}")
        
        # Patterns
        patterns = self.observations.get("patterns", {})
        if "errors" in patterns and patterns["errors"]:
            print("\n--- Error Patterns ---")
            for err_type, data in sorted(patterns["errors"].items(), 
                                         key=lambda x: x[1]["count"], reverse=True)[:5]:
                rate = data["resolved"] / data["count"] if data["count"] > 0 else 0
                print(f"  {err_type}: {data['count']} occurrences ({rate:.0%} resolved)")
        
        # Load insights
        if INSIGHTS_FILE.exists():
            with open(INSIGHTS_FILE) as f:
                insights = json.load(f)
            print("\n--- Recommendations ---")
            for rec in insights.get("recommendations", []):
                print(f"  • {rec}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 session_observer.py [start|stop|report] [project_dir]")
        sys.exit(1)
    
    command = sys.argv[1]
    observer = SessionObserver()
    
    if command == "start":
        project_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
        session = observer.start_session(project_dir)
        print(f"📊 Session started for {project_dir.name}")
        
    elif command == "stop":
        project_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
        session = observer.end_session(project_dir)
        features = session.get("features_completed", 0)
        print(f"📊 Session ended: {features} features completed")
        
    elif command == "report":
        observer.print_report()
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
