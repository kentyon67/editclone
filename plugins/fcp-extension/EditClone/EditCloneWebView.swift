import SwiftUI
import WebKit
import AppKit

/// WKWebView を SwiftUI から使うためのラッパー。
/// JavaScript → Swift の "editclone" メッセージハンドラを登録し、
/// FCPXML インポート・AI 再編集・スタイルプロファイル切替をネイティブで処理する。
struct EditCloneWebView: NSViewRepresentable {
    let url: URL

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeNSView(context: Context) -> WKWebView {
        let contentController = WKUserContentController()
        contentController.add(context.coordinator, name: "editclone")

        // FCP 内であることをウェブアプリに通知 + エージェント機能を有効化
        let bridgeScript = WKUserScript(
            source: """
            window.editcloneBridge = true;
            window.editcloneNLE = 'fcp';
            window.editcloneAgent = true;
            """,
            injectionTime: .atDocumentStart,
            forMainFrameOnly: true
        )
        contentController.addUserScript(bridgeScript)

        let config = WKWebViewConfiguration()
        config.userContentController = contentController
        config.websiteDataStore = .default()

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        context.coordinator.webView = webView
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {}

    // MARK: - Coordinator

    class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler {

        weak var webView: WKWebView?
        private var pollingTimer: Timer?
        private var pollingJobId: String?

        func userContentController(
            _ userContentController: WKUserContentController,
            didReceive message: WKScriptMessage
        ) {
            guard
                let body = message.body as? [String: Any],
                let action = body["action"] as? String
            else { return }

            switch action {

            // FCPXML を直接インポート（認証付き）
            case "importFCPXML":
                if let jobId = body["jobId"] as? String,
                   let token = body["token"] as? String,
                   let apiBase = body["apiBase"] as? String {
                    importFCPXMLWithAuth(jobId: jobId, token: token, apiBase: apiBase)
                } else if let urlString = body["url"] as? String,
                          let downloadURL = URL(string: urlString) {
                    let filename = (body["filename"] as? String) ?? "editclone_project.fcpxml"
                    downloadAndOpen(from: downloadURL, filename: filename, authToken: nil)
                }

            // AI エージェント編集: 指示を送り → ポーリング → 完了したら自動インポート
            case "agentEdit":
                if let jobId = body["jobId"] as? String,
                   let prompt = body["prompt"] as? String,
                   let token = body["token"] as? String,
                   let apiBase = body["apiBase"] as? String {
                    startAgentEdit(jobId: jobId, prompt: prompt, token: token, apiBase: apiBase)
                }

            // ジョブの詳細（カット・セグメント）を取得してウェブアプリに返す
            case "getJobDetails":
                if let jobId = body["jobId"] as? String,
                   let token = body["token"] as? String,
                   let apiBase = body["apiBase"] as? String {
                    fetchJobDetails(jobId: jobId, token: token, apiBase: apiBase)
                }

            // スタイルプロファイル一覧を取得してウェブアプリに返す
            case "getStyleProfiles":
                if let token = body["token"] as? String,
                   let apiBase = body["apiBase"] as? String {
                    fetchStyleProfiles(token: token, apiBase: apiBase)
                }

            // スタイルプロファイルをアクティブに設定
            case "activateStyleProfile":
                if let profileId = body["profileId"] as? String,
                   let token = body["token"] as? String,
                   let apiBase = body["apiBase"] as? String {
                    activateProfile(profileId: profileId, token: token, apiBase: apiBase)
                }

            // プロジェクトリビジョンをサーバーに送信（NLE での変更を学習）
            case "sendRevision":
                if let projectId = body["projectId"] as? String,
                   let token = body["token"] as? String,
                   let apiBase = body["apiBase"] as? String {
                    let notes = (body["notes"] as? String) ?? ""
                    let metadata = (body["metadata"] as? [String: Any]) ?? [:]
                    sendRevision(projectId: projectId, notes: notes, metadata: metadata,
                                 token: token, apiBase: apiBase)
                }

            default:
                break
            }
        }

        // MARK: - FCPXML インポート（ZIP展開 + パス書き換え）

        private func importFCPXMLWithAuth(jobId: String, token: String, apiBase: String) {
            // ZIP全体をダウンロードしてメディアも一緒に展開する
            guard let url = URL(string: "\(apiBase)/jobs/\(jobId)/download") else { return }
            var request = URLRequest(url: url, timeoutInterval: 180)
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

            notifyWebApp(event: "importStatus", payload: ["message": "プロジェクトをダウンロード中...", "success": true])

            URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
                guard let self = self else { return }
                guard let data = data,
                      let httpResp = response as? HTTPURLResponse,
                      (200...299).contains(httpResp.statusCode) else {
                    // フォールバック: FCPXML のみダウンロード（メディアはオフライン）
                    self.importFCPXMLOnly(jobId: jobId, token: token, apiBase: apiBase)
                    return
                }

                let fm = FileManager.default
                let tmpDir = fm.temporaryDirectory.appendingPathComponent("editclone_\(jobId)")
                try? fm.removeItem(at: tmpDir)
                try? fm.createDirectory(at: tmpDir, withIntermediateDirectories: true)
                let zipPath = tmpDir.appendingPathComponent("project.zip")
                guard (try? data.write(to: zipPath)) != nil else {
                    self.importFCPXMLOnly(jobId: jobId, token: token, apiBase: apiBase)
                    return
                }

                self.notifyWebApp(event: "importStatus", payload: ["message": "ファイルを展開中...", "success": true])

                // /usr/bin/unzip で展開
                let extractDir = tmpDir.appendingPathComponent("extracted")
                let process = Process()
                process.executableURL = URL(fileURLWithPath: "/usr/bin/unzip")
                process.arguments = ["-o", zipPath.path, "-d", extractDir.path]
                do {
                    try process.run()
                    process.waitUntilExit()
                } catch {
                    self.importFCPXMLOnly(jobId: jobId, token: token, apiBase: apiBase)
                    return
                }

                // FCPXML を探す
                guard let fcpxmlURL = self.findFile(in: extractDir, extension: "fcpxml"),
                      var fcpxmlContent = try? String(contentsOf: fcpxmlURL, encoding: .utf8) else {
                    self.importFCPXMLOnly(jobId: jobId, token: token, apiBase: apiBase)
                    return
                }

                // media ディレクトリを探してパスを絶対URLに書き換え
                if let mediaDir = self.findSubdir(named: "media", in: extractDir) {
                    // URLエンコード: スペース等をパーセントエンコード
                    let mediaPath = mediaDir.path
                        .addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? mediaDir.path
                    fcpxmlContent = fcpxmlContent
                        .replacingOccurrences(of: "./media/", with: "file://\(mediaPath)/")
                }

                // 書き換えた FCPXML を保存
                let outFcpxml = extractDir.appendingPathComponent("\(jobId)_relinked.fcpxml")
                guard (try? fcpxmlContent.write(to: outFcpxml, atomically: true, encoding: .utf8)) != nil else {
                    self.importFCPXMLOnly(jobId: jobId, token: token, apiBase: apiBase)
                    return
                }

                self.notifyWebApp(event: "importStatus", payload: [
                    "message": "Final Cut Pro でインポート中...", "success": true
                ])
                DispatchQueue.main.async {
                    self.openFCPXML(at: outFcpxml)
                    // 暗黙的学習: インポート完了 = 肯定的フィードバックとして自動記録
                    self.sendAutoRevision(jobId: jobId, token: token, apiBase: apiBase)
                }
            }.resume()
        }

        // MARK: - FCPXML のみインポート（ZIP展開失敗時のフォールバック）

        private func importFCPXMLOnly(jobId: String, token: String, apiBase: String) {
            guard let url = URL(string: "\(apiBase)/plugin/jobs/\(jobId)/fcpxml") else { return }
            var request = URLRequest(url: url, timeoutInterval: 60)
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

            URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
                guard let self = self else { return }
                if let error = error {
                    self.notifyWebApp(event: "importStatus", payload: [
                        "message": "ダウンロードエラー: \(error.localizedDescription)", "success": false
                    ])
                    return
                }
                guard let data = data,
                      let httpResp = response as? HTTPURLResponse,
                      httpResp.statusCode == 200 else {
                    let code = (response as? HTTPURLResponse)?.statusCode ?? 0
                    self.notifyWebApp(event: "importStatus", payload: [
                        "message": "API エラー: HTTP \(code)", "success": false
                    ])
                    return
                }
                let tmpURL = FileManager.default.temporaryDirectory
                    .appendingPathComponent("\(jobId).fcpxml")
                try? data.write(to: tmpURL)
                DispatchQueue.main.async { self.openFCPXML(at: tmpURL) }
            }.resume()
        }

