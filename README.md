# General
## What is this?
Dota 2 nohats is a modification for Valve's Dota 2.
Installing this mod overrides cosmetic files with default files.
Effectively it seems like nobody has cosmetics equipped.
The page for this mod is <https://dota2nohats.neocities.org/>.

## How do I install this mod?
Copy the files to the Dota 2 folder (steamapps/common/dota 2 beta/dota).
Add the "-override_vpk" parameter to the Dota 2 launch options.

## How do I uninstall this mod?
Remove the "-override_vpk" parameter fom the Dota 2 launch options.
Remove the files from the Dota 2 folder.
Note: be careful with the "resource" folder.

## Will this mod break if Dota 2 is updated?
No, generally this mod will continue to function after Dota 2 is updated.
New cosmetics are not overridden and can be seen though.

## What do I do if I have technical problems with this mod?
Remove the "-override_vpk" parameter fom the Dota 2 launch options.
Check the bug tracker for your problem.
If your problem is not on the bug tracker, create a new entry.
Make sure to include relevant demo files, screenshots, error messages, logs etc.

## Are there known problems with this mod?
The most up to date list of known problems is on the bug tracker.
At the time of this release, the known bugs are:
* Portraits can look weird, especially on couriers

# Technical
## How do I create the mod files?

The mod files are created using a Python 2 script and the files from the Dota 2 VPK's.
The command to create it is:

    python nohats.py ../dota_unpacked dota2_nohats > nohats_log.txt 2> nohats_warnings.txt

This command has been tested with Python 2.7.5 on Windows and Arch Linux.

## Which kinds of cosmetics are overridden where?

Data about cosmetic files is gathered from "scripts/items/items_game.txt".

The following are overridden with the default files:

* Cosmetic models from "model_player" fields
* Cosmetic summon models from "entity_model" visuals
* Cosmetic alternate hero models from "hero_model_change" visuals
* Cosmetic courier models from "courier" and "courier_flying" visuals
* Custom icons from "icon_replacement" and "ability_icon_replacement" visuals
* Custom particle snapshots from "particle_snapshot" visuals

These can be found in the following folders:

* "models/{courier,creeps,items}"
* "resource/flash3"
* "particles/models"

Custom sounds from "sound" visuals are overridden by the default sound lengthened to 2 seconds.
These can be found in the folder "sound".

Custom animations from "activity" visuals are overridden by modifying the hero models.
Note: taunt and loadout animations are not overridden.
Custom skins from "skin" visuals and "set_parent_skin" fields are overridden by modifying hero and courier model files.
These can be found in the folders "models/{heroes,props_gameplay}".

Custom particle systems come from "attached_particlesystem" visuals, "particle" visuals and unusual couriers.
They are overridden by default particle systems and reassembled into particle files.
These can be found in the folders "particles/{econ,units}".
