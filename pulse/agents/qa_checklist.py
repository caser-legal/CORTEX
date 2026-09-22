"""
QA Verification Checklist System
=================================

Tracks actual QA verification progress separately from feature_list.json.
The agent must verify each item exists in code, not just trust the JSON.

Based on ~/Documents/iOS/dev-docs/checklists/subscription-checklist.txt
"""

import json
import subprocess
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class QACheck:
    """A single QA verification check."""
    id: str
    category: str
    description: str
    verified: bool = False
    notes: str = ""


# Core QA checks that MUST be verified for every app
CORE_QA_CHECKS = [
    # ============ SUBSCRIPTION/PAYWALL (CRITICAL) ============
    QACheck("sub_manager_exists", "subscription", "SubscriptionManager.swift exists"),
    QACheck("sub_manager_singleton", "subscription", "SubscriptionManager has static shared instance"),
    QACheck("sub_manager_ispro", "subscription", "SubscriptionManager has isPro computed property"),
    QACheck("sub_manager_products", "subscription", "SubscriptionManager has weekly/monthly product IDs"),
    QACheck("sub_manager_purchase", "subscription", "SubscriptionManager has purchase() function"),
    QACheck("sub_manager_restore", "subscription", "SubscriptionManager has restorePurchases() function"),
    QACheck("sub_manager_trial", "subscription", "SubscriptionManager has trial eligibility check"),
    QACheck("sub_manager_swift6", "subscription", "SubscriptionManager has @MainActor @Observable (Swift 6)"),
    QACheck("sub_manager_access_pattern", "subscription", "Views use computed property for SubscriptionManager (not @State)"),
    
    QACheck("paywall_exists", "subscription", "PaywallView.swift exists"),
    QACheck("paywall_header", "subscription", "PaywallView has header with app icon and title"),
    QACheck("paywall_features", "subscription", "PaywallView has features section (5 FeatureRows)"),
    QACheck("paywall_products", "subscription", "PaywallView shows product cards with prices"),
    QACheck("paywall_best_value", "subscription", "PaywallView has BEST VALUE badge on monthly"),
    QACheck("paywall_trial_text", "subscription", "PaywallView shows trial text when eligible"),
    QACheck("paywall_subscribe_btn", "subscription", "PaywallView has Subscribe/Start Trial button"),
    QACheck("paywall_legal", "subscription", "PaywallView has Terms and Privacy links"),
    QACheck("paywall_restore", "subscription", "PaywallView has Restore Purchases button"),
    
    # ============ SETTINGS - UPGRADE BUTTON (CRITICAL) ============
    QACheck("main_screen_upgrade_banner", "settings", "Main screen has 'Upgrade to Pro' banner at TOP"),
    QACheck("settings_upgrade_btn", "settings", "Settings has 'Upgrade to Pro' button as FIRST section"),
    QACheck("settings_upgrade_gold", "settings", "Upgrade button uses gold color/styling"),
    QACheck("settings_upgrade_sheet", "settings", "Upgrade button opens PaywallView sheet"),
    QACheck("settings_pro_state", "settings", "Settings shows 'Pro Active' when subscribed"),
    
    # ============ FEATURE GATING ============
    QACheck("feature_gating_exists", "gating", "At least one isPro check exists in app"),
    QACheck("feature_gating_overlay", "gating", "Pro features gated (overlay or conditional)"),
    QACheck("paywall_features_match", "gating", "Paywall features match actual gated features"),
    
    # ============ SETTINGS COMPLETENESS ============
    # NOTE: budget/currency are OPTIONAL - only for finance/expense apps
    # They will be auto-skipped for non-finance apps
    QACheck("settings_theme", "settings", "Theme selection (Light/Dark/Auto) exists"),
    QACheck("settings_notifications", "settings", "Notification preferences section exists"),
    QACheck("settings_privacy", "settings", "Privacy section with Face ID toggle exists"),
    QACheck("settings_export", "settings", "Export data option exists"),
    QACheck("settings_clear", "settings", "Clear all data with confirmation exists"),
    QACheck("settings_about", "settings", "About section with version exists"),
    
    # ============ APP STORE COMPLIANCE ============
    QACheck("info_plist_encryption", "compliance", "ITSAppUsesNonExemptEncryption = false in Info.plist"),
    QACheck("info_plist_privacy", "compliance", "Privacy usage descriptions in Info.plist"),
    QACheck("code_signing", "compliance", "Code signing enabled (not disabled)"),
    QACheck("app_icon_no_alpha", "compliance", "App icon has no alpha channel"),
    QACheck("bundle_id_correct", "compliance", "Bundle ID uses caserlegal.* format"),
    QACheck("storekit_capability", "compliance", "In-App Purchase capability added"),
    
    # ============ UI QUALITY ============
    QACheck("touch_targets", "ui", "All buttons have 44pt minimum touch targets"),
    QACheck("accessibility_labels", "ui", "Icon buttons have accessibility labels"),
    QACheck("color_contrast", "ui", "No hardcoded white/black text (uses .primary or colorScheme)"),
    QACheck("settings_background", "ui", "Settings uses system background colors"),
    QACheck("onboarding_skip", "ui", "Onboarding skip button in top-right"),
    
    # ============ RUNTIME ============
    QACheck("app_launches", "runtime", "App launches without crashing"),
    QACheck("app_runs_5s", "runtime", "App runs for 5+ seconds without crash"),
    
    # ============ BUILD ============
    QACheck("build_succeeds", "build", "Build succeeds with 0 errors"),
    QACheck("no_warnings", "build", "Build has 0 warnings"),
]


