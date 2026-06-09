# EditClone — Premiere Pro UXP Panel

A modern Premiere Pro panel built on Adobe's UXP (Unified Extensibility Platform) framework.
Supports job browsing, AI agent editing, Premiere XML import, SRT download, and Style Profile
management — all from inside Premiere.

Requires Premiere Pro 2022 (v22.0) or later. Older Premiere versions should use the CEP panel.

---

## Requirements

| Requirement | Minimum |
|-------------|---------|
| Premiere Pro | 2022 (v22.0) |
| OS | macOS 12+ or Windows 10+ |
| UXP Developer Tools | Free — see install link below |

---

## Project Structure

```
plugins/premiere/
  manifest.json        — UXP plugin manifest (ID, host app, entrypoint, permissions)
  src/
    index.html         — Panel HTML
    main.js            — Panel logic (UXP APIs, fetch, storage, Premiere Pro integration)
    styles.css         — Panel styles
  install.sh           — macOS helper (copies files + prints instructions)
```

---

## Install UXP Developer Tools

UXP Developer Tools is a free utility from Adobe that lets you load, debug, and manage
UXP plugins without going through the Exchange review process.

Download: https://exchange.adobe.com/apps/cc/106532/uxp-developer-tools

---

## Load the Plugin (macOS)

### Option A — Using the install script

```bash
bash plugins/premiere/install.sh
```

The script copies the plugin files and prints step-by-step instructions.

### Option B — Manual via UXP Developer Tools

1. Open **UXP Developer Tools**.
2. Click **Add Plugin**.
3. Navigate to `plugins/premiere/` and select `manifest.json`.
4. Click **Load** in the plugin list.
5. In Premiere Pro, go to **Window > Extensions (Legacy) > EditClone** (or the UXP panel dock).

### Make Loading Persistent

By default, loaded plugins are lost when Premiere restarts.
To auto-load on every Premiere launch:

1. In UXP Developer Tools, click the `...` menu beside the EditClone entry.
2. Choose **Auto-load on launch**.

---

## Debugging

UXP Developer Tools includes a built-in DevTools panel:

1. In UXP Developer Tools, click the `...` menu beside EditClone.
2. Choose **Debug** — Chromium DevTools opens.
3. The **Console** tab shows JavaScript errors and `console.log` output.
4. Use the **Network** tab to inspect API calls to the backend.

---

## Configuration

The plugin connects to hardcoded URLs at the top of `src/main.js`:

```javascript
const API_BASE = "https://editclone-production.up.railway.app";
const WEB_BASE = "https://editclone.vercel.app";
```

For local backend development, change `API_BASE` to:
```javascript
const API_BASE = "http://localhost:8000";
```

---

## Authentication

The plugin uses email/password login (not API key). Your JWT is stored in `localStorage`
inside the UXP sandbox and persists across Premiere sessions.

To log out, click the logout button in the panel or clear UXP storage via DevTools:
```javascript
localStorage.removeItem("ec_token");
```

---

## Permissions

`manifest.json` declares:

```json
"requiredPermissions": {
  "localFileSystem": "fullAccess",
  "network": {
    "domains": [
      "https://editclone.vercel.app",
      "https://editclone-production.up.railway.app"
    ]
  },
  "ipc": {
    "enablePluginCommunication": true
  }
}
```

If you change the API or web URL, add the new domain here.

---

## Packaging for Adobe Exchange

1. Zip the `plugins/premiere/` directory (including `manifest.json` at the root of the zip).
2. Submit via [Adobe Developer Console](https://developer.adobe.com/developer-console/).
   - Select **UXP** as the plugin type.
   - Select **Premiere Pro** as the target host.
3. Review takes approximately 2–4 weeks.

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| Plugin not in Premiere after loading | Click Reload in UXP Developer Tools; restart Premiere |
| "premierePro module not found" | The plugin must run inside Premiere Pro (not a browser or Node.js) |
| Network request blocked | Verify the domain is listed in `requiredPermissions.network.domains` in manifest.json |
| Login fails | Check backend health at https://editclone-production.up.railway.app/health |
| Import hangs at "ファイルを保存中" | UXP storage quota exceeded; clear temp files or reinstall the plugin |
| Panel not visible in Premiere UI | Try Window > Workspaces > Reset to Saved Layout |
