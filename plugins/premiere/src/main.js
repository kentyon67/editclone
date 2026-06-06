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
let selectedJob = null;

// ---- DOM helpers ----
const $ = (id) => document.getElementById(id);
function show(id) { $(id).classList.remove("hidden"); }
function hide(id) { $(id).classList.add("hidden"); }
function showScreen(name) {
  ["screen-login", "screen-jobs", "screen-importing"].forEach((s) => {
    document.getElementById(s).classList.add("hidden");
  });
  show(`screen-${name}`);
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

function authHeaders() {
  return { Authorization: `Bearer ${accessToken}` };
}

// ---- Jobs ----
async function loadJobs() {
  show("jobs-loading");
  hide("jobs-list");
  hide("jobs-empty");

  const res = await fetch(`${API_BASE}/plugin/jobs`, { headers: authHeaders() });
  if (res.status === 401) { logout(); return; }
  const data = await res.json();
  const jobs = data.jobs || [];

  hide("jobs-loading");
  if (jobs.length === 0) {
    show("jobs-empty");
    return;
  }

  const list = $("jobs-list");
  list.innerHTML = "";

  jobs.forEach((job) => {
    const card = document.createElement("div");
    card.className = "job-card";
    card.dataset.jobId = job.job_id;
    const cutBadge = job.cut_count != null
      ? `<span class="badge cut-badge">${job.cut_count} cuts</span>`
      : "";
    card.innerHTML = `
      <div class="name">${escapeHtml(job.video_name || job.filename)}</div>
      <div class="date">${formatDate(job.created_at)}</div>
      <div class="badges">
        ${job.has_mp4 ? '<span class="badge mp4-badge">MP4</span>' : ""}
        ${cutBadge}
      </div>
    `;
    card.addEventListener("click", () => selectJob(card, job));
    list.appendChild(card);
  });

  show("jobs-list");
}

function selectJob(card, job) {
  document.querySelectorAll(".job-card").forEach((c) => c.classList.remove("selected"));
  card.classList.add("selected");
  selectedJob = job;

  // 既存のインポートセクションを削除
  const prev = document.querySelector(".import-section");
  if (prev) prev.remove();

  const section = document.createElement("div");
  section.className = "import-section";
  section.innerHTML = `
    <h3>「${escapeHtml(job.video_name || job.filename)}」をインポート</h3>
    <button id="btn-do-import" class="btn btn-import">Premiere Pro にインポート</button>
    <button id="btn-dl-srt" class="btn btn-ghost small">字幕 SRT をダウンロード</button>
  `;
  $("jobs-list").appendChild(section);

  document.getElementById("btn-do-import").addEventListener("click", () => importJob(job));
  document.getElementById("btn-dl-srt").addEventListener("click", () => downloadSRT(job));
}

async function importJob(job) {
  showScreen("importing");
  $("import-status").textContent = "Premiere XML をダウンロード中...";

  try {
    // Premiere XML をダウンロード
    const res = await fetch(
      `${API_BASE}/plugin/jobs/${job.job_id}/premiere-xml`,
      { headers: authHeaders() }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const xmlText = await res.text();

    $("import-status").textContent = "ファイルを保存中...";

    const tempFolder = await fs.getTemporaryFolder();
    const xmlFile = await tempFolder.createFile(`editclone_${job.job_id}.xml`, {
      overwrite: true,
    });
    await xmlFile.write(xmlText, { format: storage.formats.utf8 });

    $("import-status").textContent = "Premiere Pro にインポート中...";

    const ppCore = require("premierePro");
    const app = ppCore.app;
    if (!app.project) {
      throw new Error("プロジェクトが開かれていません。Premiere Pro でプロジェクトを開いてください。");
    }

    // importFiles(paths, suppressUI, targetBin, importAsNumberedStills)
    const imported = app.project.importFiles(
      [xmlFile.nativePath],
      true,
      app.project.getInsertionBin(),
      false
    );

    if (imported) {
      $("import-status").textContent = "✅ インポート完了！";
      setTimeout(() => showScreen("jobs"), 1500);
    } else {
      throw new Error("インポートに失敗しました。Premiere Pro でプロジェクトが開かれているか確認してください。");
    }
  } catch (err) {
    $("import-status").textContent = `❌ エラー: ${err.message}`;
    setTimeout(() => showScreen("jobs"), 3000);
  }
}

async function downloadSRT(job) {
  const btn = document.getElementById("btn-dl-srt");
  if (!btn) return;
  btn.disabled = true;
  btn.textContent = "ダウンロード中...";

  try {
    // ZIPからSRTを取り出す代わりにAPIから直接取得（将来エンドポイント追加時に備え）
    // 現状はZIP全体をダウンロードして SRT を案内
    const res = await fetch(
      `${API_BASE}/jobs/${job.job_id}/download`,
      { headers: authHeaders() }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();

    const tempFolder = await fs.getTemporaryFolder();
    const zipFile = await tempFolder.createFile(`editclone_${job.job_id}.zip`, { overwrite: true });
    const buf = await blob.arrayBuffer();
    await zipFile.write(buf, { format: storage.formats.binary });

    require("uxp").shell.openExternal(
      `${WEB_BASE}/ja/results/${job.job_id}`
    );
    btn.textContent = "✅ Web で SRT をダウンロード";
  } catch (err) {
    btn.textContent = "❌ 失敗";
    setTimeout(() => { btn.textContent = "字幕 SRT をダウンロード"; btn.disabled = false; }, 2000);
    return;
  }
  setTimeout(() => { btn.textContent = "字幕 SRT をダウンロード"; btn.disabled = false; }, 3000);
}

// ---- Token 永続化（localStorage 使用 — UXP では sessionStorage が不安定）----
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
  selectedJob = null;
  showScreen("login");
}

// ---- Utilities ----
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("ja-JP", {
    year: "numeric", month: "short", day: "numeric",
  });
}

// ---- Event Listeners ----
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
    await initJobsScreen();
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
$("btn-refresh").addEventListener("click", loadJobs);

$("link-signup").addEventListener("click", (e) => {
  e.preventDefault();
  require("uxp").shell.openExternal(`${WEB_BASE}/ja/signup`);
});

$("link-open-web").addEventListener("click", (e) => {
  e.preventDefault();
  require("uxp").shell.openExternal(`${WEB_BASE}/ja/upload`);
});

// ---- Init ----
async function initJobsScreen() {
  try {
    const res = await fetch(`${API_BASE}/plugin/me`, { headers: authHeaders() });
    if (!res.ok) throw new Error("auth");
    const me = await res.json();
    $("user-email").textContent = me.email || "";
  } catch (_) {
    logout();
    return;
  }
  showScreen("jobs");
  await loadJobs();
}

async function init() {
  const token = loadToken();
  if (token) {
    accessToken = token;
    await initJobsScreen();
  } else {
    showScreen("login");
  }
}

init();
