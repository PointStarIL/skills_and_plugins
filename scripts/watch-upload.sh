#!/bin/bash
# watch-upload.sh — inotifywait daemon: watches upload/ and calls process-upload.sh
# Runs as a systemd service (skills-upload-watcher.service)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UPLOAD_DIR="$REPO_DIR/upload"
PROCESS="$REPO_DIR/scripts/process-upload.sh"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [watcher] $*"; }

log "Starting — watching $UPLOAD_DIR"

# Process any files left from previous runs (e.g. crash, restart)
for f in "$UPLOAD_DIR"/*.plugin "$UPLOAD_DIR"/*.skill; do
    [ -f "$f" ] && {
        log "Found leftover file: $(basename "$f") — processing"
        "$PROCESS" "$f" || log "ERROR processing $(basename "$f")"
    }
done

# Watch for new files written or moved into the folder
inotifywait -m -e close_write,moved_to --format '%w%f' "$UPLOAD_DIR" |
while IFS= read -r FILEPATH; do
    FILENAME="$(basename "$FILEPATH")"

    # Ignore hidden files and .gitkeep
    [[ "$FILENAME" == .* ]] && continue
    [ -f "$FILEPATH" ]      || continue

    # Brief pause to ensure the write is fully flushed
    sleep 0.5

    log "Detected: $FILENAME"
    "$PROCESS" "$FILEPATH" || log "ERROR processing $FILENAME (see above)"
done
