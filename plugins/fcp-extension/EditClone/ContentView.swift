import SwiftUI

struct ContentView: View {
    // 本番デプロイURLに合わせて変更すること
    private let baseURL = "https://frontend-six-bice-51.vercel.app"

    var body: some View {
        EditCloneWebView(url: URL(string: "\(baseURL)/ja/dashboard?plugin=fcp")!)
            .ignoresSafeArea()
            .overlay(alignment: .top) {
                HStack(spacing: 8) {
                    Image(systemName: "film")
                        .foregroundStyle(.white)
                    Text("EditClone")
                        .font(.headline)
                        .foregroundStyle(.white)
                    Spacer()
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(Color.black.opacity(0.85))
            }
    }
}
