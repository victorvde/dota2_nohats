#!/bin/bash
# Copyright (c) Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

set -e
set -x

rm -r dota2_nohats || true
rm dota2_nohats.7z || true
rm -r nohats || true
rm -r dota || true

./mount.sh
pypy3 -u nohats.py ~/dota_unpacked dota2_nohats "$@" > nohats_log.txt 2>&1

unix2dos -n README.md readme.txt

mkdir nohats
pypy3 vpk.py a nohats/pak01 dota2_nohats/

mkdir dota
cp gameinfo.txt dota/gameinfo.txt

7z a -mx -ms=off dota2_nohats.7z nohats dota nohats_log.txt readme.txt > /dev/null

times
