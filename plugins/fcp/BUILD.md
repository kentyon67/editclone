# EditClone — FCP Workflow Extension ビルドガイド

## 必要環境
- macOS 13 (Ventura) 以上
- Xcode 15 以上
- Apple Developer Program 登録（年額 $99）
- Final Cut Pro (テスト用)

## セットアップ手順

### 1. Xcode プロジェクト作成
```
File > New > Project
  → macOS > App（ホストアプリ。Extensionを包むためのシェル）
  プロダクト名: EditClone
  Bundle ID: com.editclone.fcp-host
```

### 2. Extension ターゲット追加
```
File > New > Target
  → macOS > Workflow Extension
  プロダクト名: EditCloneExtension
  Bundle ID: com.editclone.fcp-extension
```

### 3. ファイルのコピー
- `EditCloneExtension.swift` → EditCloneExtension ターゲットに追加
- `Info.plist` → EditCloneExtension の Info.plist を置き換え

### 4. 署名設定
- Signing & Capabilities で Apple Developer アカウントを選択
- Hardened Runtime を有効化
- com.apple.security.network.client を有効化

### 5. ローカルテスト
```bash
# ビルド
xcodebuild -scheme EditClone -configuration Debug

# FCP に Extension をインストール（開発用）
open /Applications/Final Cut Pro.app
# FCP: Window > Extensions > EditClone
```

### 6. App Store Connect 申請
```
1. Xcode > Product > Archive
2. Organizer > Distribute App
3. Mac App Store を選択
4. App Store Connect でアプリ情報を入力
5. 審査提出（通常1〜3ヶ月）
```

## 申請カテゴリ
- Primary: Productivity
- Secondary: Video

## 必要な Apple 審査情報
- App説明 (日本語・英語)
- スクリーンショット (macOS: 1280x800 または 1440x900)
- プライバシーポリシー URL

## 参考リンク
- [FCP Workflow Extensions Guide](https://developer.apple.com/documentation/professional_video_applications)
- [App Store Connect](https://appstoreconnect.apple.com)
