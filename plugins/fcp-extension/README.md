# EditClone — Final Cut Pro Workflow Extension

## 概要

FCP のタイムラインから EditClone を直接呼び出し、無音カット済み FCPXML を 1 クリックでインポートできる Workflow Extension です。

## 開発環境

| 項目 | 要件 |
|------|------|
| macOS | 13 (Ventura) 以上 |
| Xcode | 15 以上 |
| Apple Developer Program | 必要 (年 $99) |
| Final Cut Pro | 10.6 以上 |

## Xcode プロジェクト作成手順

1. Xcode を開く → **File > New > Project**
2. **macOS > App** を選択
3. Product Name: `EditClone`、Bundle ID: `com.editclone.fcp-extension`
4. Language: Swift、Interface: SwiftUI

5. ソースファイルをコピー:
   - `EditClone/EditCloneApp.swift`
   - `EditClone/ContentView.swift`
   - `EditClone/EditCloneWebView.swift`

6. `Info.plist` の内容を Xcode の Info タブに反映

7. **Signing & Capabilities** に追加:
   - `Network`
   - `Workflow Extension` (com.apple.developer.workflow-extension-api)

8. `EditClone.entitlements` を Signing & Capabilities → + Capability → Custom Entitlements でリンク

## デプロイ URL の変更

`ContentView.swift` の `baseURL` を本番 URL に変更:
```swift
private let baseURL = "https://your-production-url.vercel.app"
```

## App Store Connect への申請手順

1. **App Store Connect** でアプリを新規作成
   - Bundle ID: `com.editclone.fcp-extension`
   - Category: **Productivity**

2. スクリーンショット準備 (1280×800 または 1440×900)
   - FCP 内で開いている状態
   - 動画処理中の状態
   - インポート完了の状態

3. App 説明文 (例):
   ```
   EditClone は AI が無音カット・テロップ生成を自動化する Final Cut Pro 拡張機能です。
   動画をアップロードするだけで、編集済み FCPXML と MP4 を生成します。
   ```

4. Xcode → **Product > Archive** でアーカイブ作成

5. **Validate App** → **Distribute App** → App Store Connect

6. App Store Connect で審査に提出

**審査期間: 約 1〜3 ヶ月**

## 動作フロー

```
FCP 起動
  └─ Window > Extensions > EditClone
       └─ EditClone Web アプリ表示 (WebView)
            └─ ログイン → 動画アップロード → AI 処理
                 └─ 「Final Cut Pro にインポート」ボタン
                      └─ ZIP ダウンロード → 保存ダイアログ
                           └─ FCP で自動オープン
```

## 注意事項

- 初回起動時はインターネット接続が必要
- FCP の外でも単体アプリとして動作する
- `com.apple.developer.workflow-extension-api` 権限はアプリ審査時に自動取得
