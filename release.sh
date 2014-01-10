#!/bin/bash
# Copyright (c) 2013-2014 Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

set -e
set -x

rm -r dota2_nohats || true
rm dota2_nohats.7z || true
fusermount -u ~/dota_unpacked || true
~/unvpk/build/vpkfs/vpkfs "/mnt/steam/steamapps/common/dota 2 beta/dota/pak01_dir.vpk" ~/dota_unpacked
# ~/unvpk/build/vpkfs/vpkfs "/mnt/steam/steamapps/common/dota 2 test/dota/pak01_dir.vpk" ~/dota_unpacked
python2 -u nohats.py ~/dota_unpacked dota2_nohats "$@" > nohats_log.txt 2> nohats_warnings.txt
unix2dos -n README.md readme.txt
7z a -mx -bd dota2_nohats.7z dota2_nohats nohats_log.txt nohats_warnings.txt readme.txt > /dev/null
