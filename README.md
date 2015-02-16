# General
## What is this?
Dota 2 NoHats is a modification for Valve's Dota 2.
Installing this mod overrides cosmetic files with default files
and removes in-game ads. Effectively it seems like nobody has
cosmetics equipped.
The page for this mod is <https://dota2nohats.neocities.org/>.

## How do I install this mod?
Extract the `nohats` and `dota` folders to the Dota 2 folder
(steamapps/common/dota 2 beta). This will overwrite `gameinfo.txt`.
Add the `-enable_addons` parameter to the Dota 2 launch options.

## How do I uninstall this mod?
Remove the `-enable_addons` parameter from the Dota 2 launch options.
Remove the `nohats` folder.
Restore the `gameinfo.txt` file by using the "Verify Integrity of Game Cache"
feature in Steam on Dota 2.

## Do I need to update this mod when Dota 2 is updated?
Yes. Updated versions appear as soon as possible, often within 24 hours.

While outdated versions of this mod will usually continue to
function after Dota 2 is updated, there are some problems:

* New cosmetics are not overridden
* Default models and effects are still the old versions
* Prepare for unforeseen consequences

## What do I do if I have technical problems with this mod?
Check the bug tracker for your problem.
If your problem is not on the bug tracker, create a new entry.
Make sure to include relevant demo files, screen shots, error messages, logs etc.

## Are there known problems with this mod?
The most up to date list of known problems is on the bug tracker.
At the time of this release, the known bugs are:

* Portraits can look weird, especially on couriers
* Alternative hero voice packs are not overridden
* Effigies are not overridden

# Technical
## How do I view the files in this mod?
Use a VPK tool such as [GCFScape](http://nemesis.thewavelength.net/?p=26).

## Which kinds of cosmetics are overridden where?
Data about cosmetic files is gathered from `scripts/items/items_game.txt`.

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

A detailed report on what has been overridden can be found in `nohats_log.txt`.

# Acknowledgements
I would like to thank `the_parrot_is_dead` for [information on using
`gameinfo.txt` to override game files](<http://steamcommunity.com/groups/EEanimemods/discussions/0/604941528489404842/#c606068060821053170>).
Check out their [mod manager](https://github.com/philface/d2modmanager).
