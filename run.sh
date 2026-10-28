#!/bin/sh
# Usage: ./run.sh CHANNEL_URL "quote" [ytsearch.py options]
# Creates a local venv with yt-dlp on first use.
cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q yt-dlp; }
exec .venv/bin/python ytsearch.py "$@"
