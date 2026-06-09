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

  showBanner("プロジェクトをダウンロード中...", "loading");

  // まずフル ZIP を試みる（メディア込みで展開してパス書き換え）
  downloadAndRewriteXML(jobId, token, apiBase, function (xmlPath, err) {
    if (err || !xmlPath) {
      // フォールバック: XML のみ（メディアはオフライン）
      var xmlUrl = apiBase + "/plugin/jobs/" + jobId + "/premiere-xml";
      downloadWithAuth(xmlUrl, token, jobId + "_editclone.xml", function (localPath, err2) {
        if (err2 || !localPath) {
          showBanner("ダウンロードエラー: " + (err2 || "不明"), "error");
          return;
        }
        showBanner("Premiere Pro にインポート中...", "loading");
        importXMLViaExtendScript(localPath, function (result) {
          handleImportResult(result, jobId, token, apiBase, true);
        });
      });
      return;
    }
    showBanner("Premiere Pro にインポート中...", "loading");
    importXMLViaExtendScript(xmlPath, function (result) {
      handleImportResult(result, jobId, token, apiBase, false);
    });
  });
}

function handleImportResult(result, jobId, token, apiBase, mediaOffline) {
  if (result === "ok") {
    var msg = "✓ インポート完了！";
    if (mediaOffline) msg += " メディアがオフラインの場合は右クリック → Link Media で元ファイルを指定してください";
    showBanner(msg, "success");
    sendImplicitFeedbackCEP(jobId, token, apiBase);
    setTimeout(hideBanner, 6000);
  } else if (result && result.indexOf("unzip_required") !== -1) {
    showBanner("ファイルを保存しました。Premiere で手動で File > Import してください", "info");
  } else {
    showBanner("インポートエラー: " + result, "error");
  }
}

// ----- ZIP ダウンロード + 展開 + パス書き換え -----

function downloadAndRewriteXML(jobId, token, apiBase, callback) {
  try {
    var os = require("os");
    var path = require("path");
    var fs = require("fs");
    var https = require("https");
    var http = require("http");
    var childProcess = require("child_process");

    var zipUrl = apiBase + "/jobs/" + jobId + "/download";
    var tmpDir = path.join(os.tmpdir(), "editclone_" + jobId);
    var zipPath = path.join(os.tmpdir(), jobId + "_project.zip");

    // ZIP をダウンロード
    var file = fs.createWriteStream(zipPath);
    var protocol = zipUrl.startsWith("https") ? https : http;
    var parsedUrl = require("url").parse(zipUrl);
    var options = {
      hostname: parsedUrl.hostname,
      port: parsedUrl.port || (zipUrl.startsWith("https") ? 443 : 80),
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
        file.close(function () {
          // ZIP を展開
          try {
            if (!fs.existsSync(tmpDir)) {
              fs.mkdirSync(tmpDir, { recursive: true });
            }
            var unzipCmd;
            if (process.platform === "win32") {
              unzipCmd = 'powershell -command "Expand-Archive -Force \'' +
                zipPath.replace(/'/g, "''") + "' '" + tmpDir.replace(/'/g, "''") + "'"+ '"';
            } else {
              unzipCmd = "/usr/bin/unzip -o " + JSON.stringify(zipPath) + " -d " + JSON.stringify(tmpDir);
            }
            childProcess.execSync(unzipCmd, { timeout: 30000 });

            // XMEML を探す
            var xmlPath = findFileRecursive(tmpDir, ".xml");
            if (!xmlPath) {
              callback(null, "xml_not_found");
              return;
            }

            // media ディレクトリを探してパスを書き換え
            var mediaDir = findDirRecursive(tmpDir, "media");
            if (mediaDir) {
              var xmlContent = fs.readFileSync(xmlPath, "utf8");
              var absMediaUrl;
              if (process.platform === "win32") {
                // Windows: file:///C:/path/to/media/
                absMediaUrl = "file:///" + mediaDir.replace(/\\/g, "/") + "/";
              } else {
                absMediaUrl = "file://" + mediaDir + "/";
              }
              xmlContent = xmlContent.replace(/\.\/media\//g, absMediaUrl);
              var rewrittenPath = path.join(tmpDir, jobId + "_relinked.xml");
              fs.writeFileSync(rewrittenPath, xmlContent, "utf8");
              callback(rewrittenPath, null);
            } else {
              callback(xmlPath, null);
            }
          } catch (e) {
            callback(null, e.message);
          }
        });
      });
    }).on("error", function (e) {
      callback(null, e.message);
    });
  } catch (e) {
    callback(null, e.message);
  }
}

function findFileRecursive(dir, ext) {
  try {
    var fs = require("fs");
    var path = require("path");
    var items = fs.readdirSync(dir);
    for (var i = 0; i < items.length; i++) {
      var full = path.join(dir, items[i]);
      var stat = fs.statSync(full);
      if (stat.isDirectory()) {
        var found = findFileRecursive(full, ext);
        if (found) return found;
      } else if (full.endsWith(ext)) {
        return full;
      }
    }
  } catch (e) {}
  return null;
}

function findDirRecursive(dir, name) {
  try {
    var fs = require("fs");
    var path = require("path");
    var items = fs.readdirSync(dir);
    for (var i = 0; i < items.length; i++) {
      var full = path.join(dir, items[i]);
      var stat = fs.statSync(full);
      if (stat.isDirectory()) {
        if (items[i] === name) return full;
        var found = findDirRecursive(full, name);
        if (found) return found;
      }
    }
  } catch (e) {}
  return null;
}

// ----- 暗黙的学習: インポート完了後に自動フィードバック送信 -----

function sendImplicitFeedbackCEP(jobId, token, apiBase) {
  try {
    var https = require("https");
    var http = require("http");
    var detailsUrl = apiBase + "/plugin/jobs/" + jobId + "/details";
    var parsedUrl = require("url").parse(detailsUrl);
    var protocol = detailsUrl.startsWith("https") ? https : http;
    var options = {
      hostname: parsedUrl.hostname,
      port: parsedUrl.port || (detailsUrl.startsWith("https") ? 443 : 80),
      path: parsedUrl.path,
      headers: { "Authorization": "Bearer " + token }
    };
    var chunks = [];
    protocol.get(options, function (res) {
      res.on("data", function (d) { chunks.push(d); });
      res.on("end", function () {
        try {
          var details = JSON.parse(Buffer.concat(chunks).toString());
          var projectId = details.project_id;
          if (!projectId) return;

          var revUrl = apiBase + "/projects/" + projectId + "/revisions";
          var parsedRev = require("url").parse(revUrl);
          var body = JSON.stringify({
            notes: "auto:premiere_cep_import",
            metadata: { source: "premiere_cep", job_id: jobId }
          });
          var revProto = revUrl.startsWith("https") ? https : http;
          var revOpts = {
            hostname: parsedRev.hostname,
            port: parsedRev.port || (revUrl.startsWith("https") ? 443 : 80),
            path: parsedRev.path,
            method: "POST",
            headers: {
              "Authorization": "Bearer " + token,
              "Content-Type": "application/json",
              "Content-Length": Buffer.byteLength(body)
            }
          };
          var req = revProto.request(revOpts, function () {});
          req.on("error", function () {});
          req.write(body);
          req.end();
        } catch (_) {}
      });
    }).on("error", function () {});
  } catch (_) {}
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
