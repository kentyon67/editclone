/**
 * EditClone — Premiere Pro ExtendScript ホスト
 * Premiere XML (XMEML) ファイルをプロジェクトに直接インポートする。
 * CEP の main.js から evalScript("importEditCloneXML(path)") で呼ばれる。
 */

/**
 * XML ファイルを現在の Premiere プロジェクトにインポートする。
 * @param {string} xmlPath - ローカルの .xml ファイルパス
 * @returns {string} "ok" または エラーメッセージ
 */
function importEditCloneXML(xmlPath) {
  try {
    var xmlFile = new File(xmlPath);
    if (!xmlFile.exists) {
      return "file_not_found:" + xmlPath;
    }

    var proj = app.project;
    if (!proj) {
      return "no_active_project";
    }

    // Premiere Pro は XMEML (FCP 7 XML) を importFiles() で読み込める
    var importArray = [xmlPath];
    proj.importFiles(importArray, true, proj.rootItem, false);

    // インポート後に最新のシーケンスをアクティブにする
    activateLatestSequence();

    return "ok";
  } catch (e) {
    return "import_error:" + e.message;
  }
}

/**
 * プロジェクト内の最後のシーケンスをアクティブにする。
 */
function activateLatestSequence() {
  try {
    var seqCount = app.project.sequences.numSequences;
    if (seqCount > 0) {
      var seq = app.project.sequences[seqCount - 1];
      app.project.activeSequence = seq;
      seq.setPlayerPosition("0");
    }
  } catch (e) {
    // シーケンス操作は必須ではないので失敗しても続行
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
