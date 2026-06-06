/* global CSInterface */

var csInterface = typeof CSInterface !== "undefined" ? new CSInterface() : null;

// フロントエンド URL（設定ファイルまたはデフォルト）
var EDITCLONE_FRONTEND_URL = localStorage.getItem("editclone_frontend_url") || "https://editclone.vercel.app";

// ----- 起動 -----

document.addEventListener("DOMContentLoaded", function () {
  var frame = document.getElementById("app-frame");
  // nle=premiere クエリを付けてプラグインモードで開く
  frame.src = EDITCLONE_FRONTEND_URL + "/ja/dashboard?nle=premiere";

  // 設定ボタン
  var settingsBtn = document.getElementById("settings-btn");
  if (settingsBtn) {
    settingsBtn.addEventListener("click", function () {
      var url = prompt(
        "EditClone フロントエンド URL を入力してください:",
        EDITCLONE_FRONTEND_URL
      );
      if (url && url.trim()) {
        EDITCLONE_FRONTEND_URL = url.trim();
        localStorage.setItem("editclone_frontend_url", EDITCLONE_FRONTEND_URL);
        frame.src = EDITCLONE_FRONTEND_URL + "/ja/dashboard?nle=premiere";
      }
    });
  }

  // iframe からの postMessage を受信する
  window.addEventListener("message", function (event) {
    var data = event.data;
    if (!data || !data.action) return;

    if (data.action === "importPremiereXML") {
      // 新プロトコル: jobId + token + apiBase を使って XML を直接ダウンロード
      handleImportPremiereXML(data.jobId, data.token, data.apiBase);
    } else if (data.action === "importFCPXML") {
      // 後方互換: ZIP ダウンロード URL が渡された場合はそのままダウンロード
      handleLegacyDownload(data.url, data.filename || "editclone_project.zip");
    }
  });
});

// ----- Premiere XML 直接インポート（推奨） -----

function handleImportPremiereXML(jobId, token, apiBase) {
  if (!jobId || !token || !apiBase) {
    showBanner("エラー: 認証情報が不足しています", "error");
    return;
  }

  var xmlUrl = apiBase + "/plugin/jobs/" + jobId + "/premiere-xml";
  showBanner("Premiere XML をダウンロード中...", "loading");

  downloadWithAuth(xmlUrl, token, jobId + "_editclone.xml", function (localPath, err) {
    if (err || !localPath) {
      showBanner("ダウンロードエラー: " + (err || "不明"), "error");
      return;
    }
    showBanner("Premiere Pro にインポート中...", "loading");
    importXMLViaExtendScript(localPath, function (result) {
      if (result === "ok") {
        showBanner("✓ インポート完了！ プロジェクトパネルを確認してください", "success");
        setTimeout(hideBanner, 5000);
      } else if (result && result.indexOf("unzip_required") !== -1) {
        showBanner("ファイルを保存しました。Premiere で手動で File > Import してください", "info");
      } else {
        showBanner("インポートエラー: " + result, "error");
      }
    });
  });
}

// ----- ファイルダウンロード (認証ヘッダー付き, Node.js) -----

function downloadWithAuth(url, token, filename, callback) {
  try {
    var os = require("os");
    var path = require("path");
    var fs = require("fs");
    var https = require("https");
    var http = require("http");

    var tmpPath = path.join(os.tmpdir(), filename);
    var file = fs.createWriteStream(tmpPath);
    var protocol = url.startsWith("https") ? https : http;

    var parsedUrl = require("url").parse(url);
    var options = {
      hostname: parsedUrl.hostname,
      port: parsedUrl.port,
      path: parsedUrl.path,
      headers: { "Authorization": "Bearer " + token }
    };

    protocol.get(options, function (response) {
      if (response.statusCode !== 200) {
        callback(null, "HTTP " + response.statusCode);
        return;
      }
      response.pipe(file);
      file.on("finish", function () {
        file.close(function () { callback(tmpPath, null); });
      });
    }).on("error", function (e) {
      callback(null, e.message);
    });
  } catch (e) {
    callback(null, e.message);
  }
}

// ----- 後方互換: ZIP/URL ダウンロード -----

function handleLegacyDownload(url, filename) {
  if (!url) return;
  showBanner('"' + filename + '" をダウンロード中...', "loading");
  try {
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
        file.close(function () {
          showBanner("保存先: " + tmpPath + "（ZIP を解凍して手動インポートしてください）", "info");
        });
      });
    }).on("error", function () {
      showBanner("ダウンロードに失敗しました", "error");
    });
  } catch (e) {
    // フォールバック: ブラウザダウンロード
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    hideBanner();
  }
}

// ----- ExtendScript 呼び出し -----

function importXMLViaExtendScript(xmlPath, callback) {
  if (!csInterface) {
    callback("CSInterface not available");
    return;
  }
  var escaped = xmlPath.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  csInterface.evalScript('importEditCloneXML("' + escaped + '")', function (result) {
    callback(result || "ok");
  });
}

// ----- バナー UI -----

function showBanner(message, type) {
  var banner = document.getElementById("import-banner");
  var msg = document.getElementById("import-message");
  if (!banner || !msg) return;
  msg.textContent = message;
  banner.className = "import-banner " + (type || "");
  banner.classList.remove("hidden");
}

function hideBanner() {
  var banner = document.getElementById("import-banner");
  if (banner) banner.classList.add("hidden");
}
