#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
	echo "Usage: $0 <video.mp4> [out_dir] [minutes]" >&2
	echo "Example: $0 ~/Movies/phim.mp4 ./chunks 5" >&2
	exit 1
fi

if ! command -v ffmpeg >/dev/null; then
	echo "Need ffmpeg in PATH" >&2
	exit 1
fi

INPUT=$1
OUT_DIR=${2:-"${INPUT%.*}_chunks"}
MINUTES=${3:-5}

if [[ ! -f $INPUT ]]; then
	echo "Missing file: $INPUT" >&2
	exit 1
fi

if ! [[ $MINUTES =~ ^[0-9]+$ ]] || [[ $MINUTES -lt 1 ]]; then
	echo "minutes must be a positive integer" >&2
	exit 1
fi

SECS=$((MINUTES * 60))
BASE=$(basename "${INPUT%.*}")
mkdir -p "$OUT_DIR"

echo "Split $INPUT -> $OUT_DIR/${BASE}_XXX.mp4 every ${MINUTES}m (copy, cut near keyframes)"
ffmpeg -hide_banner -y -i "$INPUT" \
	-c copy -map 0 \
	-f segment -segment_time "$SECS" -reset_timestamps 1 \
	"$OUT_DIR/${BASE}_%03d.mp4"

echo "Done:"
ls -lh "$OUT_DIR/${BASE}_"*.mp4
