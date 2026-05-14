#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/dist/Hermes Chat Viewer.app"
CONTENTS="$APP/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

rm -rf "$APP"
mkdir -p "$MACOS" "$RESOURCES"

swiftc \
  -parse-as-library \
  "$ROOT/macos/HermesChatViewer.swift" \
  -o "$MACOS/HermesChatViewer" \
  -framework Cocoa

cp "$ROOT/macos/Info.plist" "$CONTENTS/Info.plist"
cp "$ROOT/server.py" "$RESOURCES/server.py"
cp "$ROOT/index.html" "$RESOURCES/index.html"

chmod +x "$MACOS/HermesChatViewer"

echo "Built: $APP"
echo "Open with: open '$APP'"
