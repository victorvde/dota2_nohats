from vdf import load, dump
from os.path import abspath, exists, dirname, join
from sys import argv, stdout
from shutil import copyfile
from os import makedirs, listdir
from kvlist import KVList
from mdl import MDL
import wave

def nohats():
    with open(join(dota_dir, "scripts/items/items_game.txt"), "rb") as input:
        d = load(input)

    defaults = get_defaults(d)
    #fix_models(d, defaults)
    visuals = get_visuals(d)
    visuals = filter_visuals(visuals)
    #visuals = fix_style_models(d, visuals, defaults)
    visuals = fix_sounds(visuals)
    #visuals = fix_hero_icons(visuals)
    #visuals = fix_ability_icons(visuals)
    #units = get_units()
    #visuals = fix_summons(visuals, units)
    #visuals = fix_hero_forms(visuals)
    #visuals = fix_couriers(visuals, units)
    #visuals = fix_flying_couriers(visuals, units)
    #visuals = fix_animations(d, visuals)

    x, y = filtersplit(visuals, isvisualtype(None))
    print x
    left = set()
    for e in visuals:
        id, k, v = e
        if isinstance(v, KVList):
            left.add(v.get("type"))
    print left

def get_attrib(d, item, key):
    v = item.get(key)
    if v is None and "prefab" in item:
        v = d["items_game"]["prefabs"][item["prefab"]].get(key)
    return v

def is_default(d, item):
    return get_attrib(d, item, "baseitem") == "1"

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

def get_item(d, id):
    return d["items_game"]["items"][id]

def get_defaults(d):
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
    return defaults

def get_default_model(d, defaults, hero, slot):
    default_id = defaults.get((hero, slot))
    if default_id is None:
        return None
    default_item = d["items_game"]["items"][default_id]
    return default_item["model_player"]

def copy(src, dest):
    print u"copy '{}' to '{}'".format(src, dest)
    if nohats_dir is None:
        return
    src = join(dota_dir, src)
    dest = join(nohats_dir, dest)
    dest_dir = dirname(dest)
    if not exists(dest_dir):
        makedirs(dest_dir)
    copyfile(src, dest)

def copy_model(src, dest):
    assert src.endswith(".mdl")
    src = src[:-len(".mdl")]
    assert dest.endswith(".mdl")
    dest = dest[:-len(".mdl")]
    copy(src + ".mdl", dest + ".mdl")
    copy(src + ".vvd", dest + ".vvd")
    copy(src + ".dx90.vtx", dest + ".dx90.vtx")

def fix_models(d, defaults):
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
            default_model = get_default_model(d, defaults, hero, slot)
            if default_model is not None:
                copy_model(default_model, item["model_player"])
            else:
                copy_model("models/development/invisiblebox.mdl", item["model_player"])

def get_visuals(d):
    # get visual modifiers
    visuals = []
    for id, item in d["items_game"]["items"]:
        if id == "default" or is_default(d, item):
            continue
        if "visuals" in item:
            for k, v in item["visuals"]:
                visuals.append((id, k, v))

    return visuals

def filter_visuals(visuals):
    # ignore skip_model_combine
    visuals = filter(lambda (id, k, v): not(k == "skip_model_combine" and v == "1"), visuals)

    # ignore some crap
    ignore_types = ["announcer", "announcer_preview", "ability_name", "entity_scale", "hud_skin", "speech", "particle_control_point"]
    visuals = filter(lambda (id, k, v): not(isinstance(v, KVList) and v.get("type") in ignore_types), visuals)

    return visuals

def filtersplit(l, f):
    a = []
    b = []
    for e in l:
        if f(e):
            a.append(e)
        else:
            b.append(e)
    return (a, b)

def fix_style_models(d, visuals, defaults):
    # fix alternate style models
    styles_visuals, visuals = filtersplit(visuals, lambda (id, k, v): k == "styles")
    for id, _, visual in styles_visuals:
        item = get_item(d, id)
        hero = get_hero(d, item)
        slot = get_slot(d, item)
        default_model = get_default_model(d, defaults, hero, slot)
        for styleid, v in visual:
            if not "model_player" in v:
                continue
            if default_model is not None:
                copy_model(default_model, v["model_player"])
            else:
                copy_model("models/development/invisiblebox.mdl", v["model_player"])

    return visuals

def isvisualtype(type):
    def filter(e):
        id, k, v = e
        return isinstance(v, KVList) and v.get("type") == type
    return filter

def assetmodifier1(visual):
    type = visual.pop("type")
    asset = visual.pop("asset")
    modifier = visual.pop("modifier")
    if "frequency" in visual:
        frequency = visual.pop("frequency")
        assert frequency == "1"
    if "style" in visual:
        style = visual.pop("style")
    assert len(visual) == 0, visual.keys()
    return (asset, modifier)

def assetmodifier(iterable):
    for id, key, visual in iterable:
        yield assetmodifier1(visual)

def sound_files(sound):
    if "wave" in sound:
        return [sound["wave"].lstrip(")")]
    elif "rndwave" in sound:
        return [wave.lstrip(")") for wave in sound["rndwave"].values()]