        // MARK: - ファイル・ディレクトリ検索ヘルパー

        private func findFile(in directory: URL, extension ext: String) -> URL? {
            guard let enumerator = FileManager.default.enumerator(
                at: directory, includingPropertiesForKeys: nil
            ) else { return nil }
            for case let url as URL in enumerator {
                if url.pathExtension == ext { return url }
            }
            return nil
        }

        private func findSubdir(named name: String, in directory: URL) -> URL? {
            guard let enumerator = FileManager.default.enumerator(
                at: directory,
                includingPropertiesForKeys: [.isDirectoryKey]
            ) else { return nil }
            for case let url as URL in enumerator {
                if url.lastPathComponent == name {
                    var isDir: ObjCBool = false
                    if FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir),
                       isDir.boolValue { return url }
                }
            }
            return nil
        }

        // MARK: - 暗黙的学習: インポート完了後に自動でリビジョン送信

        private func sendAutoRevision(jobId: String, token: String, apiBase: String) {
            guard let url = URL(string: "\(apiBase)/plugin/jobs/\(jobId)/details") else { return }
            var request = URLRequest(url: url, timeoutInterval: 15)
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

            URLSession.shared.dataTask(with: request) { [weak self] data, _, _ in
                guard let self = self,
                      let data = data,
                      let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let projectId = json["project_id"] as? String,
                      !projectId.isEmpty else { return }

                self.sendRevision(
                    projectId: projectId,
                    notes: "auto:fcp_import",
                    metadata: ["source": "fcp_extension", "job_id": jobId],
                    token: token,
                    apiBase: apiBase
                )
            }.resume()
        }

        // MARK: - FCPXML を FCP で開く

        private func openFCPXML(at url: URL) {
            let success = NSWorkspace.shared.open(url)
            if success {
                notifyWebApp(event: "importStatus", payload: [
                    "message": "Final Cut Pro でインポートしています...", "success": true
                ])
            } else {
                let savePanel = NSSavePanel()
                savePanel.nameFieldStringValue = url.lastPathComponent
                savePanel.allowedContentTypes = [.init(filenameExtension: "fcpxml")!]
                savePanel.message = "FCPXML の保存先を選んでください"
                if savePanel.runModal() == .OK, let dest = savePanel.url {
                    try? FileManager.default.removeItem(at: dest)
                    try? FileManager.default.copyItem(at: url, to: dest)
                    NSWorkspace.shared.activateFileViewerSelecting([dest])
                    notifyWebApp(event: "importStatus", payload: [
                        "message": "保存しました。FCP にドラッグ&ドロップしてください。", "success": true
                    ])
                }
            }
        }

        // MARK: - AI エージェント編集

        private func startAgentEdit(jobId: String, prompt: String, token: String, apiBase: String) {
            guard let url = URL(string: "\(apiBase)/plugin/jobs/\(jobId)/agent-edit") else { return }
            var request = URLRequest(url: url, timeoutInterval: 30)
            request.httpMethod = "POST"
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            let body = try? JSONSerialization.data(withJSONObject: ["prompt": prompt])
            request.httpBody = body

            notifyWebApp(event: "agentStatus", payload: [
                "status": "started", "message": "AI 編集を開始しました..."
            ])

            URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
                guard let self = self else { return }
                if let error = error {
                    self.notifyWebApp(event: "agentStatus", payload: [
                        "status": "error", "message": error.localizedDescription
                    ])
                    return
                }
                guard let data = data,
                      let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let newJobId = json["job_id"] as? String else {
                    self.notifyWebApp(event: "agentStatus", payload: [
                        "status": "error", "message": "レスポンス解析に失敗しました"
                    ])
                    return
                }
                self.pollingJobId = newJobId
                DispatchQueue.main.async {
                    self.startPolling(jobId: newJobId, token: token, apiBase: apiBase)
                }
            }.resume()
        }

        // MARK: - ポーリング（メインスレッドで Timer 使用）

        private func startPolling(jobId: String, token: String, apiBase: String) {
            stopPolling()
            var attempts = 0
            pollingTimer = Timer.scheduledTimer(withTimeInterval: 3.0, repeats: true) { [weak self] _ in
                guard let self = self else { return }
                attempts += 1
                if attempts > 120 {
                    self.stopPolling()
                    self.notifyWebApp(event: "agentStatus", payload: [
                        "status": "error", "message": "タイムアウトしました"
                    ])
                    return
                }
                self.pollJob(jobId: jobId, token: token, apiBase: apiBase)
            }
        }

        private func stopPolling() {
            pollingTimer?.invalidate()
            pollingTimer = nil
        }

        private func pollJob(jobId: String, token: String, apiBase: String) {
            guard let url = URL(string: "\(apiBase)/plugin/jobs/\(jobId)/poll") else { return }
            var request = URLRequest(url: url, timeoutInterval: 10)
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

            URLSession.shared.dataTask(with: request) { [weak self] data, _, error in
                guard let self = self, let data = data,
                      let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
                let status = json["status"] as? String ?? ""
                let progress = json["progress"] as? String ?? ""

                self.notifyWebApp(event: "agentStatus", payload: [
                    "status": "processing", "jobId": jobId, "progress": progress
                ])

                if status == "completed" {
                    self.stopPolling()
                    self.notifyWebApp(event: "agentStatus", payload: [
                        "status": "completed", "jobId": jobId,
                        "message": "AI 編集が完了しました！"
                    ])
                    // 完了したら自動的に FCPXML インポート
                    DispatchQueue.main.async {
                        self.importFCPXMLWithAuth(jobId: jobId, token: token, apiBase: apiBase)
                    }
                } else if status == "failed" {
                    self.stopPolling()
                    let errMsg = json["error"] as? String ?? "不明なエラー"
                    self.notifyWebApp(event: "agentStatus", payload: [
                        "status": "error", "message": "処理に失敗しました: \(errMsg)"
                    ])
                }
            }.resume()
        }

        // MARK: - ジョブ詳細取得

        private func fetchJobDetails(jobId: String, token: String, apiBase: String) {
            guard let url = URL(string: "\(apiBase)/plugin/jobs/\(jobId)/details") else { return }
            var request = URLRequest(url: url, timeoutInterval: 15)
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

            URLSession.shared.dataTask(with: request) { [weak self] data, _, error in
                guard let self = self else { return }
                if let data = data,
                   let json = try? JSONSerialization.jsonObject(with: data) {
                    self.notifyWebApp(event: "jobDetails", payload: ["details": json])
                } else {
                    self.notifyWebApp(event: "jobDetails", payload: [
                        "error": error?.localizedDescription ?? "取得に失敗しました"
                    ])
                }
            }.resume()
        }

        // MARK: - スタイルプロファイル一覧

        private func fetchStyleProfiles(token: String, apiBase: String) {
            guard let url = URL(string: "\(apiBase)/plugin/style-profiles") else { return }
            var request = URLRequest(url: url, timeoutInterval: 15)
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

            URLSession.shared.dataTask(with: request) { [weak self] data, _, error in
                guard let self = self else { return }
                if let data = data,
                   let json = try? JSONSerialization.jsonObject(with: data) {
                    self.notifyWebApp(event: "styleProfiles", payload: ["data": json])
                } else {
                    self.notifyWebApp(event: "styleProfiles", payload: [
                        "error": error?.localizedDescription ?? "取得に失敗しました"
                    ])
                }
            }.resume()
        }

        // MARK: - スタイルプロファイルをアクティブ化

        private func activateProfile(profileId: String, token: String, apiBase: String) {
            guard let url = URL(string: "\(apiBase)/plugin/style-profiles/\(profileId)/activate") else { return }
            var request = URLRequest(url: url, timeoutInterval: 15)
            request.httpMethod = "POST"
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = "{}".data(using: .utf8)

            URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
                guard let self = self else { return }
                let ok = (response as? HTTPURLResponse)?.statusCode == 200
                self.notifyWebApp(event: "profileActivated", payload: [
                    "profileId": profileId,
                    "success": ok,
                    "message": ok ? "スタイルを変更しました" : "変更に失敗しました"
                ])
            }.resume()
        }

        // MARK: - リビジョン送信（Plugin → サーバー学習ループ）

        private func sendRevision(
            projectId: String, notes: String, metadata: [String: Any],
            token: String, apiBase: String
        ) {
            guard let url = URL(string: "\(apiBase)/projects/\(projectId)/revisions") else { return }
            var request = URLRequest(url: url, timeoutInterval: 15)
            request.httpMethod = "POST"
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            let body: [String: Any] = ["notes": notes, "metadata": metadata]
            request.httpBody = try? JSONSerialization.data(withJSONObject: body)

            URLSession.shared.dataTask(with: request) { [weak self] data, response, _ in
                guard let self = self else { return }
                let ok = (response as? HTTPURLResponse)?.statusCode == 200
                self.notifyWebApp(event: "revisionSent", payload: [
                    "success": ok,
                    "message": ok ? "フィードバックを送信しました" : "送信に失敗しました"
                ])
            }.resume()
        }

        // MARK: - ZIP ダウンロード（後方互換）

        private func downloadAndOpen(from url: URL, filename: String, authToken: String?) {
            var request = URLRequest(url: url, timeoutInterval: 120)
            if let token = authToken {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }
            URLSession.shared.dataTask(with: request) { [weak self] data, _, error in
                guard let data = data, error == nil else { return }
                let tmpURL = FileManager.default.temporaryDirectory
                    .appendingPathComponent(filename)
                try? data.write(to: tmpURL)
                DispatchQueue.main.async {
                    let savePanel = NSSavePanel()
                    savePanel.nameFieldStringValue = filename
                    savePanel.message = "保存先を選んでください"
                    if savePanel.runModal() == .OK, let dest = savePanel.url {
                        try? FileManager.default.removeItem(at: dest)
                        try? FileManager.default.copyItem(at: tmpURL, to: dest)
                        NSWorkspace.shared.open(dest)
                    }
                }
            }.resume()
        }

        // MARK: - Web アプリへのイベント通知

        /// CustomEvent を dispatch して JS 側がリッスンできる形で通知する。
        /// event: イベント名（"importStatus" | "agentStatus" | "jobDetails" | "styleProfiles" | ...）
        /// payload: JSON シリアライズ可能な辞書
        func notifyWebApp(event: String, payload: [String: Any]) {
            guard let jsonData = try? JSONSerialization.data(withJSONObject: payload),
                  let jsonStr = String(data: jsonData, encoding: .utf8) else { return }
            let escapedEvent = event
                .replacingOccurrences(of: "\\", with: "\\\\")
                .replacingOccurrences(of: "'", with: "\\'")
            let js = """
            window.dispatchEvent(new CustomEvent('editclone-\(escapedEvent)', {
              detail: \(jsonStr)
            }));
            """
            DispatchQueue.main.async { [weak self] in
                self?.webView?.evaluateJavaScript(js, completionHandler: nil)
            }
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
               !host.contains("localhost"),
               !host.contains("railway.app") {
                NSWorkspace.shared.open(url)
                decisionHandler(.cancel)
            } else {
                decisionHandler(.allow)
            }
        }
    }
}
