# EditClone — DaVinci Resolve Script

AI editing agent for DaVinci Resolve. Upload a video, describe your edit, and the script
builds a timeline automatically. Supports interactive chat editing, Style Profiles, and
FCPXML import for operations DaVinci's Python API cannot handle directly (speed, transitions).

No App Store review required — distribute the `.py` file directly.

---

## Requirements

| Requirement | Minimum version |
|-------------|----------------|
| DaVinci Resolve | 18.0 (Free or Studio) |
| Python | Bundled with DaVinci (3.9+) |
| OS | macOS 12+ or Windows 10+ |
| Network | Outbound HTTPS to Railway + Supabase |

---

## Install

### macOS

```bash
cd plugins/davinci-script
bash install.sh
```

Manual path:
```
~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/
```

### Windows

```
cd plugins\davinci-script
install.bat
```

Manual path:
```
%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
```

### Linux

```bash
cp editclone_import.py \
  ~/.local/share/DaVinciResolve/Fusion/Scripts/Utility/editclone_import.py
```

---

## Configuration

On first launch the script opens a dialog asking for your API URL and token.
These are saved to `~/.editclone/config.json` for future sessions.

| Setting | Value |
|---------|-------|
| API URL | `https://editclone-production.up.railway.app` |
| Token | Generate at https://editclone.vercel.app/ja/account > API Keys |

To update settings without the dialog, edit `~/.editclone/config.json`:

```json
{
  "api_url": "https://editclone-production.up.railway.app",
  "api_token": "eck_your_token_here"
}
```

---

## How to Use

1. Open DaVinci Resolve and load a project with clips in the Media Pool.
2. Go to **Workspace > Scripts > Utility > editclone_import**.
3. The EditClone Agent window opens with four tabs:

### Tab 1 — AI Edit

1. Select a clip from the Media Pool dropdown (click **↻** to refresh).
2. Type an editing instruction, or pick a quick prompt (e.g. "フィラー除去").
3. Optionally select a Style Profile.
4. Click **AIで編集**.

The script uploads the clip, sends it to the backend, polls for completion,
then creates a new timeline with the AI-suggested cuts applied.

### Tab 2 — Chat

Once a job is processed, use the chat tab to refine the edit with natural language:

```
冒頭30秒をカット
字幕を追加
再生速度を120%にして
```

Operations supported natively in DaVinci (cut, trim, audio volume, zoom, markers, subtitles)
are applied immediately. For operations requiring FCPXML (speed ramp, transitions), a button
appears to import via FCPXML.

### Tab 3 — Styles

View and activate your Style Profiles. The active profile is used for new AI edits.

### Tab 4 — Settings

Update API URL and token. Use "接続テスト" to verify connectivity.

---

## Test Connection (no DaVinci needed)

```bash
python plugins/davinci-script/test_connection.py
```

With explicit credentials:

```bash
python plugins/davinci-script/test_connection.py \
  --api-url https://editclone-production.up.railway.app \
  --token eck_your_token_here
```

Output example:
```
--- Config ---
  PASS  Config file found: /Users/you/.editclone/config.json
  PASS  API URL: https://editclone-production.up.railway.app
  PASS  Token:   eck_ab...

--- Health Check  (GET /health) ---
  PASS  HTTP 200 — version: 1.5.0

--- Authentication  (GET /plugin/me) ---
  PASS  HTTP 200 — authenticated as: you@example.com  (plan: creator)

--- Job Listing  (GET /plugin/jobs) ---
  PASS  HTTP 200 — 3 job(s) found

All tests passed. The DaVinci plugin is ready to use.
```

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| Script not in Workspace > Scripts menu | Verify the file is in the `Utility/` subdirectory; restart DaVinci |
| "DaVinci 未接続" in the header | Run the script from inside DaVinci (Workspace > Scripts), not from a terminal |
| "設定不足" dialog | Enter API URL and token in the Settings tab |
| Upload hangs | Check file size; files over 2 GB may time out — compress first |
| "タイムライン生成失敗" | Make sure the selected clip is in the active project's Media Pool |
| `tkinter` not found | DaVinci on some Linux builds omits tkinter; install `python3-tk` system-wide |

---

## Output Files

Downloaded assets are saved to:

- macOS: `~/Movies/EditClone/{job_id}/`
- Windows: `%USERPROFILE%\Videos\EditClone\{job_id}\`

Each job directory contains:
- `subtitle.srt` — subtitle file (downloaded on demand)
- `rich_edit.fcpxml` — FCPXML for speed/transition operations (downloaded on demand)
