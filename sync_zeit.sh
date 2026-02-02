#!/usr/bin/env bash
set -exu
mkdir -p work && cd work || exit 1

if ! fetch_zeit.py --formats="epub pdf"; then
    mv zeit_login_error.png /tmp
    exit 1
fi
rclone copy "$PWD" zeitung:
rm ./*.epub
rmapi mput Zeitung
rm ./*

wdir="$PWD"
cd .. && rm -rf "$wdir"
