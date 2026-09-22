# PROCEDURAL (TIER 2 - Expendable)
<!-- Position: 15-40% of context (Dead Zone) | Attention: ~60% -->
<!-- This content can be regenerated - compress aggressively -->

## CRITICAL: File Editing Rules

### NEVER USE SED FOR MULTI-LINE EDITS
**This causes catastrophic data loss 90% of the time.**

❌ FORBIDDEN:
```bash
# NEVER do this - line numbers shift, special chars break, files get corrupted
sed -i '' '10i\import Foundation\nimport SwiftUI' file.swift
sed -i '' 's/old/new/g' file.swift  # for multi-line replacements
```

✅ REQUIRED: Use proper file tools instead:
- `file_write` / `fs_write` with `str_replace` for targeted edits
- `file_write` / `fs_write` with `create` to rewrite entire file when needed
- Read file first, modify in memory, write back complete file

**Why sed fails:**
1. Line numbers shift as you insert/delete - subsequent edits hit wrong lines
2. Special chars (`/`, `&`, `\n`, quotes) break regex silently
3. One wrong line number = entire file corrupted or truncated
4. No atomic operations - partial failures leave broken state

**Rule: If editing >3 lines or adding imports, ALWAYS use file tools, NEVER sed.**

## Build Commands
```bash
# Build for device
xcodebuild -project *.xcodeproj -scheme * -destination 'generic/platform=iOS' -configuration Release build 2>&1 | tail -30

# Find app and install
APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData -name "*.app" -path "*/Release-iphoneos/*" -type d 2>/dev/null | head -1)
DEVICE_ID=$(xcrun devicectl list devices 2>/dev/null | grep -E "iPhone|iPad" | head -1 | awk '{for(i=1;i<=NF;i++) if($i ~ /^[A-F0-9]{8}-/) print $i}')
xcrun devicectl device install app --device "$DEVICE_ID" "$APP_PATH"

# Check completion
grep -c '"passes": false' feature_list.json
```

## Code Patterns

### Touch Target Pattern
```swift
Button { } label: { Image(systemName: "plus") }
    .frame(minWidth: 44, minHeight: 44)
    .contentShape(Rectangle())
```

### Adaptive Colors Pattern
```swift
@Environment(\.colorScheme) var colorScheme
Text("Title").foregroundStyle(colorScheme == .dark ? .white : .primary)
.listRowBackground(Color(.systemBackground))
```

### Subscription Banner Pattern
```swift
if !subscriptionManager.isPro {
    Button { showPaywall = true } label: {
        HStack(spacing: 13) {
            Image(systemName: "crown.fill").foregroundStyle(DS.Colors.gold)
            VStack(alignment: .leading) {
                Text("Upgrade to Pro").font(.headline)
                Text("Unlock all features").font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            Image(systemName: "chevron.right").foregroundStyle(.secondary)
        }
        .padding()
        .background(DS.Colors.gold.opacity(0.15), in: RoundedRectangle(cornerRadius: 13))
    }
}
```

### SubscriptionManager IAP Pattern (CRITICAL)
```swift
@MainActor
final class SubscriptionManager: ObservableObject {
    static let shared = SubscriptionManager()
    
    @Published private(set) var purchasedProductIDs: Set<String> = []
    @Published private(set) var headElfProduct: Product?
    
    // CRITICAL: Use SHORT IDs - NOT "caserlegal.AppName.00001"
    struct IAPProducts {
        static let headElf = "00001"      // Non-consumable
        static let tip099 = "tip_099"     // Consumable
        static let all = [headElf, tip099]
    }
    
    // Subscription uses FULL prefix
    private let productIDs = ["caserlegal.AppName.monthly"]
    
    private init() {
        Task {
            await updatePurchasedProducts()
            await loadIAPProducts()
        }
    }
    
    func loadIAPProducts() async {
        let products = try? await Product.products(for: IAPProducts.all)
        for product in products ?? [] {
            if product.id == IAPProducts.headElf { headElfProduct = product }
        }
    }
    
    func purchase(_ product: Product) async -> Bool {
        let result = try? await product.purchase()
        if case .success(let verification) = result,
           case .verified(let transaction) = verification {
            purchasedProductIDs.insert(transaction.productID)
            await transaction.finish()
            return true
        }
        return false
    }
}
```

### Onboarding Page Buttons (avoid overlap)
```swift
TabView { pages }
    .tabViewStyle(.page(indexDisplayMode: .always))
    .safeAreaInset(edge: .bottom) {
        Button("Next") { }
            .padding(.horizontal, 34)
            .padding(.bottom, 34)
    }
```

### GlassCard Pattern (MASTER.md)
```swift
struct GlassCard<Content: View>: View {
    let content: Content
    init(@ViewBuilder content: () -> Content) { self.content = content() }
    var body: some View {
        content
            .background(.ultraThinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 13))
            .overlay(RoundedRectangle(cornerRadius: 13).stroke(.white.opacity(0.2), lineWidth: 1))
    }
}
```

### ScaleButtonStyle Pattern (MASTER.md)
```swift
struct ScaleButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.easeInOut(duration: 0.15), value: configuration.isPressed)
            .onChange(of: configuration.isPressed) { _, pressed in
                if pressed { UIImpactFeedbackGenerator(style: .light).impactOccurred() }
            }
    }
}
```

### AnimatedMeshBackground Pattern (MASTER.md)
```swift
struct AnimatedMeshBackground: View {
    @State private var phase: CGFloat = 0
    var body: some View {
        TimelineView(.animation) { timeline in
            MeshGradient(width: 3, height: 3, points: [...], colors: [...])
        }
        .ignoresSafeArea()
    }
}
```

### Command Palette Pattern (MASTER.md)
```swift
.keyboardShortcut("k", modifiers: .command)
.sheet(isPresented: $showCommandPalette) { CommandPaletteView() }
```

### ConfettiView Pattern (MASTER.md)
```swift
struct ConfettiView: View {
    @Binding var isActive: Bool
    // Particle system for celebration on success/purchase
}
```

## Resolved Issues
<!-- Cleared on compression - these are solved -->
