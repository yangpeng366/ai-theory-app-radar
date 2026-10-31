#!/bin/bash
# Fetch and install the Lean 4 toolchain that openai/math pins
# (lean/lean-toolchain -> leanprover/lean4:v4.34.1) into elan, without
# relying on releases.lean-lang.org, which is unreliable from this network.
#
# Method: the GitHub release tarball is pulled in 4 MB Range chunks through a
# Range-capable mirror, reassembled, and unpacked into elan's toolchain
# directory.  The script is idempotent: chunks already on disk with the
# expected size are reused, so an interrupted run can simply be restarted.
#
# Usage (inside WSL):
#   bash fetch-lean-toolchain.sh
# Log: /root/fetch-lean.log

set -u

LOG=/root/fetch-lean.log
exec >>"$LOG" 2>&1

VERSION="v4.34.1"
SIZE=580432872
CHUNK=4194304
MIRROR="https://gh-proxy.com/https://github.com/leanprover/lean4/releases/download"
URL="$MIRROR/$VERSION/lean-4.34.1-linux.tar.zst"
PARTS=/root/leanparts
TARBALL=/root/lean-4.34.1-linux.tar.zst
TOOLCHAIN=/root/.elan/toolchains/leanprover--lean4---v4.34.1

echo "start $(date -Is)"
mkdir -p "$PARTS"

# tar --zstd needs the zstd binary; try to get it without failing the run.
if ! command -v zstd >/dev/null 2>&1; then
    apt-get install -y zstd >/dev/null 2>&1 || echo "apt-get install zstd failed"
fi
command -v zstd >/dev/null 2>&1 && echo "zstd: $(command -v zstd)" || echo "zstd: MISSING"

index=0
start=0
while [ "$start" -lt "$SIZE" ]; do
    end=$((start + CHUNK - 1))
    if [ "$end" -ge "$SIZE" ]; then end=$((SIZE - 1)); fi
    part=$(printf "%s/part.%03d" "$PARTS" "$index")
    want=$((end - start + 1))
    have=0
    if [ -f "$part" ]; then have=$(stat -c%s "$part"); fi
    if [ "$have" -ne "$want" ]; then
        curl -sSfL --retry 3 --retry-delay 2 -r "$start-$end" "$URL" -o "$part" \
            || { echo "chunk $index failed"; exit 1; }
        have=$(stat -c%s "$part")
        if [ "$have" -ne "$want" ]; then
            echo "chunk $index short: $have != $want"
            exit 1
        fi
    fi
    start=$((end + 1))
    index=$((index + 1))
    echo "chunk $index done ($start/$SIZE) $(date -Is)"
done

cat "$PARTS"/part.* > "$TARBALL"
actual=$(stat -c%s "$TARBALL")
echo "assembled $actual bytes (expected $SIZE)"
[ "$actual" -eq "$SIZE" ] || exit 2

mkdir -p /root/elan-tmp
tar --zstd -xf "$TARBALL" -C /root/elan-tmp || exit 3
mkdir -p "$TOOLCHAIN"
cp -a /root/elan-tmp/*/. "$TOOLCHAIN"/
export PATH=/root/.elan/bin:$PATH
elan default leanprover/lean4:$VERSION
/root/.elan/bin/lean --version
echo "done $(date -Is)"
