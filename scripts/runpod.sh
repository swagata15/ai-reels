#!/usr/bin/env bash
# One-shot reel factory for a RunPod GPU pod (or any Ubuntu box with an NVIDIA GPU).
#
# In the pod's web terminal:
#   export GITHUB_TOKEN=github_pat_...      # only if the repo is private
#   curl -fsSL https://raw.githubusercontent.com/swagata15/ai-reels/main/scripts/runpod.sh | bash
#   (private repo: clone first, then: bash ai-reels/scripts/runpod.sh)
#
# Options (env vars): REELS="reels/*.json"  STORIES="stories/*.json"  JOBS=2  SAMPLES=64  BLENDER_VERSION=5.0.1
# Re-running only renders reels that aren't finished yet.
set -euo pipefail

REPO=${REPO:-swagata15/ai-reels}
WORK=${WORK:-/workspace}
REELS=${REELS:-reels/*.json}
JOBS=${JOBS:-2}
SAMPLES=${SAMPLES:-64}
BLENDER_VERSION=${BLENDER_VERSION:-5.0.1}
BLENDER_DIR=$WORK/blender
SUDO=$([ "$(id -u)" = 0 ] && echo "" || echo sudo)
t0=$(date +%s)

echo "==> GPU"; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || echo "WARNING: no NVIDIA GPU found"

echo "==> system packages"
$SUDO apt-get update -qq
$SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg git wget xz-utils zip python3 \
  libxi6 libxkbcommon0 libsm6 libxrender1 libxxf86vm1 libxfixes3 libgl1 libegl1 > /dev/null

python3 -c "import numpy" 2>/dev/null || python3 -m pip install -q numpy  # for generated sound effects

echo "==> project"
mkdir -p "$WORK" && cd "$WORK"
if [ -d ai-reels/.git ]; then
  git -C ai-reels pull -q
else
  url="https://github.com/$REPO.git"
  [ -n "${GITHUB_TOKEN:-}" ] && url="https://$GITHUB_TOKEN@github.com/$REPO.git"
  git clone -q --depth 1 "$url" ai-reels
fi
cd ai-reels

echo "==> blender $BLENDER_VERSION"
if [ ! -x "$BLENDER_DIR/blender" ]; then
  wget -q "https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" -O /tmp/blender.tar.xz
  mkdir -p "$BLENDER_DIR" && tar -xf /tmp/blender.tar.xz -C "$BLENDER_DIR" --strip-components=1
fi
"$BLENDER_DIR/blender" -b --version | head -1
echo "setup took $(( $(date +%s) - t0 ))s"

echo "==> rendering $REELS (jobs=$JOBS, samples=$SAMPLES)"
python3 scripts/batch.py $REELS --blender "$BLENDER_DIR/blender" --engine cycles \
  --samples "$SAMPLES" --jobs "$JOBS" --post "--glow --grain" || echo "some reels failed - see above"

if [ -n "${STORIES:-}" ]; then
  for st in $STORIES; do
    [[ "$st" == *.voice.json ]] && continue
    voice=$(python3 -c "import json,pathlib,sys;p=pathlib.Path('$st').with_suffix('.voice.json');print(json.loads(p.read_text())['audio'] if p.exists() else '')")
    echo "==> story $st ${voice:+(voice: $voice)}"
    python3 scripts/make_story.py "$st" --blender "$BLENDER_DIR/blender" --samples "$SAMPLES" ${voice:+--voice "$voice"} \
      || echo "story $st failed"
  done
  cp output/*_story/*_story.mp4 output/ 2>/dev/null || true
fi

echo "==> packaging"
zipname="$WORK/reels_$(date +%Y%m%d_%H%M).zip"
(cd output && zip -q -j "$zipname" */*_reel.mp4 */*_cover.jpg *_story.mp4 2>/dev/null) && ls -lh "$zipname"
echo "Download it from the pod's Jupyter file browser ($zipname), or: runpodctl send $zipname"
echo "total $(( ($(date +%s) - t0) / 60 )) min - remember to STOP the pod when you're done."