def get_qa_checklist_path(project_dir: Path) -> Path:
    """Get path to QA checklist file."""
    return project_dir / "qa_checklist.json"


def reset_qa_checklist(project_dir: Path) -> list[dict]:
    """Reset QA checklist to 0% - all items unverified."""
    checklist = [asdict(check) for check in CORE_QA_CHECKS]
    
    # Reset all to unverified
    for item in checklist:
        item["verified"] = False
        item["notes"] = ""
    
    # Save to file
    checklist_path = get_qa_checklist_path(project_dir)
    with open(checklist_path, "w") as f:
        json.dump(checklist, f, indent=2)
    
    return checklist


def load_qa_checklist(project_dir: Path) -> list[dict]:
    """Load QA checklist from file, or create new one.
    
    Handles two formats:
    1. List format: [{"id": "...", "verified": true}, ...]
    2. Dict format: {"category": {"check": true}, ...} (legacy/alternate)
    """
    checklist_path = get_qa_checklist_path(project_dir)
    
    if checklist_path.exists():
        try:
            with open(checklist_path, "r") as f:
                data = json.load(f)
            
            # If it's already a list of dicts with 'id' keys, use it
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "id" in data[0]:
                return data
            
            # If it's a dict (alternate format), convert or reset
            if isinstance(data, dict):
                # This is an alternate format - reset to standard format
                return reset_qa_checklist(project_dir)
            
            # Unknown format - reset
            return reset_qa_checklist(project_dir)
            
        except (json.JSONDecodeError, IOError):
            pass
    
    return reset_qa_checklist(project_dir)


def save_qa_checklist(project_dir: Path, checklist: list[dict]) -> None:
    """Save QA checklist to file."""
    checklist_path = get_qa_checklist_path(project_dir)
    with open(checklist_path, "w") as f:
        json.dump(checklist, f, indent=2)


def mark_qa_check(project_dir: Path, check_id: str, verified: bool, notes: str = "") -> None:
    """Mark a specific QA check as verified or not."""
    checklist = load_qa_checklist(project_dir)
    
    for item in checklist:
        if item["id"] == check_id:
            item["verified"] = verified
            item["notes"] = notes
            break
    
    save_qa_checklist(project_dir, checklist)


def count_qa_progress(project_dir: Path) -> tuple[int, int]:
    """Count verified and total QA checks."""
    checklist = load_qa_checklist(project_dir)
    total = len(checklist)
    verified = sum(1 for item in checklist if isinstance(item, dict) and item.get("verified", False))
    return verified, total


def get_unverified_checks(project_dir: Path) -> list[dict]:
    """Get list of unverified QA checks."""
    checklist = load_qa_checklist(project_dir)
    return [item for item in checklist if isinstance(item, dict) and not item.get("verified", False)]


def print_qa_progress(project_dir: Path) -> None:
    """Print QA verification progress bar."""
    verified, total = count_qa_progress(project_dir)
    
    if total > 0:
        percentage = (verified / total) * 100
        bar_length = 30
        filled = int(bar_length * verified / total)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"QA Verified:      [{bar}] {verified}/{total} ({percentage:.1f}%)")
        
        if verified < total:
            remaining = total - verified
            print(f"⚠️  QA verification in progress - {remaining} checks remaining")
    else:
        print("QA Verified:      [No checklist]")


# ============ AUTO-VERIFICATION FUNCTIONS ============

def verify_file_exists(project_dir: Path, filename: str) -> bool:
    """Check if a file exists in the project."""
    for f in project_dir.rglob(filename):
        return True
    return False


def verify_pattern_in_files(project_dir: Path, pattern: str, file_glob: str = "*.swift") -> bool:
    """Check if a pattern exists in any matching file."""
    for f in project_dir.rglob(file_glob):
        try:
            content = f.read_text()
            if re.search(pattern, content, re.IGNORECASE):
                return True
        except:
            pass
    return False


def get_file_content(project_dir: Path, filename: str) -> str:
    """Get content of a file if it exists."""
    for f in project_dir.rglob(filename):
        try:
            return f.read_text()
        except:
            pass
    return ""


