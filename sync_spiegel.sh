#!/usr/bin/env bash
set -exu
mkdir -p work && cd work || exit 1

fetch_spiegel.py "$@"
rmapi mput Zeitung
rclone copy "$PWD" zeitung:
rm ./*

wdir="$PWD"
cd .. && rm -rf "$wdir"
