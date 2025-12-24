Developer: # Task: Upload New Apps to TestFlight – End-to-End Setup

## ⚠️ Critical Workflow
- Start with code. Build once at the end and resolve all issues—address every warning, error, note, or deprecated/unused item.

### Per-App Upload Steps
1. **Register Bundle ID in Xcode:**
   ```bash
   open -a Xcode [AppFolder]/*.xcodeproj
   ```
   - Wait ~5 seconds; close Xcode (auto-registers with `-allowProvisioningUpdates`).

2. **Upload the App:**
   ```bash
   cd /Users/home/Documents/iOS && ./asc upload [AppFolder]
   ```
   - Runs build, archive, IPA export, TestFlight and metadata upload, subscription creation, and adds adam.j.doherty@icloud.com as tester.

3. **Check Upload Status:**
   ```bash
   ./asc status
   ./asc builds
   ```

**Apps to upload:**
- [List apps, e.g. Binday, Blackjack-Pro, Bloom, Breadcrumbs, Breathe]

---

### Troubleshooting
- If you receive "No profiles found":
  - `-allowProvisioningUpdates` should resolve it.
  - If not: open Xcode, click Register, close, retry.
- Always build for a physical device:
  -destination 'generic/platform=iOS'

---

## Metadata Format (Required)
Each `app_store_submission.txt` must use this template:

```
Name (max 30):
AppName

Subtitle (max 30):
Short Tagline

PROMOTIONAL TEXT (140 max)
----------------------------------------
Brief promotional text here.

DESCRIPTION (4000 max)
----------------------------------------
Full app description here.

FEATURES:
• Feature 1
• Feature 2
• Feature 3

Final sentence here!

EULA: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
Terms & Privacy: https://apple.caserlegal.com/#privacy

KEYWORDS (100 max)
----------------------------------------
keyword1,keyword2,keyword3

SUPPORT URL
----------------------------------------
https://apple.caserlegal.com/#privacy

MARKETING URL (App Store Connect "Marketing URL" field)
----------------------------------------
https://apple.caserlegal.com

PRIVACY POLICY URL
----------------------------------------
https://apple.caserlegal.com/#privacy

VERSION
----------------------------------------
1.0.0

COPYRIGHT
----------------------------------------
© 2025 Adam Doherty - All Rights Reserved.
```

### Metadata Rules
1. EULA/Privacy links must be at the end of DESCRIPTION, with a blank line before.
2. Copyright: "© 2025 Adam Doherty - All Rights Reserved."
3. No `<` or `>` in description.
4. Always use provided EULA and privacy links.

---

## asc.sh – Fully Automated Steps
`./asc upload [App]` now:
- Builds & archives (with -allowProvisioningUpdates)
- Exports IPA
- Uploads to TestFlight
- Uploads metadata
- Creates subscriptions (weekly & monthly)
- Adds tester (adam.j.doherty@icloud.com)

---

## Useful Shell Commands

```bash
# Existing apps (profiles registered)
./asc upload [AppFolder]

# New apps (register first)
open -a Xcode [AppFolder]/*.xcodeproj # Register profile, close Xcode
./asc upload [AppFolder]

# Batch upload:
for app in Binday Blackjack-Pro Bloom; do
  ./asc upload "$app"
done
```

---

## Complete Agent Prompt

**New apps to upload:**
- Binday, Blackjack-Pro, Bloom, Breadcrumbs, Breathe

For each app:
```bash
cd /Users/home/Documents/iOS && ./asc upload [AppName]
```
Handles: build, upload, metadata, subscriptions, tester addition.

If "No profiles found" appears:
```bash
open -a Xcode [AppName]/*.xcodeproj
```
Wait for registration, close, retry upload.

After upload:
```bash
./asc status
./asc builds
```

**Never use simulator. Always use:**
```bash
-destination 'generic/platform=iOS'
```

Reference: `/Users/home/Documents/iOS/dev-docs/app-store-connect/README.md`

---

## Metadata/Tester Delays
Apple may take 5–15 minutes to process a new build—this is normal. The script may try to upload metadata/add testers before this finishes.

**Resolution:**
- Wait 10–15 minutes, then run:
  ```bash
  ./asc metadata-all
  ./asc testers
  ./asc status
  ```

---

## Updated New-App Workflow
1. Upload all new apps:
   ```bash
   for app in Binday Blackjack-Pro Bloom Breadcrumbs Breathe; do
     ./asc upload "$app"
   done
   ```
2. Wait 5 minutes for Apple processing.
3. Finalize:
   ```bash
   ./asc metadata-all
   ./asc testers
   ./asc status
   ```

---

## Bulk Metadata Update
Update all metadata files for EULA/Privacy/Copyright:
```bash
cd /Users/home/Documents/iOS && python3 dev-docs/update_submissions.py
```
Sync to App Store Connect:
```bash
./asc metadata-all
```
