from vdf import load
from pprint import pprint
from os.path import abspath, exists, dirname, join
from sys import argv
from shutil import copyfile
from os import makedirs

def get_hero(d, item):
    if "used_by_heroes" not in item or item["used_by_heroes"] in ["0", "1"]:
        return None
    heroes = item["used_by_heroes"].keys()
    assert len(heroes) == 1
    hero = heroes[0]
    assert item["used_by_heroes"][hero] == "1"
    return hero

def get_slot(d, item):
    return get_attrib(d, item, "item_slot")

def get_attrib(d, item, key):
    v = item.get(key)
    if v is None and "prefab" in item:
        v = d["items_game"]["prefabs"][item["prefab"]].get(key)
    return v

def is_default(d, item):
    return get_attrib(d, item, "baseitem") == "1"

def copy(src, dest):
    dest_dir = dirname(dest)
    if not exists(dest_dir):
        makedirs(dest_dir)
    copyfile(src, dest)

def remove_hats(dota_dir, nohats_dir):
    with open(join(dota_dir, "scripts/items/items_game.txt"), "rb") as input:
        d = load(input)

    defaults = {}
    for id, item in d["items_game"]["items"]:
        if is_default(d, item):
            hero = get_hero(d, item)
            assert hero is not None
            slot = get_slot(d, item)
            assert slot is not None
            if (hero, slot) in defaults:
                print u"id {} is a duplicate default for {}".format(id, (hero, slot))
            else:
                defaults[(hero, slot)] = id

    replace = {}

    # first: models
    visuals = []
    for id, item in d["items_game"]["items"]:
        if id == "default" or is_default(d, item):
            continue
        if not "model_player" in item:
            continue
        hero = get_hero(d, item)
        slot = get_slot(d, item)
        if hero is None:
            assert slot == "none" or slot in d["items_game"]["player_loadout_slots"].values(), slot
        else:
            if (hero, slot) in defaults:
                default_id = defaults[(hero, slot)]
                default_item = d["items_game"]["items"][default_id]
                print u"replace {} with default {}".format(item["model_player"], default_item["model_player"])
                # copy(join(dota_dir, default_item["model_player"]), join(nohats_dir, item["model_player"]))
            else:
                print u"completely remove {}".format(item["model_player"])
                # copy(join(dota_dir, "models/development/invisiblebox.mdl"), join(nohats_dir, item["model_player"]))
        if "visuals" in item:
            for k, v in item["visuals"]:
                visuals.append([(id, k, v)])

    # visual overrides #1: sounds
#    with
    #s =

if __name__ == "__main__":
    dota_dir = abspath(argv[1])
    nohats_dir = abspath("nohats")
    remove_hats(dota_dir, nohats_dir)
