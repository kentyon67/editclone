import SwiftUI

@main
struct EditCloneApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(minWidth: 360, minHeight: 640)
        }
        .windowResizability(.contentSize)
    }
}
