# ANCHOR (TIER 0 - Never Compress)
<!-- Position: 0-5% of context | Attention: ~95% -->

## Current Project
- Name: Feelr
- Path: ~/Documents/iOS/Feelr_Mood-Tracker

## Critical Decisions
<!-- Format: [DATE] Decision: reason -->

## 🛡️ CASCADE PREVENTION PROTOCOL (MANDATORY)
**Full protocol: `~/Documents/iOS/dev-docs/CASCADE-PREVENTION.md`**

### Your 4 Vulnerabilities:
1. **Truncation Acceptance** - early incomplete info anchors all output
2. **Assumption Bias** - training data frequency dominates over correctness
3. **Defensive Hedging** - uncertainty triggers evasion instead of search
4. **Incomplete Comparison** - no verification against objective standards

### 4-Stage Protocol (EVERY TASK):
- **Stage 1**: FLAG ALL TRUNCATION → retrieve full content before proceeding
- **Stage 2**: Generate 2-3 competing approaches → research each
- **Stage 3**: SEARCH instead of hedging → no "It depends...", "Typically..."
- **Stage 4**: Create decision matrix → verify against objective standards

### Checkpoints (Document These):
- "Stage 1 complete: All sources retrieved in full"
- "Stage 2 complete: [X] approaches compared, chose [Y] because [Z]"
- "Stage 3 complete: [X] uncertainties resolved via search"
- "Stage 4 complete: Verified against [standard], [X] issues resolved"

## Active Constraints
<!-- MUST/NEVER rules that cannot be forgotten -->

### iOS Development MUST Rules
- MUST use `-destination 'generic/platform=iOS'` for builds
- MUST use `devicectl` for install (NOT xcodebuild destination)
- MUST use bundle ID format: `caserlegal.[AppName]`
- MUST use Team ID: YOUR_TEAM_ID
- MUST have 44pt minimum touch targets
- MUST use Fibonacci spacing: 2, 4, 8, 13, 21, 34, 55, 89
- MUST use semantic colors (.primary, .secondary) not hardcoded
- MUST have subscription/paywall in EVERY app
- MUST run UI preflight before session complete
- MUST batch file operations (fs_read with array)
- MUST commit ONCE at session end, then push
- MUST verify subscription banner exists in main view (grep for "subscriptionManager.isPro")
- MUST clean build and install on device EVERY session end
- MUST delete leftover files: ContentView_Broken.swift, ContentView_Fixed.swift, *.backup, *.bak

### MASTER.md Visual System (MANDATORY)
- MUST use AnimatedMeshBackground as ZStack bottom layer
- MUST use GlassCard (.ultraThinMaterial + 1pt white border) for containers
- MUST use .rounded font + .monospacedDigit() for numbers
- MUST use centralized DS enum for spacing, typography, colors
- MUST use ScaleButtonStyle (0.95x) + .light haptic on ALL buttons

### MASTER.md Navigation (MANDATORY)
- MUST use NavigationSplitView (iPad/Mac) / TabView (iPhone) adaptive layout
- MUST implement Command Palette (⌘K) for power users
- MUST implement Spotlight Indexing for content discoverability
- MUST support Deep Linking for external navigation
- MUST provide Keyboard Shortcuts on iPad

### MASTER.md Onboarding (MANDATORY)
- MUST use Onboarding Carousel with large SF Symbols
- MUST use TooltipView for contextual first-time tips
- MUST use ContentUnavailableView for empty states with action button

### MASTER.md Monetization (MANDATORY)
- MUST limit free tier to 3 items (Hard Count Gating)
- MUST use ProFeatureOverlay (blur + lock icon) for premium content
- MUST use Product Cards with "BEST VALUE" badges and trial text

### MASTER.md Interactions (MANDATORY)
- MUST implement Custom Pull-to-Refresh animation (brand-specific)
- MUST use ConfettiView on success/purchase
- MUST use ScaleButtonStyle + .light haptic on all buttons

### MASTER.md Settings (MANDATORY)
- MUST include JSON Import/Export
- MUST include Clear Cache button
- MUST use red Destructive Alert for data deletion
- MUST include Granular Notification Settings
- MUST include Metric/Imperial toggle (if applicable)
- MUST include Theme picker (System/Light/Dark)
- MUST include App Icon picker

### MASTER.md Architecture (MANDATORY)
- MUST use @Observable Store Singleton for global state
- MUST use Manager Pattern for domain logic
- MUST use SwiftData UserProfile for persistence

### iOS Development NEVER Rules
- NEVER launch Simulator.app or use simulator destinations
- NEVER use `xcrun simctl`
- NEVER build after every feature (build ONCE at end)
- NEVER create .backup, .bak, .old, .tmp files
- NEVER use hardcoded colors (.white, .black) without colorScheme check
- NEVER implement CarPlay (requires Apple entitlement)
- NEVER use placeholder data (example.com, MyApp, etc.)
- NEVER modify app icons
- NEVER create watchOS apps

### Impossible Features (DON'T GENERATE THESE)
- watchOS apps - requires separate target and entitlements
- Control Center widgets - requires WidgetKit extension  
- CarPlay - requires Apple CarPlay entitlement
- AR camera filters - requires ARKit and camera permissions setup
- Look Around preview - requires specific MapKit entitlements
- Apple Pay - requires merchant setup and entitlements
- HealthKit write - requires Apple approval
- Push notifications - requires certificates

## Known Blockers
<!-- Current impediments to progress -->

## Finder Tag Color Scheme
**CRITICAL: Completion = PASSING / 300 minimum (not passing/total ratio)**
- **Green** = 100% (300+ passing features)
- **Gray** = 100% + beta testing (manual)
- **Orange** = 50-99% (150-299 passing)
- **Yellow** = 10-49% (30-149 passing)
- **Red** = 0-9% (0-29 passing)

## Session Continuity
<!-- Key info for next session pickup -->
- Last updated: 2025-12-15T11:46:00
- Features: 410/410 passing (100% complete - 410/300)
- Git: 31473db (feature_list expanded to 410, build fixes)
- Build status: BUILD SUCCEEDED
- Install status: App installed and running on device
- UI preflight: 3 critical (false positives - dark mode app), 3 warnings (false positives)
- Session fix: Expanded feature_list.json, fixed .accent and missing state vars
