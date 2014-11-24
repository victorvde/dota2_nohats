# General
## What is this?
Dota 2 nohats is a modification for Valve's Dota 2.
Installing this mod overrides cosmetic files with default files and removes in-game ads.
Effectively it seems like nobody has cosmetics equipped.
The page for this mod is <https://dota2nohats.neocities.org/>.

## How do I install this mod?
Copy the files to the Dota 2 folder (steamapps/common/dota 2 beta/dota).
Add the "-override_vpk" parameter to the Dota 2 launch options.

## How do I uninstall this mod?
Remove the "-override_vpk" parameter from the Dota 2 launch options.
Remove the files from the Dota 2 folder.

Be careful with the "resource" folder. If you remove default Dota 2
files, you can get them back with "Verify Integrity of Game Cache".

## Do I need to update this mod when Dota 2 is updated?
Yes. Updated versions appear as soon as possible, often within 24 hours.

While outdated versions of this mod will usually continue to
function after Dota 2 is updated, there are some problems:
* New cosmetics are not overridden
* Default models and effects are still the old versions
* Unforeseen changes can have unpredictable results

## What do I do if I have technical problems with this mod?
Remove the "-override_vpk" parameter from the Dota 2 launch options.
Check the bug tracker for your problem.
If your problem is not on the bug tracker, create a new entry.
Make sure to include relevant demo files, screen shots, error messages, logs etc.

## Are there known problems with this mod?
The most up to date list of known problems is on the bug tracker.
At the time of this release, the known bugs are:
* Portraits can look weird, especially on couriers

# Technical
## How do I create the mod files?

The mod files are created using a Python 3 script and the files from the Dota 2 VPKs.
The command to create it is:

    python3 nohats.py ../dota_unpacked dota2_nohats > nohats_log.txt 2> nohats_warnings.txt

This command has been tested with Python 3.4.2 on Linux.

## Which kinds of cosmetics are overridden where?

Data about cosmetic files is gathered from "scripts/items/items_game.txt".

Then cosmetic effects are overridden, including:
* Models (*.mdl)
* Sounds (*.wav or *.mp3)
* Icons (*.png)
* Particles (*.pcf)
* Animations except taunts (hero *.mdl)
* Skins (hero *.mdl)

Also in-game ads are removed:
* Scaleform GFx (*.gfx)

Cosmetics that don't affect others are not overridden, including:
* HUDs
* Loading screens
* Weather effects
* Announcers
* Music

A detailed report on what has been overridden can be found in nohats_log.txt .
