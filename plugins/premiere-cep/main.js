/* global CSInterface */

// EditClone の本番 URL（デプロイ後に変更すること）
var EDITCLONE_URL = "https://frontend-six-bice-51.vercel.app/ja/dashboard?plugin=premiere";

var csInterface = typeof CSInterface !== "undefined" ? new CSInterface() : null;
var pendingDownloadUrl = null;
var pendingFilename = null;

// ----- 起動 -----

document.addEventListener("DOMContentLoaded", function () {
  var frame = document.getElementById("app-frame");
  frame.src = EDITCLONE_URL;

  // iframe からの postMessage を受信する（EditClone web app が importFCPXML を送信）
  window.addEventListener("message", function (event) {
    var data = event.data;
    if (!data || data.action !== "importFCPXML") return;

    pendingDownloadUrl = data.url;
    pendingFilename = data.filename || "editclone_project.zip";

    var banner = document.getElementById("import-banner");
    var msg = document.getElementById("import-message");
    banner.classList.remove("hidden");
    msg.textContent = "\"" + pendingFilename + "\" を Premiere にインポート";
  });
});

// ----- インポートボタン -----

function triggerImport() {
  if (!pendingDownloadUrl) return;

  var btn = document.getElementById("import-btn");
  btn.disabled = true;
  btn.textContent = "ダウンロード中...";

  // Node.js (CEP) でファイルをダウンロードして ExtendScript に渡す
  downloadZip(pendingDownloadUrl, pendingFilename, function (localPath) {
    if (localPath) {
      // ExtendScript 経由で Premiere にインポート
      importViaExtendScript(localPath, function (result) {
        btn.disabled = false;
        if (result === "ok") {
          btn.textContent = "✓ インポート完了";
          setTimeout(function () {
            document.getElementById("import-banner").classList.add("hidden");
            btn.textContent = "Premiere Pro にインポート";
          }, 3000);
        } else {
          btn.textContent = "エラー: " + result;
        }
      });
    } else {
      btn.disabled = false;
      btn.textContent = "ダウンロードに失敗しました";
    }
  });
}

// ----- ファイルダウンロード (Node.js / XMLHttpRequest) -----

function downloadZip(url, filename, callback) {
  try {
    // CEP 環境: Node.js を使用
    var os = require("os");
    var path = require("path");
    var fs = require("fs");
    var https = require("https");
    var http = require("http");

    var tmpPath = path.join(os.tmpdir(), filename);
    var file = fs.createWriteStream(tmpPath);
    var protocol = url.startsWith("https") ? https : http;

    protocol.get(url, function (response) {
      response.pipe(file);
      file.on("finish", function () {
        file.close(function () { callback(tmpPath); });
      });
    }).on("error", function () {
      callback(null);
    });
  } catch (e) {
    // フォールバック: ブラウザダウンロード
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    callback(null);
  }
}

// ----- ExtendScript 呼び出し -----

function importViaExtendScript(zipPath, callback) {
  if (!csInterface) {
    callback("CSInterface not available");
    return;
  }
  var script = "importEditCloneZip(\"" + zipPath.replace(/\\/g, "\\\\").replace(/"/g, '\\"') + "\")";
  csInterface.evalScript(script, function (result) {
    callback(result || "ok");
  });
}
