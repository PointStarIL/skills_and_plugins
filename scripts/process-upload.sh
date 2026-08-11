#!/bin/bash
# process-upload.sh — process a single .plugin or .skill file from upload/
# Usage: process-upload.sh <absolute-path-to-file>
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLUGINS_DIR="$REPO_DIR/plugins"
MARKETPLACE_JSON="$REPO_DIR/.claude-plugin/marketplace.json"
MARKETPLACE_PY="$REPO_DIR/scripts/update-marketplace.py"

FILE="$1"
FILENAME="$(basename "$FILE")"
EXT="${FILENAME##*.}"
BASENAME="${FILENAME%.*}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "File received: $FILENAME"

# Validate extension
if [[ "$EXT" != "plugin" && "$EXT" != "skill" ]]; then
    log "ERROR: Unsupported extension .$EXT — expected .plugin or .skill"
    exit 1
fi

# Extract to temp dir
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

if ! unzip -q "$FILE" -d "$TMPDIR" 2>/dev/null; then
    log "ERROR: Failed to unzip $FILENAME — is it a valid zip archive?"
    exit 1
fi

# Determine plugin name: prefer name field in plugin.json, fall back to filename
PLUGIN_JSON="$TMPDIR/.claude-plugin/plugin.json"
if [ -f "$PLUGIN_JSON" ]; then
    PLUGIN_NAME="$(python3 -c "import json,sys; print(json.load(open('$PLUGIN_JSON'))['name'])" 2>/dev/null || echo "$BASENAME")"
    PLUGIN_DESC="$(python3 -c "import json,sys; print(json.load(open('$PLUGIN_JSON')).get('description',''))" 2>/dev/null || echo "")"
    PLUGIN_VER="$(python3  -c "import json,sys; print(json.load(open('$PLUGIN_JSON')).get('version','latest'))" 2>/dev/null || echo "latest")"
else
    PLUGIN_NAME="$BASENAME"
    PLUGIN_DESC=""
    PLUGIN_VER="latest"
fi

log "Plugin name: $PLUGIN_NAME  |  version: $PLUGIN_VER"

TARGET_DIR="$PLUGINS_DIR/$PLUGIN_NAME"

if [ -d "$TARGET_DIR" ]; then
    # ── UPDATE existing plugin ──────────────────────────────────────────────
    log "Mode: UPDATE (existing plugin found)"
    cp -r "$TMPDIR/." "$TARGET_DIR/"
    COMMIT_MSG="Update $PLUGIN_NAME to $PLUGIN_VER"
else
    # ── CREATE new plugin ───────────────────────────────────────────────────
    log "Mode: CREATE (new plugin)"
    mkdir -p "$TARGET_DIR"
    cp -r "$TMPDIR/." "$TARGET_DIR/"
    python3 "$MARKETPLACE_PY" "$MARKETPLACE_JSON" "$PLUGIN_NAME" "$PLUGIN_DESC"
    COMMIT_MSG="Add new plugin: $PLUGIN_NAME"
fi

# Remove the uploaded file now that content is copied
rm "$FILE"
log "Removed: $FILENAME from upload/"

# Git commit and push
cd "$REPO_DIR"
git add .

if git diff --cached --quiet; then
    log "Nothing changed after extraction — no commit needed"
    exit 0
fi

git commit -m "$COMMIT_MSG"
log "Committed: $COMMIT_MSG"

git push
log "Pushed to origin ✓"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
