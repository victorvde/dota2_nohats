from vdf import load, dump
from os.path import abspath, exists, dirname, join
from sys import argv, stdout
from shutil import copyfile
from os import makedirs, listdir
from kvlist import KVList

def sound_files(sound):
    if "wave" in sound:
        return [sound["wave"].lstrip(")")]
    elif "rndwave" in sound:
        return [wave.lstrip(")") for wave in sound["rndwave"].values()]

def filtersplit(l, f):
    a = []
    b = []
    for e in l:
        if f(e):
            a.append(e)
        else:
            b.append(e)
    return (a, b)

def isvisualtype(type):
    def filter(e):
        id, k, v = e
        return isinstance(v, KVList) and v.get("type") == type
    return filter

def assetmodifier(iterable):
   for id, key, visual in iterable:
        type = visual.pop("type")
        asset = visual.pop("asset")
        modifier = visual.pop("modifier")
        if "frequency" in visual:
            frequency = visual.pop("frequency")
            assert frequency == "1"
        if "style" in visual:
            style = visual.pop("style")
        assert len(visual) == 0, visual.keys()
        yield (asset, modifier)

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

def get_default_model(d, hero, slot):
    default_id = defaults.get((hero, slot))
    if default_id is None:
        return None
    default_item = d["items_game"]["items"][default_id]
    return default_item["model_player"]

def is_default(d, item):
    return get_attrib(d, item, "baseitem") == "1"

def copy(src, dest):
    print u"copy '{}' to '{}'".format(src, dest)
    src = join(dota_dir, src)
    dest = join(nohats_dir, dest)
    return
    dest_dir = dirname(dest)
    if not exists(dest_dir):
        makedirs(dest_dir)
    copyfile(src, dest)

if __name__ == "__main__":
    dota_dir = abspath(argv[1])
    nohats_dir = abspath("nohats")

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
            default_model = get_default_model(d, hero, slot)
            if default_model is not None:
                copy(default_model, item["model_player"])
            else:
                copy("models/development/invisiblebox.mdl", item["model_player"])

    # get visual modifiers
    visuals = []
    for id, item in d["items_game"]["items"]:
        if id == "default" or is_default(d, item):
            continue
        if "visuals" in item:
            for k, v in item["visuals"]:
                visuals.append((id, k, v))

    # ignore skip_model_combine
    visuals = filter(lambda (id, k, v): not(k == "skip_model_combine" and v == "1"), visuals)

    # ignore some crap
    ignore_types = ["announcer", "announcer_preview", "ability_name", "entity_scale", "hud_skin", "speech", "particle_control_point"]
    visuals = filter(lambda (id, k, v): not(isinstance(v, KVList) and v.get("type") in ignore_types), visuals)

    # fix alternate style models
    styles_visuals, visuals = filtersplit(visuals, lambda (id, k, v): k == "styles")
    for id, _, visual in styles_visuals:
        item = d["items_game"]["items"][id]
        hero = get_hero(d, item)
        slot = get_slot(d, item)
        default_model = get_default_model(d, hero, slot)
        for styleid, v in visual:
            if not "model_player" in v:
                continue
            if default_model is not None:
                copy(default_model, v["model_player"])
            else:
                copy("models/development/invisiblebox.mdl", v["model_player"])

    # get sound list
    sounds = KVList()
    hero_sound_dir = join(dota_dir, "scripts/game_sounds_heroes")
    for filename in listdir(hero_sound_dir):
        with open(join(hero_sound_dir, filename)) as s:
            part_sounds = load(s)
        sounds.update(list(part_sounds))

    # fix sound visuals
    sound_visuals, visuals = filtersplit(visuals, isvisualtype("sound"))
    for asset, modifier in assetmodifier(sound_visuals):
        asset_files = sound_files(sounds[asset])
        modifier_files = sound_files(sounds[modifier])
        for modifier_file in modifier_files:
            copy(join("sound", asset_files[0]), join("sound", modifier_file))

    # fix hero icon visuals (lina arcana)
    icon_visuals, visuals = filtersplit(visuals, isvisualtype("icon_replacement"))
    for asset, modifier in assetmodifier(icon_visuals):
        for image_dir in ["resource/flash3/images/heroes", "resource/flash3/images/miniheroes"]:
            copy(join(image_dir, asset + ".png"), join(image_dir, modifier + ".png"))

    # fix spell icon visuals (lina arcana)
    ability_icon_visuals, visuals = filtersplit(visuals, isvisualtype("ability_icon_replacement"))
    for asset, modifier in assetmodifier(ability_icon_visuals):
        image_dir = "resource/flash3/images/spellicons"
        copy(join(image_dir, asset + ".png"), join(image_dir, modifier + ".png"))

    # get unit model list
    with open(join(dota_dir, "scripts/npc/npc_units.txt")) as input:
        units = load(input)

    # fix summon overrides
    entity_model_visuals, visuals = filtersplit(visuals, isvisualtype("entity_model"))
    for asset, modifier in assetmodifier(entity_model_visuals):
        asset_model = None
        npc = units["DOTAUnits"].get(asset)
        if npc is None:
            # spirit bear
            npc = units["DOTAUnits"].get(asset + "1")
        if npc is None:
            # warlock golem
            npc = units["DOTAUnits"].get(asset + "_1")
        if npc is not None:
            asset_model = npc["Model"]
        elif asset == "dota_death_prophet_exorcism_spirit":
            # wth?
            asset_model = "models/heroes/death_prophet/death_prophet_ghost.mdl"
        assert asset_model is not None, asset
        copy(asset_model, modifier)

    # fix hero model overrides
    hero_visuals, visuals = filtersplit(visuals, isvisualtype("hero_model_change"))
    for asset, modifier in assetmodifier(hero_visuals):
        copy(asset, modifier)

    # fix particle snapshots
    psf_visuals, visuals = filtersplit(visuals, isvisualtype("particle_snapshot"))
    for asset, modifier in assetmodifier(psf_visuals):
        copy(asset, modifier)

    # fix courier
    courier_visuals, visuals = filtersplit(visuals, isvisualtype("courier"))
    courier_model = units["DOTAUnits"]["npc_dota_courier"]["Model"]
    for asset, modifier in assetmodifier(courier_visuals):
        assert modifier in ["radiant", "dire"]
        copy(courier_model, asset)

    # fix flying courier
    flying_courier_visuals, visuals = filtersplit(visuals, isvisualtype("courier_flying"))
    flying_courier_model = units["DOTAUnits"]["npc_dota_flying_courier"]["Model"]
    for asset, modifier in assetmodifier(flying_courier_visuals):
        assert modifier in ["radiant", "dire"]
        copy(flying_courier_model, asset)

    x, y = filtersplit(visuals, isvisualtype(None))
    print x
    left = set()
    for e in visuals:
        id, k, v = e
        if isinstance(v, KVList):
            left.add(v.get("type"))
    print left
