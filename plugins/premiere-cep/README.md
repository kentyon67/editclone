# EditClone — Premiere Pro CEP Panel

An HTML/JS panel for Premiere Pro using Adobe's CEP (Common Extensibility Platform) framework.
The panel embeds the EditClone web app, lets you trigger AI edits, and imports Premiere XML
directly into the active project.

Compatible with Premiere Pro CC 2019 (v13.0) through Premiere Pro 2025.
Distribute via Adobe Exchange (2–4 weeks review) or install locally for testing.

---

## Requirements

| Requirement | Minimum |
|-------------|---------|
| Premiere Pro | CC 2019 (v13.0 / CEP 9) |
| OS | macOS 12+ or Windows 10+ |
| Browser engine | CEP ships with a Chromium-based engine — no separate install needed |

---

## Project Structure

```
plugins/premiere-cep/
  CSXS/
    manifest.xml         — Extension metadata (ID, host app, version ranges)
  host/
    host.jsx             — ExtendScript (runs in Premiere's scripting engine)
  CSInterface.js         — Adobe CEP JavaScript bridge (bundled)
  index.html             — Panel entry point
  main.js                — Panel logic
  style.css              — Panel styles
  install.sh             — macOS installer
  install.bat            — Windows installer
  debug-enable.sh        — macOS: enable unsigned extension loading
  debug-enable.bat       — Windows: enable unsigned extension loading
```

---

## Local Installation

### Step 1 — Enable unsigned extension loading (run once)

Premiere Pro blocks unsigned extensions by default. These scripts set the `PlayerDebugMode`
registry/plist key that allows locally installed extensions.

**macOS:**
```bash
bash plugins/premiere-cep/debug-enable.sh
```

**Windows:**
```
plugins\premiere-cep\debug-enable.bat
```

Verify on macOS:
```bash
defaults read com.adobe.CSXS.11 PlayerDebugMode
# Expected output: 1
```

Verify on Windows:
```
reg query "HKCU\Software\Adobe\CSXS.11" /v PlayerDebugMode
# Expected: ... REG_SZ    1
```

### Step 2 — Install the extension

**macOS:**
```bash
bash plugins/premiere-cep/install.sh
```

**Windows:**
```
plugins\premiere-cep\install.bat
```

The installer copies all files to:
- macOS: `~/Library/Application Support/Adobe/CEP/extensions/com.editclone.premiere/`
- Windows: `%APPDATA%\Adobe\CEP\extensions\com.editclone.premiere\`

### Step 3 — Restart Premiere Pro

Quit and reopen Premiere Pro. Go to **Window > Extensions > EditClone**.

---

## Manual Installation

If you prefer to install manually:

1. Copy the entire `premiere-cep/` folder to:
   - macOS: `~/Library/Application Support/Adobe/CEP/extensions/com.editclone.premiere/`
   - Windows: `%APPDATA%\Adobe\CEP\extensions\com.editclone.premiere\`
2. Make sure the folder is named exactly `com.editclone.premiere`.
3. Verify `CSXS/manifest.xml` is present inside that folder.

---

## Debugging the Panel

CEP panels run in an embedded Chromium browser. You can open Chrome DevTools:

1. In `CSXS/manifest.xml`, confirm `<Parameter>--enable-nodejs</Parameter>` is present.
2. Open a Chromium browser and go to: `http://localhost:7777`
3. You should see the EditClone panel listed. Click "inspect".

If port 7777 is not responding, add the debug port to `manifest.xml`:

```xml
<CEFCommandLine>
  <Parameter>--remote-debugging-port=7777</Parameter>
  <Parameter>--enable-nodejs</Parameter>
  <Parameter>--mixed-context</Parameter>
</CEFCommandLine>
```

---

## Changing the API URL

The panel connects directly to the backend API. The URL is hardcoded in `main.js`:

```javascript
// Line near the top of main.js
var EDITCLONE_URL = "https://editclone.vercel.app/ja/dashboard?plugin=premiere";
```

For local backend development, change to:
```javascript
var EDITCLONE_URL = "http://localhost:8000";
```

---

## Packaging for Adobe Exchange

1. Download ZXPSignCmd from [Adobe's GitHub](https://github.com/Adobe-CEP/CEP-Resources/tree/master/ZXPSignCMD).
2. Create a self-signed certificate (for testing) or use your Exchange certificate:
   ```bash
   ZXPSignCmd -selfSignedCert US CA EditClone EditClone password editclone.p12
   ```
3. Package the extension:
   ```bash
   ZXPSignCmd -sign plugins/premiere-cep/ EditClone.zxp editclone.p12 password
   ```
4. Submit `EditClone.zxp` via [Adobe Developer Console](https://developer.adobe.com/developer-console/).

Review takes approximately 2–4 weeks.

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| Extension not in Window > Extensions | Run `debug-enable` again; verify Premiere version >= CC 2019 |
| Panel shows blank white screen | Check DevTools at http://localhost:7777 for JS errors |
| `CSInterface is not defined` | `CSInterface.js` is missing — it should be in the extension root |
| ExtendScript errors in host.jsx | Open the ExtendScript Toolkit (ESTK) for debugging |
| "PlayerDebugMode" key not taking effect | Some Premiere installations use a higher CSXS version; the installer sets 9-12 |
| Import fails silently | Check the browser console for network errors; verify the token is valid |
