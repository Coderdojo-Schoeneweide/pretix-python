#!/bin/bash
set -e

echo "Installing pretix…"

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$PROJECT_DIR/run.sh"
TARGET="$HOME/.local/bin/pretix"

sed "s|^PROJ=.*|PROJ=\"$PROJECT_DIR\"|" "$SRC" > "$TARGET"

chmod +x "$TARGET"

echo "Installed as: $TARGET"
echo "Run with: pretix r"
