import SwiftUI
import WebKit
import AppKit

/// WKWebView を SwiftUI から使うためのラッパー。
/// JavaScript → Swift の "editclone" メッセージハンドラを登録し、
/// FCPXML インポート要求をネイティブで処理する。
struct EditCloneWebView: NSViewRepresentable {
    let url: URL

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeNSView(context: Context) -> WKWebView {
        let contentController = WKUserContentController()
        contentController.add(context.coordinator, name: "editclone")

        // window.editcloneBridge = true を inject して FCP 内であることをウェブアプリに通知
        let bridgeScript = WKUserScript(
            source: "window.editcloneBridge = true; window.editcloneNLE = 'fcp';",
            injectionTime: .atDocumentStart,
            forMainFrameOnly: true
        )
        contentController.addUserScript(bridgeScript)

        let config = WKWebViewConfiguration()
        config.userContentController = contentController
        config.websiteDataStore = .default()

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {}

    // MARK: - Coordinator

    class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler {

        // JavaScript から届くメッセージを処理する
        func userContentController(
            _ userContentController: WKUserContentController,
            didReceive message: WKScriptMessage
        ) {
            guard
                let body = message.body as? [String: Any],
                let action = body["action"] as? String
            else { return }

            switch action {
            case "importFCPXML":
                // 新プロトコル: jobId + token + apiBase でセキュアにダウンロード
                if let jobId = body["jobId"] as? String,
                   let token = body["token"] as? String,
                   let apiBase = body["apiBase"] as? String {
                    importFCPXMLWithAuth(jobId: jobId, token: token, apiBase: apiBase)
                } else if let urlString = body["url"] as? String,
                          let downloadURL = URL(string: urlString) {
                    // 後方互換: 直接 URL が渡された場合
                    let filename = (body["filename"] as? String) ?? "editclone_project.zip"
                    downloadAndSave(from: downloadURL, suggestedName: filename, authToken: nil)
                }

            default:
                break
            }
        }

        // MARK: - FCPXML ダウンロード（認証ヘッダー付き）

        private func importFCPXMLWithAuth(jobId: String, token: String, apiBase: String) {
            guard let url = URL(string: "\(apiBase)/plugin/jobs/\(jobId)/fcpxml") else { return }

            var request = URLRequest(url: url, timeoutInterval: 60)
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

            URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
                guard let self = self else { return }

                if let error = error {
                    self.notifyWebApp(message: "ダウンロードエラー: \(error.localizedDescription)", success: false)
                    return
                }
                guard let data = data,
                      let httpResp = response as? HTTPURLResponse,
                      httpResp.statusCode == 200 else {
                    let code = (response as? HTTPURLResponse)?.statusCode ?? 0
                    self.notifyWebApp(message: "API エラー: HTTP \(code)", success: false)
                    return
                }

                let tmpURL = FileManager.default.temporaryDirectory
                    .appendingPathComponent("\(jobId).fcpxml")
                try? data.write(to: tmpURL)

                DispatchQueue.main.async {
                    self.openFCPXML(at: tmpURL)
                }
            }.resume()
        }

        // MARK: - FCPXML を FCP で開く

        private func openFCPXML(at url: URL) {
            // .fcpxml はシステムで FCP に関連付けられているため open で起動できる
            let success = NSWorkspace.shared.open(url)
            if success {
                notifyWebApp(message: "Final Cut Pro でインポートしています...", success: true)
            } else {
                // FCP が見つからない場合は保存ダイアログにフォールバック
                let savePanel = NSSavePanel()
                savePanel.nameFieldStringValue = url.lastPathComponent
                savePanel.allowedContentTypes = [.init(filenameExtension: "fcpxml")!]
                savePanel.message = "FCPXML の保存先を選んでください"

                if savePanel.runModal() == .OK, let dest = savePanel.url {
                    try? FileManager.default.removeItem(at: dest)
                    try? FileManager.default.copyItem(at: url, to: dest)
                    NSWorkspace.shared.activateFileViewerSelecting([dest])
                    notifyWebApp(message: "ファイルを保存しました。FCP にドラッグ&ドロップしてください。", success: true)
                }
            }
        }

        // MARK: - ZIP ダウンロード（後方互換）

        private func downloadAndSave(from url: URL, suggestedName: String, authToken: String?) {
            var request = URLRequest(url: url, timeoutInterval: 120)
            if let token = authToken {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            URLSession.shared.dataTask(with: request) { [weak self] data, _, error in
                guard let data = data, error == nil else { return }
                let tmpURL = FileManager.default.temporaryDirectory
                    .appendingPathComponent(suggestedName)
                try? data.write(to: tmpURL)

                DispatchQueue.main.async {
                    let savePanel = NSSavePanel()
                    savePanel.nameFieldStringValue = suggestedName
                    savePanel.message = "FCPXML とメディアの保存先を選んでください"

                    if savePanel.runModal() == .OK, let dest = savePanel.url {
                        try? FileManager.default.removeItem(at: dest)
                        try? FileManager.default.copyItem(at: tmpURL, to: dest)
                        NSWorkspace.shared.open(dest)
                    }
                }
            }.resume()
        }

        // MARK: - Web アプリへ結果通知

        private func notifyWebApp(message: String, success: Bool) {
            // WKWebView への参照は Coordinator が直接持たないため CustomEvent で通知
            // EditCloneWebView の makeNSView で生成した webView に対して evalJS を送る方法は
            // NSApplication の delegate 等経由が必要なため、ここではログのみ。
            // フロントエンド側は window.addEventListener('editclone-status') で受け取る。
            print("[EditClone FCP] \(success ? "✓" : "✗") \(message)")
        }

        // MARK: - ナビゲーション

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            if navigationAction.navigationType == .linkActivated,
               let url = navigationAction.request.url,
               let host = url.host,
               !host.contains("vercel.app"),
               !host.contains("localhost") {
                NSWorkspace.shared.open(url)
                decisionHandler(.cancel)
            } else {
                decisionHandler(.allow)
            }
        }
    }
}
