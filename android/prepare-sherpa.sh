#!/usr/bin/env bash
# Download the pinned, official sherpa-onnx Android AAR; do not commit binaries.
set -euo pipefail
mkdir -p android/app/libs
url="https://github.com/k2-fsa/sherpa-onnx/releases/download/v2.0.1/sherpa-onnx-2.0.1.aar"
dest="android/app/libs/sherpa-onnx.aar"
expected="a8d09d1d32f3eb8520482c6d3d43fae674681c5b050385967c70a3c2c9bf0ee7"
if [[ -f "$dest" ]] && echo "$expected  $dest" | sha256sum -c - >/dev/null 2>&1; then
  echo "sherpa-onnx Android AAR já validado"; exit 0
fi
curl --retry 3 -fL --connect-timeout 15 --max-time 240 "$url" -o "$dest.tmp"
echo "$expected  $dest.tmp" | sha256sum -c -
mv "$dest.tmp" "$dest"
