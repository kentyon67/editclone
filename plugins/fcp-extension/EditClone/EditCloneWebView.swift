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

        let config = WKWebViewConfiguration()
        config.userContentController = contentController
        // Allow localStorage / sessionStorage
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
                guard
                    let urlString = body["url"] as? String,
                    let downloadURL = URL(string: urlString)
                else { return }
                let filename = (body["filename"] as? String) ?? "editclone_project.zip"
                downloadAndSave(from: downloadURL, suggestedName: filename)

            default:
                break
            }
        }

        // ZIP をダウンロードして保存ダイアログを表示する
        private func downloadAndSave(from url: URL, suggestedName: String) {
            URLSession.shared.dataTask(with: url) { data, _, error in
                guard let data = data, error == nil else { return }

                let tmpURL = FileManager.default.temporaryDirectory
                    .appendingPathComponent(suggestedName)
                try? data.write(to: tmpURL)

                DispatchQueue.main.async {
                    let savePanel = NSSavePanel()
                    savePanel.nameFieldStringValue = suggestedName
                    savePanel.allowedContentTypes = [.zip]
                    savePanel.message = "FCPXMLとメディアの保存先を選んでください"

                    if savePanel.runModal() == .OK, let dest = savePanel.url {
                        try? FileManager.default.removeItem(at: dest)
                        try? FileManager.default.copyItem(at: tmpURL, to: dest)
                        // Final Cut Pro で開く
                        NSWorkspace.shared.open(dest)
                    }
                }
            }.resume()
        }

        // 外部リンクをデフォルトブラウザで開く
        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            if navigationAction.navigationType == .linkActivated,
               let url = navigationAction.request.url,
               !url.absoluteString.contains("frontend-six-bice-51.vercel.app") {
                NSWorkspace.shared.open(url)
                decisionHandler(.cancel)
            } else {
                decisionHandler(.allow)
            }
        }
    }
}
