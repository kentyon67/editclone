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
        // WKWebView with JS bridge
        let config = WKWebViewConfiguration()
        let contentController = WKUserContentController()

        // Inject bridge detection script
        let bridgeScript = WKUserScript(
            source: "window.editcloneBridge = true;",
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

        // Register message handler for JS → Swift communication
        contentController.add(self, name: "editclone")
        webView.navigationDelegate = self

        // Load the EditClone web app in FCP plugin mode
        var comps = URLComponents(string: "\(webBase)/ja/dashboard")!
        comps.queryItems = [URLQueryItem(name: "nle", value: "fcp")]
        if let url = comps.url {
            webView.load(URLRequest(url: url))
        }
    }

    // MARK: WKScriptMessageHandler

    /// JS から postMessage("editclone", { action: "importFCPXML", url: "...", filename: "..." }) が呼ばれる
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
            downloadAndImportFCPXML(from: url, filename: body["filename"] as? String)

        case "openExternal":
            if let urlStr = body["url"] as? String, let url = URL(string: urlStr) {
                NSWorkspace.shared.open(url)
            }

        default:
            break
        }
    }

    // MARK: FCPXML Import

    private func downloadAndImportFCPXML(from url: URL, filename: String?) {
        sendStatusToJS("FCPXMLをダウンロード中...")

        let task = URLSession.shared.downloadTask(with: url) { [weak self] localURL, _, error in
            guard let self = self else { return }
            if let error = error {
                self.sendStatusToJS("エラー: \(error.localizedDescription)")
                return
            }
            guard let localURL = localURL else {
                self.sendStatusToJS("ダウンロード失敗")
                return
            }

            let destURL = FileManager.default.temporaryDirectory
                .appendingPathComponent(filename ?? "editclone.fcpxml")

            try? FileManager.default.removeItem(at: destURL)
            do {
                try FileManager.default.moveItem(at: localURL, to: destURL)
            } catch {
                self.sendStatusToJS("ファイル保存エラー: \(error.localizedDescription)")
                return
            }

            DispatchQueue.main.async {
                self.importFCPXMLFile(at: destURL)
            }
        }
        task.resume()
    }

    private func importFCPXMLFile(at url: URL) {
        sendStatusToJS("Final Cut Pro にインポート中...")

        // FCP Workflow Extension API でインポートをトリガー
        // (実際のFCP Extension APIはApple Frameworkを使用)
        // ここではFCPXMLをFCPに渡すためのURLスキームを使用
        let fcpURL = URL(string: "fcpxml://open?path=\(url.path.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")")
        if let fcpURL = fcpURL {
            NSWorkspace.shared.open(fcpURL)
        }

        // フォールバック: Finderでファイルを表示し、ユーザーにドラッグ&ドロップを促す
        NSWorkspace.shared.activateFileViewerSelecting([url])
        sendStatusToJS("インポート完了！ FCPにドラッグ&ドロップしてください。")
    }

    // MARK: JS Bridge helpers

    private func sendStatusToJS(_ message: String) {
        let escaped = message.replacingOccurrences(of: "\"", with: "\\\"")
        let js = "window.dispatchEvent(new CustomEvent('editclone-status', { detail: { message: \"\(escaped)\" } }));"
        DispatchQueue.main.async { [weak self] in
            self?.webView.evaluateJavaScript(js)
        }
    }
}
