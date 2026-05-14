import Cocoa

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem?
    private var serverProcess: Process?
    private var logHandle: FileHandle?
    private let port = 8765

    private var viewerURL: URL {
        URL(string: "http://127.0.0.1:\(port)")!
    }

    private var logURL: URL {
        let base = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/Hermes Chat Viewer", isDirectory: true)
        try? FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        return base.appendingPathComponent("server.log")
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
        if let iconURL = Bundle.main.url(forResource: "AppIcon", withExtension: "icns"),
           let image = NSImage(contentsOf: iconURL) {
            image.size = NSSize(width: 18, height: 18)
            item.button?.image = image
        } else {
            item.button?.title = "⚕"
        }
        item.button?.toolTip = "Hermes Chat Viewer"

        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "Open Viewer", action: #selector(openViewerAction), keyEquivalent: "o"))
        menu.addItem(NSMenuItem(title: "Restart Server", action: #selector(restartServerAction), keyEquivalent: "r"))
        menu.addItem(NSMenuItem(title: "Show Logs", action: #selector(showLogsAction), keyEquivalent: "l"))
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
        guard let pythonPath = findPython() else {
            showAlert("Could not find python3. Install Python or Homebrew Python, then restart the app.")
            return
        }

        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments = [serverPath, "--port", String(port)]
        process.currentDirectoryURL = Bundle.main.resourceURL
        let handle = openLog()
        process.standardOutput = handle
        process.standardError = handle

        do {
            try process.run()
            serverProcess = process
            appendLog("Started server with \(pythonPath) \(serverPath) --port \(port)\n")
        } catch {
            showAlert("Could not start the local viewer server:\n\(error.localizedDescription)")
            closeLog()
        }
    }

    private func findPython() -> String? {
        let candidates = [
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3"
        ]
        return candidates.first { FileManager.default.isExecutableFile(atPath: $0) }
    }

    private func openLog() -> FileHandle {
        let path = logURL.path
        if !FileManager.default.fileExists(atPath: path) {
            FileManager.default.createFile(atPath: path, contents: nil)
        }
        let handle = (try? FileHandle(forWritingTo: logURL)) ?? FileHandle.standardError
        _ = try? handle.seekToEnd()
        logHandle = handle
        appendLog("\n--- Hermes Chat Viewer \(Date()) ---\n")
        return handle
    }

    private func appendLog(_ text: String) {
        guard let data = text.data(using: .utf8) else { return }
        try? logHandle?.write(contentsOf: data)
    }

    private func closeLog() {
        try? logHandle?.close()
        logHandle = nil
    }

    private func stopServer() {
        guard let process = serverProcess else { return }
        if process.isRunning {
            process.terminate()
            DispatchQueue.global(qos: .utility).async {
                process.waitUntilExit()
                DispatchQueue.main.async {
                    self.closeLog()
                }
            }
        } else {
            closeLog()
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

    @objc private func showLogsAction() {
        NSWorkspace.shared.open(logURL)
    }

    @objc private func quitAction() {
        stopServer()
        NSApp.terminate(nil)
    }
}