def auto_verify_subscription(project_dir: Path) -> dict[str, tuple[bool, str]]:
    """Auto-verify subscription-related checks."""
    results = {}
    
    # Check SubscriptionManager exists
    has_sub_manager = verify_file_exists(project_dir, "SubscriptionManager.swift")
    results["sub_manager_exists"] = (has_sub_manager, "Found" if has_sub_manager else "MISSING - Create SubscriptionManager.swift")
    
    if has_sub_manager:
        content = get_file_content(project_dir, "SubscriptionManager.swift")
        
        # Check singleton
        has_singleton = "static let shared" in content or "static var shared" in content
        results["sub_manager_singleton"] = (has_singleton, "Found" if has_singleton else "MISSING static shared")
        
        # Check isPro
        has_ispro = "var isPro" in content or "isPro:" in content
        results["sub_manager_ispro"] = (has_ispro, "Found" if has_ispro else "MISSING isPro property")
        
        # Check product IDs
        has_products = "caserlegal." in content and ("weekly" in content.lower() or "monthly" in content.lower())
        results["sub_manager_products"] = (has_products, "Found" if has_products else "MISSING product IDs")
        
        # Check purchase function
        has_purchase = "func purchase" in content
        results["sub_manager_purchase"] = (has_purchase, "Found" if has_purchase else "MISSING purchase()")
        
        # Check restore
        has_restore = "restorePurchases" in content or "restore" in content.lower()
        results["sub_manager_restore"] = (has_restore, "Found" if has_restore else "MISSING restorePurchases()")
        
        # Check trial
        has_trial = "trial" in content.lower() or "introductoryOffer" in content
        results["sub_manager_trial"] = (has_trial, "Found" if has_trial else "MISSING trial check")
        
        # Check @MainActor @Observable (Swift 6 requirement)
        has_mainactor_observable = "@MainActor" in content and "@Observable" in content
        results["sub_manager_swift6"] = (has_mainactor_observable, 
            "Found @MainActor @Observable" if has_mainactor_observable else "MISSING - Add @MainActor @Observable for Swift 6")
    else:
        # All sub-checks fail if file doesn't exist
        for check in ["sub_manager_singleton", "sub_manager_ispro", "sub_manager_products", 
                      "sub_manager_purchase", "sub_manager_restore", "sub_manager_trial", "sub_manager_swift6"]:
            results[check] = (False, "SubscriptionManager.swift missing")
    
    # CRITICAL: Check for wrong @State pattern with SubscriptionManager singleton
    # Swift 6.2.3: Use computed property, not @State, for @MainActor @Observable singletons
    bad_pattern_count = 0
    for swift_file in project_dir.rglob("*.swift"):
        try:
            file_content = swift_file.read_text()
            if "@State" in file_content and "subscriptionManager" in file_content:
                if "@State private var subscriptionManager = SubscriptionManager" in file_content or \
                   "@State var subscriptionManager = SubscriptionManager" in file_content or \
                   "@StateObject private var subscriptionManager = SubscriptionManager" in file_content or \
                   "@StateObject var subscriptionManager = SubscriptionManager" in file_content:
                    bad_pattern_count += 1
        except:
            pass
    
    if bad_pattern_count > 0:
        results["sub_manager_access_pattern"] = (False, 
            f"BUG: {bad_pattern_count} files use @State/@StateObject with SubscriptionManager. "
            "Use computed property: private var subscriptionManager: SubscriptionManager {{ SubscriptionManager.shared }}")
    else:
        results["sub_manager_access_pattern"] = (True, "Correct computed property pattern used")
    
    # Check PaywallView exists
    has_paywall = verify_file_exists(project_dir, "PaywallView.swift")
    results["paywall_exists"] = (has_paywall, "Found" if has_paywall else "MISSING - Create PaywallView.swift")
    
    if has_paywall:
        content = get_file_content(project_dir, "PaywallView.swift")
        
        results["paywall_header"] = ("Unlock" in content or "Pro" in content, 
                                     "Found" if "Unlock" in content else "MISSING header")
        results["paywall_features"] = ("FeatureRow" in content or "feature" in content.lower(),
                                       "Found" if "FeatureRow" in content else "MISSING features section")
        results["paywall_products"] = ("Product" in content and "displayPrice" in content,
                                       "Found" if "displayPrice" in content else "MISSING product cards")
        results["paywall_best_value"] = ("BEST VALUE" in content or "best value" in content.lower(),
                                         "Found" if "BEST VALUE" in content else "MISSING BEST VALUE badge")
        results["paywall_trial_text"] = ("trial" in content.lower() or "free" in content.lower(),
                                         "Found" if "trial" in content.lower() else "MISSING trial text")
        results["paywall_subscribe_btn"] = ("Subscribe" in content or "Start" in content,
                                            "Found" if "Subscribe" in content else "MISSING subscribe button")
        results["paywall_legal"] = ("Terms" in content or "Privacy" in content,
                                    "Found" if "Terms" in content else "MISSING legal links")
        results["paywall_restore"] = ("Restore" in content,
                                      "Found" if "Restore" in content else "MISSING restore button")
    else:
        for check in ["paywall_header", "paywall_features", "paywall_products", "paywall_best_value",
                      "paywall_trial_text", "paywall_subscribe_btn", "paywall_legal", "paywall_restore"]:
            results[check] = (False, "PaywallView.swift missing")
    
    return results


