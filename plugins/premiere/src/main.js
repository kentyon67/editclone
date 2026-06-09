/* global require */
"use strict";

// ---- UXP modules ----
const { storage } = require("uxp");
const fs = storage.localFileSystem;

// ---- Config ----
const API_BASE = "https://editclone-production.up.railway.app";
const WEB_BASE = "https://editclone.vercel.app";

// ---- State ----
let accessToken = null;
let allJobs = [];
let activeStyles = [];
let agentPollingTimer = null;
let pendingAgentJobId = null;

// ---- DOM helpers ----
const $ = (id) => document.getElementById(id);
function show(id) { const el = $(id); if (el) el.classList.remove("hidden"); }
function hide(id) { const el = $(id); if (el) el.classList.add("hidden"); }

function showScreen(name) {
  ["screen-login", "screen-agent", "screen-importing"].forEach((s) => {
    const el = document.getElementById(s);
    if (el) el.classList.add("hidden");
  });
  show(`screen-${name}`);
}

function authHeaders() {
  return { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" };
}

// ---- Token persistence ----
function saveToken(token) {
  try { localStorage.setItem("ec_token", token); } catch (_) {}
  accessToken = token;
}
function loadToken() {
  try { return localStorage.getItem("ec_token"); } catch (_) { return null; }
}
function logout() {
  try { localStorage.removeItem("ec_token"); } catch (_) {}
  accessToken = null;
  allJobs = [];
  activeStyles = [];
  clearAgentPolling();
  showScreen("login");
}

// ---- Utilities ----
function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("ja-JP", {
    year: "numeric", month: "short", day: "numeric",
  });
}
function formatDuration(secs) {
  if (!secs) return "";
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

// ---- Auth ----
async function login(email, password) {
  const res = await fetch(`${API_BASE}/plugin/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("メールアドレスまたはパスワードが正しくありません");
  const data = await res.json();
  return data.access_token;
}

async function verifyAndInitAgent() {
  try {
    const res = await fetch(`${API_BASE}/plugin/me`, { headers: authHeaders() });
    if (!res.ok) { logout(); return; }
    const me = await res.json();
    const emailEl = $("header-email");
    if (emailEl) emailEl.textContent = me.email || "";
  } catch (_) { logout(); return; }

  showScreen("agent");
  await Promise.all([loadJobs(), loadStyles()]);
}

// ===========================================================================
// Jobs Tab
// ===========================================================================

async function loadJobs() {
  show("jobs-loading");
  hide("jobs-list");
  hide("jobs-empty");

  const res = await fetch(`${API_BASE}/plugin/jobs`, { headers: authHeaders() });
  if (res.status === 401) { logout(); return; }
  const data = await res.json();
  allJobs = data.jobs || [];

  hide("jobs-loading");
  renderJobsList();
  populateAgentJobSelect();
}

function renderJobsList() {
  if (allJobs.length === 0) {
    show("jobs-empty");
    return;
  }
  const list = $("jobs-list");
  list.innerHTML = "";

  allJobs.forEach((job) => {
    const card = document.createElement("div");
    card.className = "job-card";
    card.dataset.jobId = job.job_id;

    const cutText = job.cut_count != null ? `${job.cut_count}カット` : "";
    const promptSnippet = job.prompt ? `<div class="job-prompt">"${escapeHtml(job.prompt.slice(0, 40))}${job.prompt.length > 40 ? "…" : ""}"</div>` : "";

    card.innerHTML = `
      <div class="job-card-name">${escapeHtml(job.video_name || job.filename)}</div>
      <div class="job-card-meta">
        <span class="job-date">${formatDate(job.created_at)}</span>
        ${cutText ? `<span class="job-badge cut">${cutText}</span>` : ""}
        ${job.has_mp4 ? '<span class="job-badge mp4">MP4</span>' : ""}
      </div>
      ${promptSnippet}
      <div class="job-card-actions hidden" id="actions-${job.job_id}">
        <button class="btn-action import" data-job-id="${job.job_id}">📥 インポート</button>
        <button class="btn-action srt" data-job-id="${job.job_id}">📄 SRT</button>
        <button class="btn-action re-edit" data-job-id="${job.job_id}">🤖 再編集</button>
      </div>
    `;

    card.addEventListener("click", (e) => {
      if (e.target.closest(".btn-action")) return;
      const actionsId = `actions-${job.job_id}`;
      const actionsEl = document.getElementById(actionsId);
      const isOpen = !actionsEl.classList.contains("hidden");
      // 全カード閉じる
      document.querySelectorAll(".job-card-actions").forEach((el) => el.classList.add("hidden"));
      document.querySelectorAll(".job-card").forEach((el) => el.classList.remove("selected"));
      if (!isOpen) {
        actionsEl.classList.remove("hidden");
        card.classList.add("selected");
      }
    });

    list.appendChild(card);
  });

  // アクションボタン
  list.querySelectorAll(".btn-action.import").forEach((btn) => {
    btn.addEventListener("click", () => importJob(btn.dataset.jobId));
  });
  list.querySelectorAll(".btn-action.srt").forEach((btn) => {
    btn.addEventListener("click", () => downloadSRT(btn.dataset.jobId));
  });
  list.querySelectorAll(".btn-action.re-edit").forEach((btn) => {
    btn.addEventListener("click", () => jumpToAgentWithJob(btn.dataset.jobId));
  });

  show("jobs-list");
}

async function importJob(jobId) {
  showScreen("importing");
  const statusEl = $("import-status");
  if (statusEl) statusEl.textContent = "Premiere XML をダウンロード中...";

  try {
    const res = await fetch(
      `${API_BASE}/plugin/jobs/${jobId}/premiere-xml`,
      { headers: authHeaders() }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const xmlText = await res.text();

    if (statusEl) statusEl.textContent = "ファイルを保存中...";
    const tempFolder = await fs.getTemporaryFolder();
    const xmlFile = await tempFolder.createFile(`editclone_${jobId}.xml`, { overwrite: true });
    await xmlFile.write(xmlText, { format: storage.formats.utf8 });

    if (statusEl) statusEl.textContent = "Premiere Pro にインポート中...";
    const ppCore = require("premierePro");
    const app = ppCore.app;
    if (!app.project) {
      throw new Error("プロジェクトを開いてください（File > New Project）");
    }

    const imported = app.project.importFiles(
      [xmlFile.nativePath], true, app.project.getInsertionBin(), false
    );
    if (imported) {
      if (statusEl) statusEl.textContent =
        "✅ インポート完了！ メディアがオフラインの場合は右クリック → Link Media で元ファイルを指定してください";
      // 暗黙的学習: インポート完了 = 肯定的フィードバックとして自動記録
      sendImplicitFeedback(jobId).catch(() => {});
      setTimeout(() => { showScreen("agent"); switchTab("jobs"); }, 2500);
    } else {
      throw new Error("インポートに失敗しました");
    }
  } catch (err) {
    if (statusEl) statusEl.textContent = `❌ ${err.message}`;
    setTimeout(() => { showScreen("agent"); switchTab("jobs"); }, 3000);
  }
}

async function sendImplicitFeedback(jobId) {
  try {
    const detailsRes = await fetch(`${API_BASE}/plugin/jobs/${jobId}/details`, {
      headers: authHeaders(),
    });
    if (!detailsRes.ok) return;
    const details = await detailsRes.json();
    const projectId = details.project_id;
    if (!projectId) return;

    await fetch(`${API_BASE}/projects/${projectId}/revisions`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        notes: "auto:premiere_import",
        metadata: { source: "premiere_uxp", job_id: jobId },
      }),
    });
  } catch (_) {}
}

async function downloadSRT(jobId) {
  try {
    const res = await fetch(`${API_BASE}/plugin/jobs/${jobId}/srt`, { headers: authHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const srtText = await res.text();

    const tempFolder = await fs.getTemporaryFolder();
    const srtFile = await tempFolder.createFile(`editclone_${jobId}.srt`, { overwrite: true });
    await srtFile.write(srtText, { format: storage.formats.utf8 });

    require("uxp").shell.openPath(srtFile.nativePath);
  } catch (err) {
    // フォールバック: Web ページを開く
    require("uxp").shell.openExternal(`${WEB_BASE}/ja/results/${jobId}`);
  }
}

function jumpToAgentWithJob(jobId) {
  switchTab("agent");
  const sel = $("agent-job-select");
  if (sel) sel.value = jobId;
}

// ===========================================================================
// Agent Tab
// ===========================================================================

function populateAgentJobSelect() {
  const sel = $("agent-job-select");
  if (!sel) return;
  const prev = sel.value;
  sel.innerHTML = '<option value="">-- 動画を選択 --</option>';
  allJobs.forEach((job) => {
    const opt = document.createElement("option");
    opt.value = job.job_id;
    opt.textContent = `${job.video_name || job.filename} (${formatDate(job.created_at)})`;
    sel.appendChild(opt);
  });
  if (prev) sel.value = prev;
}

async function startAgentEdit() {
  const jobId = $("agent-job-select")?.value;
  const prompt = $("agent-prompt")?.value?.trim();

  if (!jobId) {
    showAgentError("対象ジョブを選択してください");
    return;
  }
  if (!prompt) {
    showAgentError("編集指示を入力してください");
    return;
  }

  clearAgentPolling();
  hide("agent-error");
  hide("agent-result");
  show("agent-processing");
  $("btn-agent-send").disabled = true;

  const progressEl = $("agent-progress-text");
  if (progressEl) progressEl.textContent = "AI 編集を開始中...";

  // プロンプトが複雑な場合はエージェントチームモードを試みる
  const useTeams = prompt.length > 20 || prompt.includes(",") || prompt.includes("、");

  if (useTeams && progressEl) {
    progressEl.textContent = "🤖 エージェントチーム起動中...";
  }

  try {
    // まず team-edit エンドポイントで即時編集操作を取得する（ジョブなし・高速）
    const teamRes = await fetch(`${API_BASE}/plugin/jobs/${jobId}/team-edit`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ prompt, history: [], use_teams: useTeams }),
    });

    if (teamRes.ok) {
      const teamData = await teamRes.json();
      const agentReports = teamData.agent_reports || {};
      const agentSucceeded = teamData.agents_succeeded || [];
      const synthesis = teamData.synthesis || "";

      // エージェント協調完了を表示してから agent-edit に移行
      if (agentSucceeded.length > 0 && progressEl) {
        progressEl.textContent = `🤖 ${agentSucceeded.length} エージェント協調完了`;
        // 1秒後に通常のポーリングフロー（agent-edit）へ
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }

      // エージェントレポートをコンソールに出力（デバッグ用）
      Object.entries(agentReports).forEach(([name, report]) => {
        if (report && !report.startsWith("(")) {
          console.log(`[EditClone ${name}]`, report.slice(0, 200));
        }
      });
    }

    // 通常の agent-edit フローに移行（バックグラウンドジョブとして処理）
    if (progressEl) progressEl.textContent = "AI 編集ジョブを送信中...";
    const res = await fetch(`${API_BASE}/plugin/jobs/${jobId}/agent-edit`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ prompt }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    pendingAgentJobId = data.job_id;
    startPolling(pendingAgentJobId);
  } catch (err) {
    hide("agent-processing");
    $("btn-agent-send").disabled = false;
    showAgentError(err.message);
  }
}

const PROGRESS_LABELS = {
  "pending": "ジョブ待機中...",
  "processing": "処理中...",
  "動画情報を取得中...": "動画を解析中... (1/8)",
  "セリフを文字起こし中...": "音声を文字起こし中... (2/8)",
  "無音箇所を検出中...": "無音区間を検出中... (3/8)",
  "AIが編集指示を解析中...": "AI がカットを判断中... (4/8)",
  "チャプター生成中...": "チャプターを生成中... (5/8)",
  "字幕ファイル生成中...": "字幕を生成中... (6/8)",
  "FCPXMLを生成中...": "編集プロジェクトを生成中... (7/8)",
  "MP4 をレンダリング中...": "MP4 をレンダリング中... (8/8)",
  "ファイルをまとめています...": "ファイルをパッケージ中...",
  "完了": "完了",
};

const PROGRESS_WIDTHS = {
  "動画情報を取得中...": 12,
  "セリフを文字起こし中...": 25,
  "無音箇所を検出中...": 40,
  "AIが編集指示を解析中...": 52,
  "チャプター生成中...": 62,
  "字幕ファイル生成中...": 70,
  "FCPXMLを生成中...": 78,
  "Premiere XML を生成中...": 82,
  "EDL を生成中...": 86,
  "MP4 をレンダリング中...": 90,
  "ファイルをまとめています...": 96,
  "完了": 100,
};

function startPolling(jobId) {
  let attempts = 0;
  const maxAttempts = 120; // 最大6分

  agentPollingTimer = setInterval(async () => {
    attempts++;
    if (attempts > maxAttempts) {
      clearAgentPolling();
      hide("agent-processing");
      $("btn-agent-send").disabled = false;
      showAgentError("タイムアウトしました。Web ページで状態を確認してください。");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/plugin/jobs/${jobId}/poll`, { headers: authHeaders() });
      if (!res.ok) return;
      const data = await res.json();

      const progressEl = $("agent-progress-text");
      const barEl = $("agent-progress-bar");
      const label = PROGRESS_LABELS[data.progress] || data.progress || "処理中...";
      const width = PROGRESS_WIDTHS[data.progress] || 10;
      if (progressEl) progressEl.textContent = label;
      if (barEl) barEl.style.width = `${width}%`;

      if (data.status === "completed") {
        clearAgentPolling();
        hide("agent-processing");
        $("btn-agent-send").disabled = false;
        showAgentResult(jobId);
        await loadJobs(); // ジョブリスト更新
      } else if (data.status === "failed") {
        clearAgentPolling();
        hide("agent-processing");
        $("btn-agent-send").disabled = false;
        showAgentError(`処理に失敗しました: ${data.error || "不明なエラー"}`);
      }
    } catch (_) {}
  }, 3000);
}