def copy_wave(src, dest):
    print u"copy wave '{}' to '{}'".format(src, dest)
    src = join(dota_dir, src)
    try:
        input = wave.open(src, "rb")
        frames_available = input.getnframes()
        # fill to two seconds because of noise
        frames_needed = 2 * input.getframerate()
        empty_frame = "\0" * input.getsampwidth() * input.getnchannels()
        filler_frames = empty_frame * max(frames_needed - frames_available, 0)

        if nohats_dir is None:
            return
        dest = join(nohats_dir, dest)
        dest_dir = dirname(dest)
        if not exists(dest_dir):
            makedirs(dest_dir)

        try:
            output = wave.open(dest, "wb")
            output.setparams(input.getparams())
            output.writeframes(input.readframes(frames_available) + filler_frames)
        finally:
            output.close()
    finally:
        input.close()

def fix_sounds(visuals):
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
            copy_wave(join("sound", asset_files[0]), join("sound", modifier_file))

    return visuals

def fix_hero_icons(visuals):
    # fix hero icon visuals (lina arcana)
    icon_visuals, visuals = filtersplit(visuals, isvisualtype("icon_replacement"))
    for asset, modifier in assetmodifier(icon_visuals):
        prefix = "npc_dota_hero_"
        assert asset.startswith(prefix)
        asset = asset[len(prefix):]
        assert modifier.startswith(prefix)
        modifier = modifier[len(prefix):]
        for image_dir in ["resource/flash3/images/heroes", "resource/flash3/images/miniheroes"]:
            copy(join(image_dir, asset + ".png"), join(image_dir, modifier + ".png"))

    return visuals

def fix_ability_icons(visuals):
    # fix spell icon visuals (lina arcana)
    ability_icon_visuals, visuals = filtersplit(visuals, isvisualtype("ability_icon_replacement"))
    for asset, modifier in assetmodifier(ability_icon_visuals):
        image_dir = "resource/flash3/images/spellicons"
        copy(join(image_dir, asset + ".png"), join(image_dir, modifier + ".png"))

    return visuals

def get_units():
    # get unit model list
    with open(join(dota_dir, "scripts/npc/npc_units.txt")) as input:
        units = load(input)
    return units

def fix_summons(visuals, units):
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
        copy_model(asset_model, modifier)

    return visuals

def fix_hero_forms(visuals):
    # fix hero model overrides
    hero_visuals, visuals = filtersplit(visuals, isvisualtype("hero_model_change"))
    for asset, modifier in assetmodifier(hero_visuals):
        copy_model(asset, modifier)

    return visuals

def fix_particle_snapshots(visuals):
    # fix particle snapshots
    psf_visuals, visuals = filtersplit(visuals, isvisualtype("particle_snapshot"))
    for asset, modifier in assetmodifier(psf_visuals):
        copy(asset, modifier)

    return visuals

def fix_couriers(visuals, units):
    courier_visuals, visuals = filtersplit(visuals, isvisualtype("courier"))
    courier_model = units["DOTAUnits"]["npc_dota_courier"]["Model"]
    for asset, modifier in assetmodifier(courier_visuals):
        assert modifier in ["radiant", "dire"]
        copy_model(courier_model, asset)
    return visuals

def fix_flying_couriers(visuals, units):
    flying_courier_visuals, visuals = filtersplit(visuals, isvisualtype("courier_flying"))
    flying_courier_model = units["DOTAUnits"]["npc_dota_flying_courier"]["Model"]
    for asset, modifier in assetmodifier(flying_courier_visuals):
        assert modifier in ["radiant", "dire"]
        copy_model(flying_courier_model, asset)

    return visuals

def fix_animations(d, visuals):
    item_activities = {}
    activity_visuals, visuals = filtersplit(visuals, isvisualtype("activity"))
    for id, key, visual in activity_visuals:
        asset, modifier = assetmodifier1(visual)
        if asset == "ACT_DOTA_TAUNT":
            continue
        item = get_item(d, id)
        hero = get_hero(d, item)
        item_activities.setdefault(hero, set())
        item_activities[hero].add(modifier)

    with open(join(dota_dir, "scripts/npc/npc_heroes.txt")) as input:
        npc_heroes = load(input)

    for hero in item_activities.keys():
        model = npc_heroes["DOTAHeroes"][hero]["Model"]
        mung_offsets = set()
        model_parsed = MDL()
        with open(join(dota_dir, model), "rb") as s:
            model_parsed.unpack(s)
        for sequence in model_parsed.data["localsequence"]:
            for activitymodifier in sequence["activitymodifier"]:
                if activitymodifier["szindex"][1] in item_activities[hero]:
                    mung_offsets.add(activitymodifier["szindex"][0])

        copy(model, model)
        print u"Removing sequences with modifier {}".format(item_activities[hero])
        if nohats_dir is None:
            continue
        with open(join(nohats_dir, model), "r+b") as s:
            for offset in mung_offsets:
                s.seek(offset)
                assert s.read(1) not in ["X", ""]
                s.seek(offset)
                s.write("X")

    return visuals


if __name__ == "__main__":
    dota_dir = abspath(argv[1])
    try:
        nohats_dir = argv[2]
    except IndexError:
        nohats_dir = None
    if nohats_dir is not None:
        nohats_dir = abspath(nohats_dir)

    nohats()