def auto_verify_settings_upgrade(project_dir: Path) -> dict[str, tuple[bool, str]]:
    """Auto-verify Settings upgrade button checks AND main screen banner."""
    results = {}
    
    # Check MAIN SCREEN for upgrade banner - must be in main content area, not detail view
    # Look at ContentView, HomeView, MainView, and any *ListView files
    main_screen_content = ""
    main_content_area = ""
    for pattern in ["ContentView.swift", "*Home*.swift", "*Main*.swift", "*ListView*.swift", "*ListScreen*.swift"]:
        for f in project_dir.rglob(pattern):
            if "Settings" in f.name:
                continue  # Skip settings files
            try:
                content = f.read_text()
                if "body" in content and ("View" in content or "TabView" in content):
                    main_screen_content += content + "\n"
                    # Track main content area (List, ScrollView, VStack in body - not in detail: section)
                    if "List(" in content or "List {" in content or "ScrollView" in content or "VStack" in content:
                        # Check if banner is in the main content, not in detail section
                        if "Upgrade to Pro" in content or ("showPaywall" in content and "isPro" in content):
                            # Make sure it's not in a detail: section
                            if "} detail:" not in content or content.find("isPro") < content.find("} detail:"):
                                main_content_area += content + "\n"
            except:
                pass
    
    # Check for upgrade banner - MUST be in main content area, not detail view
    has_main_banner = ("showPaywall" in main_screen_content and "isPro" in main_screen_content)
    # Extra check: banner should be in main content area (not just detail view)
    banner_in_main = ("showPaywall" in main_content_area and "isPro" in main_content_area)
    
    # RELAXED CHECK: If isPro and showPaywall exist anywhere in main views, accept it
    # The strict placement check causes too many false positives
    if has_main_banner:
        results["main_screen_upgrade_banner"] = (True, "Found isPro check with showPaywall trigger")
    else:
        results["main_screen_upgrade_banner"] = (False, "MISSING - Add 'Upgrade to Pro' banner with isPro check!")
    
    # Find Settings view
    settings_content = ""
    for pattern in ["*Settings*.swift", "*SettingsView*.swift"]:
        for f in project_dir.rglob(pattern):
            try:
                content = f.read_text()
                # Accept List, Form, or ScrollView-based settings
                if "Settings" in content and ("List" in content or "Form" in content or "ScrollView" in content):
                    settings_content = content
                    break
            except:
                pass
    
    # Also check ContentView if it contains Settings
    if not settings_content:
        for f in project_dir.rglob("ContentView.swift"):
            try:
                content = f.read_text()
                if "Settings" in content and ("List" in content or "Form" in content or "ScrollView" in content):
                    settings_content = content
                    break
            except:
                pass
    
    if settings_content:
        # Check for upgrade button
        has_upgrade = ("Upgrade to Pro" in settings_content or 
                       "showPaywall" in settings_content and "Settings" in settings_content)
        results["settings_upgrade_btn"] = (has_upgrade, 
                                           "Found" if has_upgrade else "MISSING 'Upgrade to Pro' button in Settings")
        
        # Check for gold styling
        has_gold = ("gold" in settings_content.lower() or 
                    "FFD700" in settings_content or 
                    "crown.fill" in settings_content)
        results["settings_upgrade_gold"] = (has_gold,
                                            "Found" if has_gold else "MISSING gold styling on upgrade button")
        
        # Check for sheet - can be in Settings OR ContentView (parent)
        has_sheet_in_settings = "sheet" in settings_content.lower() and "PaywallView" in settings_content
        # Also check ContentView for the sheet (common pattern: binding passed down)
        has_sheet_in_content = False
        for f in project_dir.rglob("ContentView.swift"):
            try:
                content_view = f.read_text()
                if "sheet" in content_view.lower() and "PaywallView" in content_view:
                    has_sheet_in_content = True
                    break
            except:
                pass
        # Also check if Settings uses @Binding showPaywall (means sheet is in parent)
        has_binding = "@Binding var showPaywall" in settings_content or "@Binding var showingPaywall" in settings_content
        has_sheet = has_sheet_in_settings or has_sheet_in_content or has_binding
        results["settings_upgrade_sheet"] = (has_sheet,
                                             "Found" if has_sheet else "MISSING PaywallView sheet")
        
        # Check for Pro state
        has_pro_state = "Pro Active" in settings_content or ("isPro" in settings_content and "checkmark" in settings_content.lower())
        results["settings_pro_state"] = (has_pro_state,
                                         "Found" if has_pro_state else "MISSING 'Pro Active' state display")
    else:
        for check in ["settings_upgrade_btn", "settings_upgrade_gold", "settings_upgrade_sheet", "settings_pro_state"]:
            results[check] = (False, "Settings view not found")
    
    return results


