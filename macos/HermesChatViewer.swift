import Cocoa

@main
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem?
    private var serverProcess: Process?
    private let port = 8765

    private var viewerURL: URL {
        URL(string: "http://127.0.0.1:\(port)")!
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        setupMenu()
        startServer()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
            self.openViewer()
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        stopServer()
    }

    private func setupMenu() {
        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        item.button?.title = "⚕"
        item.button?.toolTip = "Hermes Chat Viewer"

        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "Open Viewer", action: #selector(openViewerAction), keyEquivalent: "o"))
        menu.addItem(NSMenuItem(title: "Restart Server", action: #selector(restartServerAction), keyEquivalent: "r"))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit", action: #selector(quitAction), keyEquivalent: "q"))
        item.menu = menu

        statusItem = item
    }

    private func startServer() {
        guard serverProcess?.isRunning != true else { return }
        guard let serverPath = Bundle.main.path(forResource: "server", ofType: "py") else {
            showAlert("server.py was not found inside the app bundle.")
            return
        }

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", serverPath, "--port", String(port)]
        process.currentDirectoryURL = Bundle.main.resourceURL
        process.standardOutput = Pipe()
        process.standardError = Pipe()

        do {
            try process.run()
            serverProcess = process
        } catch {
            showAlert("Could not start the local viewer server:\n\(error.localizedDescription)")
        }
    }

    private func stopServer() {
        guard let process = serverProcess else { return }
        if process.isRunning {
            process.terminate()
            DispatchQueue.global(qos: .utility).async {
                process.waitUntilExit()
            }
        }
        serverProcess = nil
    }

    private func showAlert(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "Hermes Chat Viewer"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.runModal()
    }

    @objc private func openViewerAction() {
        openViewer()
    }

    private func openViewer() {
        NSWorkspace.shared.open(viewerURL)
    }

    @objc private func restartServerAction() {
        stopServer()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
            self.startServer()
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                self.openViewer()
            }
        }
    }

    @objc private func quitAction() {
        stopServer()
        NSApp.terminate(nil)
    }
}