function clearAgentPolling() {
  if (agentPollingTimer) {
    clearInterval(agentPollingTimer);
    agentPollingTimer = null;
  }
}

function showAgentResult(jobId) {
  pendingAgentJobId = jobId;
  const label = $("agent-result-label");
  if (label) label.textContent = "✅ AI 編集が完了しました！";
  show("agent-result");
  hide("agent-error");
}

function showAgentError(msg) {
  const el = $("agent-error");
  if (el) {
    el.textContent = msg;
    el.classList.remove("hidden");
  }
}

// ===========================================================================
// Styles Tab
// ===========================================================================

async function loadStyles() {
  show("styles-loading");
  hide("styles-list");
  hide("styles-empty");

  try {
    const res = await fetch(`${API_BASE}/plugin/style-profiles`, { headers: authHeaders() });
    if (!res.ok) { hide("styles-loading"); return; }
    const data = await res.json();
    activeStyles = data.profiles || [];
  } catch (_) {
    hide("styles-loading");
    return;
  }

  hide("styles-loading");
  renderStylesList();
}

function renderStylesList() {
  if (activeStyles.length === 0) {
    show("styles-empty");
    return;
  }
  const list = $("styles-list");
  list.innerHTML = "";

  activeStyles.forEach((profile) => {
    const card = document.createElement("div");
    card.className = `style-card${profile.is_active ? " active" : ""}`;
    card.id = `style-${profile.id}`;

    const captionStyle = profile.caption_style || {};
    const zoom = captionStyle.zoom_effect || "none";
    const zoomLabel = { none: "ズームなし", subtle: "ズーム小", punch: "ズーム強" }[zoom] || zoom;
    const promptPreview = (profile.default_prompt || "").slice(0, 50);

    card.innerHTML = `
      <div class="style-card-header">
        <div class="style-name">${escapeHtml(profile.name)}</div>
        ${profile.is_active ? '<span class="active-badge">✓ アクティブ</span>' : ""}
      </div>
      <div class="style-stats">
        <span>無音: ${profile.noise_db ?? -30}dB</span>
        <span>最小: ${profile.min_silence_seconds ?? 0.5}s</span>
        <span>${zoomLabel}</span>
      </div>
      ${promptPreview ? `<div class="style-prompt">"${escapeHtml(promptPreview)}${profile.default_prompt?.length > 50 ? "…" : ""}"</div>` : ""}
      ${!profile.is_active ? `<button class="btn-activate" data-id="${profile.id}">アクティブに設定</button>` : ""}
    `;
    list.appendChild(card);
  });

  list.querySelectorAll(".btn-activate").forEach((btn) => {
    btn.addEventListener("click", () => activateStyle(btn.dataset.id));
  });

  show("styles-list");
}

