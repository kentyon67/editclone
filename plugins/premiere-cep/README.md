# EditClone — Premiere Pro CEP Plugin

## 概要

Premiere Pro のパネルから EditClone を呼び出し、AI 編集済み FCPXML を直接インポートできる CEP 拡張機能です。

## 開発環境

| 項目 | 要件 |
|------|------|
| Premiere Pro | CC 2019 (v13.0) 以上 |
| OS | Windows / macOS |
| Adobe Developer Console | 申請に必要 |

## ローカルでのインストール・テスト

### 1. CEP デバッグモードを有効化

**macOS:**
```bash
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
```

**Windows (管理者 PowerShell):**
```powershell
reg add "HKEY_CURRENT_USER\SOFTWARE\Adobe\CSXS.11" /v PlayerDebugMode /t REG_SZ /d 1 /f
```

### 2. プラグインをコピー

**macOS:**
```
~/Library/Application Support/Adobe/CEP/extensions/com.editclone.premiere/
```

**Windows:**
```
%APPDATA%\Adobe\CEP\extensions\com.editclone.premiere\
```

`premiere-cep/` フォルダ内のファイルをそのままコピーする（フォルダ名は `com.editclone.premiere`）。

### 3. CSInterface.js を配置

Adobe の公式 [CEP Resources](https://github.com/Adobe-CEP/CEP-Resources) から `CSInterface.js` をダウンロードして `premiere-cep/` に配置する。

### 4. Premiere Pro を再起動

**Window > Extensions > EditClone** が表示される。

## Adobe Exchange への申請

1. [Adobe Developer Console](https://developer.adobe.com/developer-console/) でアプリ登録
2. Exchange 申請フォームに以下を記入:
   - **Product**: Premiere Pro
   - **Category**: Video Editing
   - **Description**: AI による無音カット・テロップ自動生成。編集済み FCPXML を Premiere に直接インポート。
3. ZCC パッケージを作成して提出

**審査期間: 約 2〜4 週間**

## デプロイ URL の変更

`main.js` の `EDITCLONE_URL` を本番 URL に変更:
```javascript
var EDITCLONE_URL = "https://your-production-url.vercel.app/ja/dashboard?plugin=premiere";
```

## 動作フロー

```
Premiere Pro 起動
  └─ Window > Extensions > EditClone
       └─ EditClone パネル表示
            └─ EditClone Web アプリ (iframe)
                 └─ ログイン → 動画アップロード → AI 処理
                      └─ 「Premiere Pro にインポート」ボタン
                           └─ ZIP ダウンロード → ExtendScript でインポート
```

## 注意事項

- FCPXML を Premiere にインポートするには Premiere が XML インポートに対応している必要がある
- XML インポートが効かない場合はユーザーが ZIP を解凍して手動インポートできる（案内メッセージ表示）
- `CSInterface.js` は Adobe のライセンスのためリポジトリに含めていない
