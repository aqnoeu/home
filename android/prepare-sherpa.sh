#!/usr/bin/env bash
# Download the pinned, official sherpa-onnx Android AAR; do not commit binaries.
set -euo pipefail
mkdir -p android/app/libs
url="https://github.com/k2-fsa/sherpa-onnx/releases/download/v1.13.8/sherpa-onnx-1.13.8.aar"
dest="android/app/libs/sherpa-onnx.aar"
expected="633c24321e06b1fe79feafa03ea16cbc0f8a286641e2da3559bac91bdb13bd96"
if [[ -f "$dest" ]] && echo "$expected  $dest" | sha256sum -c - >/dev/null 2>&1; then
  echo "sherpa-onnx Android AAR já validado"; exit 0
fi
curl --retry 3 -fL --connect-timeout 15 --max-time 240 "$url" -o "$dest.tmp"
echo "$expected  $dest.tmp" | sha256sum -c -
mv "$dest.tmp" "$dest"