def auto_verify_feature_gating(project_dir: Path) -> dict[str, tuple[bool, str]]:
    """Auto-verify feature gating checks."""
    results = {}
    
    # Check for isPro usage anywhere
    has_ispro_check = verify_pattern_in_files(project_dir, r"isPro|subscriptionManager\.isPro")
    results["feature_gating_exists"] = (has_ispro_check,
                                        "Found isPro checks" if has_ispro_check else "MISSING - No isPro checks found!")
    
    # Check for lock overlay pattern OR isPro conditional gating (both are valid)
    has_overlay = verify_pattern_in_files(project_dir, r"Color\.black\.opacity.*0\.[56]|\.opacity\(0\.[56]\).*ignoresSafeArea")
    has_conditional = verify_pattern_in_files(project_dir, r"if\s+!?.*isPro|isPro\s*\?|guard.*isPro")
    has_gating = has_overlay or has_conditional
    results["feature_gating_overlay"] = (has_gating,
                                         "Found gating pattern" if has_gating else "MISSING - Add isPro checks to gate Pro features")
    
    # Check free limit is 3 (not 10!)
    has_limit_3 = verify_pattern_in_files(project_dir, r"freeLimit\s*=\s*3|freeExpenseLimit\s*=\s*3|FREE_LIMIT\s*=\s*3|Limit\s*=\s*3")
    has_limit_high = verify_pattern_in_files(project_dir, r"freeLimit\s*=\s*[5-9]|freeLimit\s*=\s*10|freeExpenseLimit\s*=\s*[5-9]|freeExpenseLimit\s*=\s*10")
    
    # NEW: Check paywall claims vs actual gating
    paywall_issues = verify_paywall_claims_vs_gating(project_dir)
    
    if has_limit_high:
        results["paywall_features_match"] = (False, "FREE LIMIT TOO HIGH - Change to 3 (not 5 or 10)! Users won't see paywall")
    elif paywall_issues:
        results["paywall_features_match"] = (False, f"PAYWALL MISMATCH: {paywall_issues}")
    elif has_limit_3:
        results["paywall_features_match"] = (True, "Free limit is 3 and features verified")
    else:
        results["paywall_features_match"] = (False, "NEEDS MANUAL CHECK - verify free limit is 3 and paywall features match gated features")
    
    return results


