# EditClone — Plugin Quick Start

EditClone has four plugins that connect your NLE directly to the EditClone AI backend.
Each plugin lets you trigger AI edits, import results, and sync your editing style — without leaving your NLE.

| Plugin | NLE | Language | Distribution |
|--------|-----|----------|-------------|
| [DaVinci Script](#davinci-resolve-script) | DaVinci Resolve 18+ | Python | Direct (no review) |
| [FCP Extension](#final-cut-pro-workflow-extension) | Final Cut Pro 10.6+ | Swift/SwiftUI | Mac App Store (1-3 months review) |
| [Premiere CEP Panel](#premiere-pro-cep-panel) | Premiere Pro CC 2019+ | HTML/JS | Adobe Exchange (2-4 weeks review) |
| [Premiere UXP Panel](#premiere-pro-uxp-panel) | Premiere Pro 2022+ | HTML/JS | Adobe Exchange (2-4 weeks review) |

---

## API Setup (all plugins)

All plugins connect to the same backend.

| Setting | Value |
|---------|-------|
| API URL | `https://editclone-production.up.railway.app` |
| Token | Generate at https://editclone.vercel.app/ja/account under "API Keys" |

Token format: `eck_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## DaVinci Resolve Script

A Python script that runs inside DaVinci Resolve's scripting engine. No App Store review required.

**Full guide:** [davinci-script/README.md](davinci-script/README.md)

### Quick Start (macOS)

```bash
cd plugins/davinci-script
bash install.sh
```

### Quick Start (Windows)

```
cd plugins\davinci-script
install.bat
```

### Test without DaVinci

```bash
python plugins/davinci-script/test_connection.py
```

---

## Final Cut Pro Workflow Extension

A native macOS app (Swift/SwiftUI + WKWebView) that appears as a workflow extension inside Final Cut Pro.

**Full guide:** [fcp-extension/README.md](fcp-extension/README.md)

### Quick Start

1. Open `plugins/fcp-extension/` in Xcode
2. Set your Team in Signing & Capabilities
3. Press Run (Cmd+R) — Final Cut Pro opens with the extension loaded
4. Go to Window > Extensions > EditClone

---

## Premiere Pro CEP Panel

An HTML/JS panel for Premiere Pro using Adobe's CEP (Common Extensibility Platform) framework.
Works with Premiere Pro CC 2019 through Premiere Pro 2025.

**Full guide:** [premiere-cep/README.md](premiere-cep/README.md)

### Quick Start (macOS)

```bash
cd plugins/premiere-cep
bash debug-enable.sh   # run once to allow unsigned extensions
bash install.sh
```

### Quick Start (Windows)

```
cd plugins\premiere-cep
debug-enable.bat        # run once to allow unsigned extensions
install.bat
```

Then restart Premiere Pro and go to **Window > Extensions > EditClone**.

---

## Premiere Pro UXP Panel

A modern HTML/JS panel using Adobe's UXP framework. Requires Premiere Pro 2022 (v22.0) or later
and the free [UXP Developer Tools](https://exchange.adobe.com/apps/cc/106532/uxp-developer-tools).

**Full guide:** [premiere/README.md](premiere/README.md)

### Quick Start (macOS)

```bash
cd plugins/premiere
bash install.sh
```

Then load the plugin via UXP Developer Tools (see guide).

---

## Troubleshooting

### General

| Problem | Solution |
|---------|---------|
| "Cannot connect to API" | Check that https://editclone-production.up.railway.app/health returns `{"status":"ok"}` |
| "Unauthorized" (401) | Regenerate your API token at https://editclone.vercel.app/ja/account |
| "Forbidden" (403) | Plugin access requires Creator or Studio plan |

### DaVinci Script

| Problem | Solution |
|---------|---------|
| Script not in menu | Check install path; restart DaVinci after copying |
| "DaVinci 未接続" | Run the script from inside DaVinci (Workspace > Scripts), not from a terminal |
| Python not found | DaVinci bundles Python — run from the Scripts menu, not externally |

### Premiere CEP

| Problem | Solution |
|---------|---------|
| Extension not in Window > Extensions | Run `debug-enable` scripts again; verify Premiere version >= CC 2019 |
| Panel shows blank | Open Chrome DevTools at http://localhost:7777 to see JS errors |
| "PlayerDebugMode" not working | Some Premiere versions use CSXS.10 or .11 — the installer sets all versions 9-12 |

### FCP Extension

| Problem | Solution |
|---------|---------|
| Extension not in Window > Extensions | Make sure you're running the app from Xcode with a valid signing identity |
| WebView blank | Check network entitlements in EditClone.entitlements |

### Premiere UXP

| Problem | Solution |
|---------|---------|
| Plugin not loading | Re-add via UXP Developer Tools > Add Plugin > select manifest.json |
| "premierePro" module not found | UXP plugins must run inside Premiere, not a browser |
