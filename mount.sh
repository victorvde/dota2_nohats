#!/bin/bash
# Copyright (c) Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

set -e
set -x

fusermount -u ~/dota_unpacked || true
~/unvpk/build/vpkfs/vpkfs "/mnt/steam/steamapps/common/dota 2 beta/dota/pak01_dir.vpk" ~/dota_unpacked
# ~/unvpk/build/vpkfs/vpkfs "/mnt/steam/steamapps/common/dota 2 test/dota/pak01_dir.vpk" ~/dota_unpacked