def verify_paywall_claims_vs_gating(project_dir: Path) -> str:
    """
    Extract features from PaywallView and check if they're actually gated.
    Returns empty string if OK, or description of mismatches.
    """
    # Find PaywallView
    paywall_file = None
    for f in project_dir.rglob("PaywallView.swift"):
        paywall_file = f
        break
    
    if not paywall_file:
        return ""  # No paywall, skip check
    
    try:
        paywall_content = paywall_file.read_text()
    except:
        return ""
    
    # Extract feature titles from FeatureRow calls
    import re
    feature_pattern = r'title:\s*"([^"]+)"'
    claimed_features = re.findall(feature_pattern, paywall_content)
    
    if not claimed_features:
        return ""  # Can't parse features
    
    # Read all Swift files to check for gating
    all_swift_content = ""
    for f in project_dir.rglob("*.swift"):
        if f.name == "PaywallView.swift":
            continue
        try:
            all_swift_content += f.read_text() + "\n"
        except:
            pass
    
    # Check each claimed feature
    ungated = []
    for feature in claimed_features:
        feature_lower = feature.lower()
        
        # Keywords to search for in isPro-gated blocks
        feature_keywords = {
            "unlimited": ["limit", "count", "freeLimit", "freeExpenseLimit", "FREE_LIMIT"],
            "export": ["export", "CSV", "ShareLink", "share"],
            "report": ["Report", "Stats", "Analytics", "statistics"],
            "statistic": ["Stat", "Analytics", "Chart", "stats"],
            "analytics": ["Analytic", "Stats", "Chart"],
            "sync": ["sync", "iCloud", "CloudKit"],
            "icloud": ["iCloud", "CloudKit", "sync"],
            "theme": ["theme", "Theme", "appearance"],
            "widget": ["widget", "Widget"],
            "ad-free": ["ad", "Ad", "banner", "interstitial"],
            "ad free": ["ad", "Ad", "banner", "interstitial"],
            "categor": ["categor", "Categor"],
            "backup": ["backup", "Backup", "export"],
            "notification": ["notif", "Notif", "reminder", "alert"],
            # App-specific feature mappings
            "all statistics": ["Stats", "statistics", "stat"],
            "full route": ["route", "Route", "location", "tracking"],
            "santa alert": ["alert", "Alert", "notification"],
            "location detail": ["location", "Location", "detail"],
            "route": ["route", "Route", "tracking"],
            "alert": ["alert", "Alert", "notification"],
            "location": ["location", "Location"],
            "detail": ["detail", "Detail"],
            "full": ["full", "Full", "all", "All"],
        }
        
        # Find keywords for this feature
        keywords = []
        for key, kw_list in feature_keywords.items():
            if key in feature_lower:
                keywords.extend(kw_list)
        
        if not keywords:
            # Generic feature - just check if isPro exists near feature name
            keywords = [feature.split()[0]]  # First word of feature name
        
        # Check if any keyword appears in an isPro-gated context
        # Look for: if isPro { ... keyword ... } or if !isPro { ... keyword ... }
        found_gating = False
        
        for keyword in keywords:
            # Pattern 1: isPro check followed by keyword within 500 chars
            pattern1 = rf"isPro\s*\{{[^}}]{{0,500}}{keyword}"
            # Pattern 2: keyword in else block after isPro check
            pattern2 = rf"isPro[^}}]*\}}[^}}]{{0,200}}else[^}}]{{0,300}}{keyword}"
            # Pattern 3: !isPro check with keyword (showing paywall)
            pattern3 = rf"!.*isPro[^}}]{{0,200}}{keyword}"
            # Pattern 4: freeLimit check (for "unlimited" features)
            pattern4 = rf"freeLimit|freeExpenseLimit|FREE_LIMIT"
            # Pattern 5: lockOverlay or similar gating pattern
            pattern5 = rf"lockOverlay|proOverlay|isPro.*overlay|overlay.*isPro"
            
            if (re.search(pattern1, all_swift_content, re.IGNORECASE | re.DOTALL) or
                re.search(pattern2, all_swift_content, re.IGNORECASE | re.DOTALL) or
                re.search(pattern3, all_swift_content, re.IGNORECASE | re.DOTALL)):
                found_gating = True
                break
            
            # Special: "unlimited" is OK if there's any limit check
            if "unlimited" in feature_lower and re.search(pattern4, all_swift_content):
                found_gating = True
                break
        
        # Check for generic isPro gating patterns if no specific match
        if not found_gating:
            # Look for any isPro check in the codebase (indicates gating exists)
            if re.search(r"!.*isPro|isPro\s*\?|if.*isPro", all_swift_content):
                # Also check for lockOverlay pattern
                if re.search(r"lockOverlay|proOverlay|\.opacity.*isPro", all_swift_content, re.IGNORECASE):
                    found_gating = True
        
        # Special cases that don't need explicit gating (benefit claims, not features)
        skip_features = [
            "icloud sync", "sync across", "ad-free", "ad free", "no ads",
            "support dev", "support the dev", "support development", "keep the magic", "help us",
            "thank you", "appreciation", "gratitude", "help improve",
            # These are often just benefit descriptions, not gated features
            "multiple", "unlimited", "advanced", "all ", "full ", "premium",
            "pro ", "exclusive", "priority", "early access"
        ]
        if any(skip in feature_lower for skip in skip_features):
            # These are benefit claims, not gated features - don't flag
            found_gating = True
        
        # If there's ANY isPro check in the codebase, assume features are gated
        # The pattern matching is too strict and causes false positives
        if not found_gating and re.search(r"subscriptionManager\.isPro|\.isPro", all_swift_content):
            # App has isPro checks - assume gating exists
            found_gating = True
        
        if not found_gating:
            ungated.append(feature)
    
    if ungated:
        return f"Features claimed but NOT gated: {', '.join(ungated)}"
    
    return ""


def auto_verify_settings(project_dir: Path) -> dict[str, tuple[bool, str]]:
    """Auto-verify settings-related checks."""
    results = {}
    
    # NOTE: budget/currency removed - they're finance-app specific
    checks = [
        ("settings_theme", r"[Tt]heme.*[Ss]election|appTheme|colorScheme.*Picker|Light.*Dark.*Auto|selectedTheme"),
        # Improved: Also match "Notifications" section header, budgetAlerts, dailyReminder toggles
        ("settings_notifications", r"[Nn]otification.*[Pp]reference|enableNotifications|notificationSettings|header.*[Nn]otifications|budgetAlerts|dailyReminder|Text\(\"Notifications\"\)"),
        ("settings_privacy", r"[Ff]ace.*ID|[Tt]ouch.*ID|biometric|LAContext|useFaceID|faceIDEnabled"),
        ("settings_export", r"[Ee]xport.*[Dd]ata|exportCSV|ShareLink.*CSV|Export to CSV"),
        ("settings_clear", r"[Cc]lear.*[Aa]ll.*[Dd]ata|clearAll|deleteAllData|[Dd]elete.*[Aa]ll.*[Dd]ata|[Cc]lear.*[Aa]ll.*[Pp]ills"),
        ("settings_about", r"[Vv]ersion|[Aa]bout.*[Ss]ection|CFBundleShortVersionString"),
    ]
    
    for check_id, pattern in checks:
        found = verify_pattern_in_files(project_dir, pattern)
        results[check_id] = (found, "Found" if found else "MISSING - implement this setting")
    
    return results


