// EditClone — Final Cut Pro Workflow Extension
// ビルド要件: macOS 13+, Xcode 15+, Apple Developer Program
// FCP Extension API: https://developer.apple.com/documentation/professional_video_applications

import Foundation
import AppKit
import WebKit
import AVFoundation

// MARK: - Extension Principal Class

/// FCP から呼び出されるエクステンションのエントリポイント。
/// Info.plist の NSExtensionPrincipalClass に指定すること。
@objc(EditCloneExtension)
class EditCloneExtension: NSObject {

    private var windowController: EditCloneWindowController?

    @objc func showWindow() {
        if windowController == nil {
            windowController = EditCloneWindowController()
        }
        windowController?.showWindow(nil)
        windowController?.window?.makeKeyAndOrderFront(nil)
    }
}

// MARK: - Window Controller

class EditCloneWindowController: NSWindowController, WKNavigationDelegate, WKScriptMessageHandler {

    private var webView: WKWebView!
    private let apiBase = "https://editclone-production.up.railway.app"
    private let webBase = "https://editclone.vercel.app"

    override func windowDidLoad() {
        super.windowDidLoad()
        window?.title = "EditClone"
        window?.setContentSize(NSSize(width: 400, height: 640))
        window?.minSize = NSSize(width: 320, height: 480)
    }

    convenience init() {
        let config = WKWebViewConfiguration()
        let contentController = WKUserContentController()

        // ブリッジ検出スクリプト + FCP モード設定
        let bridgeScript = WKUserScript(
            source: "window.editcloneBridge = true; window.editcloneNLE = 'fcp';",
            injectionTime: .atDocumentStart,
            forMainFrameOnly: true
        )
        contentController.addUserScript(bridgeScript)
        config.userContentController = contentController

        let webView = WKWebView(frame: .zero, configuration: config)

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 400, height: 640),
            styleMask: [.titled, .closable, .resizable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        window.contentView = webView

        self.init(window: window)
        self.webView = webView

        // JS → Swift メッセージハンドラ登録
        contentController.add(self, name: "editclone")
        webView.navigationDelegate = self

        // nle=fcp パラメーターをつけて Web アプリを読み込む
        var comps = URLComponents(string: "\(webBase)/ja/dashboard")!
        comps.queryItems = [URLQueryItem(name: "nle", value: "fcp")]
        if let url = comps.url {
            webView.load(URLRequest(url: url))
        }
    }

    // MARK: WKScriptMessageHandler

    /// JS から postMessage("editclone", { action: "importFCPXML", url: "...", filename: "...", token: "..." }) が呼ばれる
    func userContentController(
        _ userContentController: WKUserContentController,
        didReceive message: WKScriptMessage
    ) {
        guard
            message.name == "editclone",
            let body = message.body as? [String: Any],
            let action = body["action"] as? String
        else { return }

        switch action {
        case "importFCPXML":
            guard let urlStr = body["url"] as? String,
                  let url = URL(string: urlStr) else { return }
            let token = body["token"] as? String
            let filename = body["filename"] as? String
            downloadAndImportFCPXML(from: url, filename: filename, token: token)

        case "openExternal":
            if let urlStr = body["url"] as? String, let url = URL(string: urlStr) {
                NSWorkspace.shared.open(url)
            }

        default:
            break
        }
    }

    // MARK: FCPXML Download

    private func downloadAndImportFCPXML(from url: URL, filename: String?, token: String?) {
        sendStatusToJS("FCPXMLをダウンロード中...")

        var request = URLRequest(url: url)
        // 認証トークンがある場合は Authorization ヘッダーをセット
        if let token = token, !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let task = URLSession.shared.downloadTask(with: request) { [weak self] localURL, response, error in
            guard let self = self else { return }

            if let error = error {
                self.sendStatusToJS("❌ ダウンロードエラー: \(error.localizedDescription)")
                return
            }

            // HTTP エラー確認（401 Unauthorized など）
            if let http = response as? HTTPURLResponse, http.statusCode != 200 {
                self.sendStatusToJS("❌ サーバーエラー: HTTP \(http.statusCode)")
                return
            }

            guard let localURL = localURL else {
                self.sendStatusToJS("❌ ダウンロード失敗")
                return
            }

            let destName = filename ?? "editclone.fcpxml"
            let destURL = FileManager.default.temporaryDirectory
                .appendingPathComponent(destName)

            try? FileManager.default.removeItem(at: destURL)
            do {
                try FileManager.default.moveItem(at: localURL, to: destURL)
            } catch {
                self.sendStatusToJS("❌ ファイル保存エラー: \(error.localizedDescription)")
                return
            }

            DispatchQueue.main.async {
                self.importFCPXMLFile(at: destURL)
            }
        }
        task.resume()
    }

    // MARK: FCPXML Import into FCP

    private func importFCPXMLFile(at url: URL) {
        sendStatusToJS("Final Cut Pro にインポート中...")

        // .fcpxml は FCP がデフォルトハンドラーとして登録されている。
        // NSWorkspace.open() で FCP が起動（または前面に来て）インポートダイアログが表示される。
        let opened = NSWorkspace.shared.open(url)
        if opened {
            sendStatusToJS("✅ FCP にインポートしました！ライブラリを選択してください。")
        } else {
            // フォールバック: Finder でファイルをハイライト → 手動ドラッグ&ドロップを促す
            NSWorkspace.shared.activateFileViewerSelecting([url])
            sendStatusToJS("⚠️ FCP を開けませんでした。Finder 内のファイルを FCP にドラッグしてください。")
        }
    }

    // MARK: JS Bridge Helpers

    private func sendStatusToJS(_ message: String) {
        let escaped = message
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
        let js = "window.dispatchEvent(new CustomEvent('editclone-status', { detail: { message: \"\(escaped)\" } }));"
        DispatchQueue.main.async { [weak self] in
            self?.webView.evaluateJavaScript(js)
        }
    }
}
