#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8765}"
URL="http://127.0.0.1:${PORT}"

clear
echo "Hermes Chat Viewer"
echo "Project: $(pwd)"
echo
echo "Starting local server at ${URL}"
echo "Close this Terminal window or press Ctrl+C to stop."
echo

python3 server.py --port "${PORT}" --open