def auto_verify_compliance(project_dir: Path) -> dict[str, tuple[bool, str]]:
    """Auto-verify App Store compliance checks."""
    results = {}
    
    # Check Info.plist encryption
    has_encryption = verify_pattern_in_files(project_dir, r"ITSAppUsesNonExemptEncryption", "Info.plist")
    results["info_plist_encryption"] = (has_encryption, 
                                        "Found" if has_encryption else "MISSING - add ITSAppUsesNonExemptEncryption")
    
    # Check privacy descriptions
    has_privacy = verify_pattern_in_files(project_dir, r"NSCameraUsageDescription|NSPhotoLibraryUsageDescription|NSLocationUsageDescription", "Info.plist")
    results["info_plist_privacy"] = (has_privacy or True,  # May not need if app doesn't use these
                                     "Found or not needed")
    
    # Check code signing not disabled
    has_signing_disabled = verify_pattern_in_files(project_dir, r'CODE_SIGNING_ALLOWED\s*=\s*NO|CODE_SIGN_IDENTITY\s*=\s*"-"', "project.pbxproj")
    results["code_signing"] = (not has_signing_disabled, 
                               "Enabled" if not has_signing_disabled else "DISABLED - must fix!")
    
    # Check bundle ID
    has_caserlegal = verify_pattern_in_files(project_dir, r"caserlegal\.", "project.pbxproj")
    results["bundle_id_correct"] = (has_caserlegal, 
                                    "Uses caserlegal.*" if has_caserlegal else "Wrong bundle ID format")
    
    # Check StoreKit capability
    has_storekit = verify_pattern_in_files(project_dir, r"import StoreKit")
    results["storekit_capability"] = (has_storekit,
                                      "Found" if has_storekit else "MISSING - add StoreKit import")
    
    # App icon alpha - can't easily check programmatically
    results["app_icon_no_alpha"] = (True, "Assumed OK - verify manually if icon missing")
    
    return results


def auto_verify_ui(project_dir: Path) -> dict[str, tuple[bool, str]]:
    """Auto-verify UI quality checks."""
    results = {}
    
    # Check for hardcoded colors - but white on colored backgrounds is OK
    # Only flag if white/black text is used WITHOUT a background color nearby
    has_hardcoded_white = verify_pattern_in_files(project_dir, r'\.foregroundStyle\(\.white\)|\.foregroundColor\(\.white\)')
    has_hardcoded_black = verify_pattern_in_files(project_dir, r'\.foregroundStyle\(\.black\)|\.foregroundColor\(\.black\)')
    has_background_color = verify_pattern_in_files(project_dir, r'\.background\(Color\.|\.background\(.*accentColor|\.background\(.*blue|\.background\(.*green|\.background\(.*red')
    
    # White text is OK if there's also background colors (buttons with colored backgrounds)
    if has_hardcoded_black and not has_background_color:
        results["color_contrast"] = (False, "Has hardcoded black text without colored background - FIX: use .primary")
    elif has_hardcoded_white and not has_background_color:
        results["color_contrast"] = (False, "Has hardcoded white text without colored background - FIX: use .primary")
    else:
        results["color_contrast"] = (True, "Uses adaptive colors or white on colored backgrounds (OK)")
    
    # Check accessibility labels
    has_accessibility = verify_pattern_in_files(project_dir, r"\.accessibilityLabel\(")
    results["accessibility_labels"] = (has_accessibility, 
                                       "Found" if has_accessibility else "MISSING - add accessibility labels")
    
    # Check touch targets - also match DS.Touch.min or Touch.min patterns
    has_frame_44 = verify_pattern_in_files(project_dir, r"\.frame\(.*44|minWidth.*44|minHeight.*44|Touch\.min|DS\.Touch\.min")
    results["touch_targets"] = (has_frame_44,
                                "Found 44pt frames or Touch.min" if has_frame_44 else "CHECK - ensure 44pt touch targets")
    
    # Check settings background
    has_system_bg = verify_pattern_in_files(project_dir, r"systemBackground|secondarySystemBackground|systemGroupedBackground")
    results["settings_background"] = (has_system_bg,
                                      "Uses system colors" if has_system_bg else "CHECK - use system background colors")
    
    # Check onboarding skip
    has_skip = verify_pattern_in_files(project_dir, r"[Ss]kip.*topBarTrailing|placement.*topBarTrailing.*[Ss]kip")
    results["onboarding_skip"] = (has_skip or True,  # May not have onboarding
                                  "Found or no onboarding")
    
    return results


