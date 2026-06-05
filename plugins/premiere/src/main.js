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
let selectedJobId = null;

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
    card.innerHTML = `
      <div class="name">${escapeHtml(job.video_name || job.filename)}</div>
      <div class="date">${formatDate(job.created_at)}</div>
      ${job.has_mp4 ? '<span class="badge">MP4 あり</span>' : ""}
    `;
    card.addEventListener("click", () => selectJob(card, job));
    list.appendChild(card);
  });

  show("jobs-list");
}

function selectJob(card, job) {
  document.querySelectorAll(".job-card").forEach((c) => c.classList.remove("selected"));
  card.classList.add("selected");
  selectedJobId = job.job_id;

  // Remove any previous import section
  const prev = document.querySelector(".import-section");
  if (prev) prev.remove();

  const section = document.createElement("div");
  section.className = "import-section";
  section.innerHTML = `
    <h3>「${escapeHtml(job.video_name)}」をインポート</h3>
    <button id="btn-do-import" class="btn btn-import">Premiere Pro にインポート</button>
  `;
  $("jobs-list").appendChild(section);

  document.getElementById("btn-do-import").addEventListener("click", () => importJob(job));
}

async function importJob(job) {
  showScreen("importing");
  $("import-status").textContent = "Premiere XML をダウンロード中...";

  try {
    // Download Premiere XML
    const res = await fetch(
      `${API_BASE}/plugin/jobs/${job.job_id}/premiere-xml`,
      { headers: authHeaders() }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const xmlText = await res.text();

    $("import-status").textContent = "ファイルを保存中...";

    // Save to temp folder
    const tempFolder = await fs.getTemporaryFolder();
    const xmlFile = await tempFolder.createFile(`editclone_${job.job_id}.xml`, {
      overwrite: true,
    });
    await xmlFile.write(xmlText, { format: storage.formats.utf8 });

    $("import-status").textContent = "Premiere Pro にインポート中...";

    // Import into Premiere Pro
    const ppCore = require("premierePro");
    const app = ppCore.app;
    if (!app.project) {
      throw new Error("プロジェクトが開かれていません");
    }
    const imported = app.project.importFiles(
      [xmlFile.nativePath],
      true,
      app.project.getInsertionBin(),
      false
    );

    if (imported) {
      $("import-status").textContent = "インポート完了！";
      setTimeout(() => showScreen("jobs"), 1500);
    } else {
      throw new Error("インポートに失敗しました");
    }
  } catch (err) {
    $("import-status").textContent = `エラー: ${err.message}`;
    setTimeout(() => showScreen("jobs"), 2500);
  }
}

// ---- Session storage ----
function saveToken(token) {
  try { sessionStorage.setItem("ec_token", token); } catch (_) {}
  accessToken = token;
}

function loadToken() {
  try { return sessionStorage.getItem("ec_token"); } catch (_) { return null; }
}

function logout() {
  try { sessionStorage.removeItem("ec_token"); } catch (_) {}
  accessToken = null;
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

// ---- Event listeners ----
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
  // Verify token
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
