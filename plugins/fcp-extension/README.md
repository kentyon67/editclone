# EditClone — Final Cut Pro Workflow Extension

A native macOS Workflow Extension (Swift/SwiftUI + WKWebView) that embeds the EditClone
web app directly inside Final Cut Pro. Upload videos, trigger AI edits, and import the
resulting FCPXML — without leaving FCP.

Distributed via the Mac App Store. Apple review takes approximately 1-3 months.

---

## Requirements

| Requirement | Minimum |
|-------------|---------|
| macOS | 13 (Ventura) |
| Xcode | 15 |
| Final Cut Pro | 10.6 |
| Apple Developer Program | Recommended ($99/year); personal team works for local testing |

---

## Project Structure

```
plugins/fcp-extension/
  EditClone/
    EditCloneApp.swift        — App entry point
    ContentView.swift         — Root SwiftUI view
    EditCloneWebView.swift    — WKWebView wrapper with JS bridge
    Info.plist                — Bundle configuration
  EditClone.entitlements      — Network + Workflow Extension entitlements
```

---

## Build and Run (Local Testing)

### 1. Create the Xcode Project

1. Open Xcode.
2. **File > New > Project**.
3. Choose **macOS > App**.
4. Fill in:
   - Product Name: `EditClone`
   - Bundle Identifier: `com.editclone.fcp-extension`
   - Language: **Swift**
   - Interface: **SwiftUI**
5. Choose a location and click Create.

### 2. Add Source Files

Replace the auto-generated files with those from `plugins/fcp-extension/EditClone/`:

- `EditCloneApp.swift`
- `ContentView.swift`
- `EditCloneWebView.swift`

In Xcode's project navigator, delete `ContentView.swift` that Xcode created, then
drag the three files above into the project.

### 3. Configure Info.plist

In Xcode, select the `EditClone` target > **Info** tab. Add the following keys
(or paste the contents of `Info.plist` directly):

| Key | Value |
|-----|-------|
| `NSPrincipalClass` | `NSApplication` |
| `FCP Workflow Extension` | Dictionary with bundle ID `com.editclone.fcp-extension` |

### 4. Set Up Signing

1. Select the project in the navigator.
2. Go to **Signing & Capabilities**.
3. Set **Team** to your Apple Developer account (personal team is fine for local testing).
4. Confirm **Bundle Identifier** is `com.editclone.fcp-extension`.

### 5. Add Capabilities

In **Signing & Capabilities**, click **+ Capability** and add:

- **Network** (outgoing connections to the EditClone backend)
- **Workflow Extension** — searches for `com.apple.developer.workflow-extension-api`

If the Workflow Extension capability is not listed, add it manually by editing
`EditClone.entitlements` (already present in the repo).

### 6. Run

Press **Cmd+R** or click the Run button. Xcode builds the app and launches it.
Final Cut Pro should open automatically and register the extension.

In FCP, go to **Window > Extensions > EditClone**.

---

## Change the API URL

By default, `EditCloneWebView.swift` (or `ContentView.swift`) points to the production URL.
Search for `baseURL` and update if needed:

```swift
private let baseURL = "https://editclone.vercel.app"
```

For local development, point to your local Next.js server:

```swift
private let baseURL = "http://localhost:3000"
```

---

## Distribution via Mac App Store

1. In Xcode, go to **Product > Archive**.
2. In the Organizer, click **Validate App** to check for issues.
3. Click **Distribute App > App Store Connect**.
4. In App Store Connect (https://appstoreconnect.apple.com):
   - Create a new app with Bundle ID `com.editclone.fcp-extension`.
   - Category: **Productivity**.
   - Add screenshots (1280x800 or 1440x900) showing FCP with the extension open.
5. Submit for review.

Apple's review team typically takes 1–3 months for Workflow Extensions.

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| Extension not in Window > Extensions | Confirm the app ran successfully in Xcode; check Console.app for errors |
| WebView shows blank page | Verify outbound network entitlement; check that `baseURL` is reachable |
| "Workflow Extension capability not found" | Manually add the key to `EditClone.entitlements`; see Apple docs for the exact entitlement string |
| Build fails on `WKWebView` import | Ensure the target is macOS (not iOS); WebKit is macOS-only in this project |
| Personal team code signing error | Go to Signing & Capabilities, check "Automatically manage signing", pick your personal team |