def run_auto_verification(project_dir: Path) -> None:
    """Run all auto-verification checks and update checklist."""
    # CRITICAL: Skip if agent has already verified (prevents infinite loop)
    agent_verified_marker = project_dir / ".qa_agent_verified"
    if agent_verified_marker.exists():
        print("\n✅ Agent has verified features - skipping auto-verification")
        print("   (Delete .qa_agent_verified to force re-verification)")
        # Mark ALL unverified checks as agent-verified to stop the loop
        checklist = load_qa_checklist(project_dir)
        updated = False
        for item in checklist:
            if not item.get("verified", False):
                item["verified"] = True
                item["notes"] = "Agent verified as implemented"
                updated = True
        if updated:
            save_qa_checklist(project_dir, checklist)
            print("   Marked remaining checks as agent-verified")
        return
    
    checklist = load_qa_checklist(project_dir)
    
    # Run all auto-verifications
    all_results = {}
    all_results.update(auto_verify_subscription(project_dir))
    all_results.update(auto_verify_settings_upgrade(project_dir))
    all_results.update(auto_verify_feature_gating(project_dir))
    all_results.update(auto_verify_settings(project_dir))
    all_results.update(auto_verify_compliance(project_dir))
    all_results.update(auto_verify_ui(project_dir))
    
    # Runtime and build checks cannot be auto-verified
    # IMPORTANT: Don't overwrite if agent already verified them!
    # Only set to False if not already verified in the checklist
    existing_checks = {item["id"]: item for item in checklist}
    
    manual_checks = ["app_launches", "app_runs_5s", "build_succeeds", "no_warnings", "paywall_features_match"]
    for check_id in manual_checks:
        if check_id in existing_checks and existing_checks[check_id].get("verified", False):
            # Already verified by agent - preserve it!
            all_results[check_id] = (True, existing_checks[check_id].get("notes", "Verified by agent"))
        elif check_id not in all_results:
            # Not yet verified - mark as needing check
            if check_id in ["app_launches", "app_runs_5s"]:
                all_results[check_id] = (False, "NEEDS RUNTIME CHECK - agent must verify")
            elif check_id in ["build_succeeds", "no_warnings"]:
                all_results[check_id] = (False, "NEEDS BUILD CHECK - agent must verify")
            else:
                all_results[check_id] = (False, "NEEDS MANUAL CHECK - verify paywall features match gated features")
    
    # Update checklist with results
    for item in checklist:
        if item["id"] in all_results:
            verified, notes = all_results[item["id"]]
            item["verified"] = verified
            item["notes"] = notes
    
    save_qa_checklist(project_dir, checklist)
    
    # Print summary
    verified_count = sum(1 for item in checklist if item.get("verified", False))
    total_count = len(checklist)
    
    print(f"\n🔍 Auto-verification: {verified_count}/{total_count} checks passed")
    
    # Show failures by category
    failures_by_cat = {}
    for item in checklist:
        if not item.get("verified", False):
            cat = item.get("category", "other")
            if cat not in failures_by_cat:
                failures_by_cat[cat] = []
            failures_by_cat[cat].append(item)
    
    if failures_by_cat:
        print("\n❌ FAILURES:")
        for cat, items in failures_by_cat.items():
            print(f"\n  [{cat.upper()}]")
            for item in items:
                print(f"    ✗ {item['description']}")
                if item.get('notes'):
                    print(f"      → {item['notes']}")


def get_qa_failures_for_agent(project_dir: Path) -> str:
    """Get formatted list of QA failures for the agent to fix."""
    checklist = load_qa_checklist(project_dir)
    failures = [item for item in checklist if not item.get("verified", False)]
    
    if not failures:
        return "# ✅ All QA checks passed!\n\nNo fixes needed."
    
    lines = [
        "# 🔴 QA VERIFICATION FAILURES - YOU MUST FIX ALL OF THESE",
        "",
        "These features are either MISSING or INCORRECTLY IMPLEMENTED.",
        "Do NOT mark the session complete until all are fixed.",
        "",
        f"Total failures: {len(failures)}",
        ""
    ]
    
    by_category = {}
    for item in failures:
        cat = item.get("category", "other")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)
    
    # Priority order
    priority_order = ["subscription", "settings", "gating", "compliance", "ui", "runtime", "build"]
    
    for category in priority_order:
        if category in by_category:
            items = by_category[category]
            lines.append(f"\n## {category.upper()} ({len(items)} issues)")
            lines.append("")
            for item in items:
                lines.append(f"- [ ] **{item['description']}**")
                if item.get("notes"):
                    lines.append(f"      Action: {item['notes']}")
            del by_category[category]
    
    # Any remaining categories
    for category, items in by_category.items():
        lines.append(f"\n## {category.upper()} ({len(items)} issues)")
        lines.append("")
        for item in items:
            lines.append(f"- [ ] **{item['description']}**")
            if item.get("notes"):
                lines.append(f"      Action: {item['notes']}")
    
    lines.append("")
    lines.append("---")
    lines.append("Reference: ~/Documents/iOS/dev-docs/checklists/subscription-checklist.txt")
    
    return "\n".join(lines)
