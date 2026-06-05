/**
 * EditClone — Premiere Pro ExtendScript ホスト
 * ZIP を解凍して FCPXML を Premiere プロジェクトにインポートする。
 *
 * CEP の main.js から evalScript("importEditCloneZip(path)") で呼ばれる。
 */

/**
 * ZIP 内の .fcpxml と media/ フォルダを Premiere にインポートする。
 * @param {string} zipPath - ローカルの ZIP ファイルパス
 * @returns {string} "ok" または エラーメッセージ
 */
function importEditCloneZip(zipPath) {
  try {
    var zipFile = new File(zipPath);
    if (!zipFile.exists) {
      return "ZIP not found: " + zipPath;
    }

    // ZIP を同じフォルダに展開
    var destFolder = new Folder(zipFile.parent.fsName + "/" + zipFile.name.replace(".zip", ""));
    if (!destFolder.exists) {
      destFolder.create();
    }

    // ExtendScript には ZIP 展開の標準APIがないため
    // Premiere の app.project.importFiles() で FCPXML を直接インポートできるかを試みる
    // 先に FCPXML を手動パスで探す（ユーザーが解凍済みの場合）
    var fcpxmlPath = zipFile.parent.fsName + "/" + zipFile.name.replace(".zip", ".fcpxml");
    var fcpxmlFile = new File(fcpxmlPath);

    if (fcpxmlFile.exists) {
      return importFCPXML(fcpxmlPath);
    }

    // ZIP が未解凍の場合: ユーザーに案内するメッセージを返す
    return "unzip_required:" + zipPath;
  } catch (e) {
    return "error:" + e.message;
  }
}

/**
 * FCPXML ファイルを現在の Premiere プロジェクトにインポートする。
 */
function importFCPXML(fcpxmlPath) {
  try {
    var proj = app.project;
    if (!proj) {
      return "No active project";
    }

    var importArray = [fcpxmlPath];
    var suppressDialog = true;
    proj.importFiles(importArray, suppressDialog, proj.rootItem, false);
    return "ok";
  } catch (e) {
    return "import_error:" + e.message;
  }
}

/**
 * アクティブなシーケンスの情報を返す（デバッグ用）
 */
function getSequenceInfo() {
  try {
    var seq = app.project.activeSequence;
    if (!seq) return "No active sequence";
    return seq.name + " | " + seq.frameSizeHorizontal + "x" + seq.frameSizeVertical;
  } catch (e) {
    return "error:" + e.message;
  }
}