async function activateStyle(profileId) {
  const btn = document.querySelector(`.btn-activate[data-id="${profileId}"]`);
  if (btn) { btn.disabled = true; btn.textContent = "設定中..."; }

  try {
    const res = await fetch(`${API_BASE}/plugin/style-profiles/${profileId}/activate`, {
      method: "POST",
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    await loadStyles();
  } catch (err) {
    if (btn) { btn.disabled = false; btn.textContent = "アクティブに設定"; }
    showAgentError(`スタイル設定に失敗: ${err.message}`);
  }
}

// ===========================================================================
// Tab switching
// ===========================================================================

function switchTab(name) {
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === name);
  });
  document.querySelectorAll(".tab-content").forEach((c) => {
    c.classList.add("hidden");
  });
  const target = document.getElementById(`tab-${name}`);
  if (target) target.classList.remove("hidden");
}

// ===========================================================================
// Event Listeners
// ===========================================================================

// Login
$("btn-login").addEventListener("click", async () => {
  const email = $("input-email").value.trim();
  const password = $("input-password").value;
  const errEl = $("login-error");
  errEl.classList.add("hidden");
  if (!email || !password) {
    errEl.textContent = "メールアドレスとパスワードを入力してください";
    errEl.classList.remove("hidden");
    return;
  }
  $("btn-login").disabled = true;
  $("btn-login").textContent = "ログイン中...";
  try {
    const token = await login(email, password);
    saveToken(token);
    await verifyAndInitAgent();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove("hidden");
  } finally {
    $("btn-login").disabled = false;
    $("btn-login").textContent = "ログイン";
  }
});

