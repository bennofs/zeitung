#!/usr/bin/env bash
set -exu
mkdir -p work && cd work || exit 1

fetch_freitag.py pdf epub
rclone copy "$PWD" zeitung:
rm ./*.epub
rmapi mput Zeitung
rm ./*

wdir="$PWD"
cd .. && rm -rf "$wdir"
