#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/dist/Hermes Chat Viewer.app"
CONTENTS="$APP/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
ICON_SOURCE="$ROOT/assets/app-icon.jpeg"
ICON_TIFF="$ROOT/dist/AppIcon.tiff"

rm -rf "$APP"
mkdir -p "$MACOS" "$RESOURCES"

swiftc \
  "$ROOT/macos/main.swift" \
  "$ROOT/macos/HermesChatViewer.swift" \
  -o "$MACOS/HermesChatViewer" \
  -framework Cocoa

cp "$ROOT/macos/Info.plist" "$CONTENTS/Info.plist"
cp "$ROOT/server.py" "$RESOURCES/server.py"
cp "$ROOT/index.html" "$RESOURCES/index.html"

if [[ -f "$ICON_SOURCE" ]]; then
  sips -s format tiff -z 512 512 "$ICON_SOURCE" --out "$ICON_TIFF" >/dev/null
  tiff2icns "$ICON_TIFF" "$RESOURCES/AppIcon.icns"
  rm -f "$ICON_TIFF"
fi

chmod +x "$MACOS/HermesChatViewer"

echo "Built: $APP"
echo "Open with: open '$APP'"