$("input-password").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("btn-login").click();
});

$("btn-logout").addEventListener("click", logout);
$("btn-refresh-jobs").addEventListener("click", loadJobs);
$("btn-refresh-styles").addEventListener("click", loadStyles);

// Tabs
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

// Agent quick prompts
document.querySelectorAll(".quick-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const ta = $("agent-prompt");
    if (ta) ta.value = btn.dataset.prompt;
  });
});

$("btn-agent-send").addEventListener("click", startAgentEdit);

// Import result after agent edit
$("btn-import-result").addEventListener("click", () => {
  if (pendingAgentJobId) importJob(pendingAgentJobId);
});

$("btn-agent-edit-again").addEventListener("click", () => {
  hide("agent-result");
  hide("agent-error");
  const ta = $("agent-prompt");
  if (ta) ta.value = "";
});

// Web links
document.querySelectorAll("#link-signup, #link-open-web, #link-create-style, #link-create-style2").forEach((a) => {
  a.addEventListener("click", (e) => {
    e.preventDefault();
    const path = e.target.id === "link-signup" ? "/ja/signup" : "/ja";
    if (e.target.id === "link-create-style" || e.target.id === "link-create-style2") {
      require("uxp").shell.openExternal(`${WEB_BASE}/ja/styles`);
    } else {
      require("uxp").shell.openExternal(`${WEB_BASE}${path}`);
    }
  });
});

// ===========================================================================
// Init
// ===========================================================================

async function init() {
  const token = loadToken();
  if (token) {
    accessToken = token;
    await verifyAndInitAgent();
  } else {
    showScreen("login");
  }
}

init();
