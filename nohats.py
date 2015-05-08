# Copyright (c) 2013 Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from vdf import load, dump
from os.path import abspath, exists, dirname, join
from os import SEEK_END
from sys import argv, stdout, stderr, version
from shutil import copyfile
from os import makedirs, listdir, walk, name as os_name
from kvlist import KVList
from mdl import MDL, LocalSequence
from pcf import PCF
from swf import ScaleFormSWF, Matrix
from wave import open as wave_open
from collections import OrderedDict
from io import StringIO
from itertools import chain
from binary import FakeWriteStream
from random import randint, seed
from re import subn

def header(s):
    print("== {} ==".format(s))

def canonical_file(p):
    return p.lower().replace("\\", "/")

def dota_file(p):
    return join(dota_dir, canonical_file(p))

def nohats_file(p):
    return join(nohats_dir, canonical_file(p))

def source_file(src):
    if nohats_dir and exists(nohats_file(src)):
        src = nohats_file(src)
    else:
        src = dota_file(src)
    return src

def nohats():
    header("Loading items_game.txt")
    with open(dota_file("scripts/items/items_game.txt"), "rt", encoding="utf-8") as input:
        d = load(input)

    header("Getting defaults")
    defaults = get_defaults(d)
    default_ids = set(defaults.values())
    header("Getting visuals")
    visuals = get_visuals(d, default_ids)
    visuals = filter_visuals(visuals)
    header("Loading npc_units.txt")
    units = get_units()
    header("Loading npc_heroes.txt")
    npc_heroes = get_npc_heroes()

    header("Fixing scaleform files")
    fix_scaleform()

    header("Fixing simple model files")
    fix_models(d, defaults, default_ids)
    header("Fixing alternate style models")
    visuals = fix_style_models(d, visuals, defaults)
    header("Fixing additional wearables")
    visuals = fix_additional_wearables(d, visuals, defaults)
    header("Fixing hex models")
    visuals = fix_hex_models(d, visuals)
    header("Fixing pet models")
    visuals = fix_pet_models(visuals)
    header("Fixing portrait models")
    visuals = fix_portrait_models(visuals)
    header("Fixing sounds")
    visuals = fix_sounds(visuals)
    header("Fixing icons")
    visuals = fix_hero_icons(visuals)
    visuals = fix_ability_icons(visuals)
    header("Fixing summons")
    visuals = fix_summons(visuals, units, d, default_ids)
    header("Fixing alternate hero models")
    visuals = fix_hero_forms(visuals)
    header("Fixing particle snapshots")
    visuals = fix_particle_snapshots(visuals)
    header("Fixing animations")
    visuals = fix_animations(d, visuals, npc_heroes)
    header("Fixing alternate base models")
    visuals = fix_base_models(visuals, npc_heroes)
    header("Fixing skins")
    courier_model = units["DOTAUnits"]["npc_dota_courier"]["Model"]
    flying_courier_model = units["DOTAUnits"]["npc_dota_flying_courier"]["Model"]
    fix_skins(courier_model, flying_courier_model)
    header("Fixing couriers")
    visuals = fix_couriers(visuals, units, courier_model)
    visuals = fix_flying_couriers(visuals, units, flying_courier_model)
    header("Fixing particle color")
    fix_particle_color(npc_heroes)
    header("Fixing effigies")
    fix_effigies()
    header("Fixing particles")
    visuals = fix_particles(d, defaults, default_ids, visuals, units, npc_heroes)

    assert not visuals, visuals

def get_attrib(d, item, key):
    v = item.get(key)
    if v is None and "prefab" in item:
        v = d["items_game"]["prefabs"][item["prefab"]].get(key)
    return v

def get_hero(d, item):
    if "used_by_heroes" not in item or item["used_by_heroes"] in ["0", "1"]:
        return None
    heroes = list(item["used_by_heroes"].keys())
    if len(heroes) != 1:
        return None
    hero = heroes[0]
    assert item["used_by_heroes"][hero] == "1"
    return hero

def get_slot(d, item):
    return get_attrib(d, item, "item_slot")

def get_item(d, id):
    return d["items_game"]["items"][id]

def find_item_by_name(d, name):
    for id, item in d["items_game"]["items"]:
        if item.get("name") == name:
            return (id, item)
    return None

def get_defaults(d):
    defaults = {}
    for id, item in d["items_game"]["items"]:
        if get_attrib(d, item, "baseitem") == "1":
            slot = get_slot(d, item)
            assert slot is not None, id
            hero = get_hero(d, item)
            assert hero is not None, id
            if (hero, slot) in defaults:
                print("Warning: id '{}' is a duplicate default for '{}'".format(id, (hero, slot)), file=stderr)
            else:
                defaults[(hero, slot)] = id
    return defaults

def get_default_item(d, defaults, item):
    hero = get_hero(d, item)
    slot = get_slot(d, item)
    default_id = defaults.get((hero, slot))
    if default_id is None:
        return None
    default_item = get_item(d, default_id)
    return default_item

def copy(src, dest, dota=True):
    print("copy '{}' to '{}'".format(src, dest))
    if not exists(dota_file(dest)) and not dest.endswith(".cloth"):
        print("Warning: trying to override '{}' which does not exist".format(dest), file=stderr)
    if nohats_dir is None:
        return
    if dota:
        src = source_file(src)
    dest = nohats_file(dest)
    if src == dest:
        return
    dest_dir = dirname(dest)
    if not exists(dest_dir):
        makedirs(dest_dir)
    if not exists(dest):
        copyfile(src, dest)

def copy_model(src, dest):
    if src != dest:
        copy_model_always(src, dest)

def copy_model_always(src, dest):
    assert src.endswith(".mdl")
    src = src[:-len(".mdl")]
    assert dest.endswith(".mdl")
    dest = dest[:-len(".mdl")]
    copy(src + ".mdl", dest + ".mdl")
    copy(src + ".vvd", dest + ".vvd")
    copy(src + ".dx90.vtx", dest + ".dx90.vtx")
    if exists(source_file(src + ".cloth")):
        copy(src + ".cloth", dest + ".cloth")
    else:
        print("Create empty cloth file '{}'".format(dest + ".cloth"))
        if nohats_dir:
            with open(nohats_file(dest + ".cloth"), "wb") as s:
                s.write(b"ClothSystem\r\n{\r\n}\r\n")

def has_alternate_skins(item):
    if item.get("skin", "0") != "0":
        return True
    if "visuals" in item:
        if item["visuals"].get("skin", "0") != "0":
            return True
        for style_id, style in item["visuals"].get("styles", []):
            if style.get("skin", "0") != "0" and "model_player" not in style:
                return True
    return False

def fix_item_model(item, default_item, model_player):
    if default_item is not None:
        if not model_player in default_item:
            print("Warning: missing default model for '{}'".format(default_item["name"]), file=stderr)
            return
        copy_model(default_item[model_player], item[model_player])
        if has_alternate_skins(item):
            m = MDL()
            with open(source_file(default_item[model_player]), "rb") as s:
                m.unpack(s)
            if m["numskinfamilies"].data != 1:
                print("Warning: model '{}' has '{}' skin families, need to fix '{}'".format(default_item[model_player], m["numskinfamilies"].data, item[model_player]), file=stderr)
    else:
        copy_model("models/development/invisiblebox.mdl", item[model_player])

def fix_models(d, defaults, default_ids):
    for id, item in d["items_game"]["items"]:
        if id == "default" or id in default_ids:
            continue
        for model_player in ["model_player", "model_player1", "model_player2", "model_player3", "model_player4"]:
            if model_player in item:
                default_item = get_default_item(d, defaults, item)
                fix_item_model(item, default_item, model_player)

def get_visuals(d, default_ids):
    # get visual modifiers
    visuals = []
    for id, item in d["items_game"]["items"]:
        # if id == "default" or id in default_ids:
        #     continue
        slot = get_slot(d, item)
        if slot in ["weather", "music"]:
            continue
        if "visuals" in item:
            for k, v in item["visuals"]:
                visuals.append((id, k, v))

    for k, v in d["items_game"]["asset_modifiers"]:
        for k_, v_ in v:
            if k_.startswith("asset_modifier"):
                k_ = k_[len("asset_modifier"):]
            if not k_.isdigit():
                assert not isinstance(v_, KVList), "Wrong name for {} key {} but it should not be skipped".format(k, k_)
                continue
            visuals.append((None, "asset_modifier"+k+"_"+k_, v_))

    return visuals

def filter_visuals(visuals):
    # particle systems are handled seperately as a group per item
    visuals = [(id, k, v) for (id, k, v) in visuals if not k.startswith("attached_particlesystem")]

    # random stuff
    ignore_keys = [
        "skip_model_combine",
        "alternate_icons",
        "animation_modifiers",
        "skin",
        "player_card",
        "hide_on_portrait",
    ]
    visuals = [(id, k, v) for (id, k, v) in visuals if k not in ignore_keys]

    ignore_types = [
        "announcer",
        "announcer_preview",
        "ability_name",
        "entity_scale",
        "hud_skin",
        "speech",
        "particle_control_point",
        "loading_screen",
        "response_criteria",
        "custom_kill_effect",
        "cursor_pack",
        "buff_modifier",
        "strange_control_point",
        "healthbar_offset",
        "entity_healthbar_offset",
        "portrait_game",
        ]
    to_ignore = invisualtypes(ignore_types)
    visuals = [x for x in visuals if not to_ignore(x)]

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
    styles_visuals, visuals = filtersplit(visuals, lambda id_k_v: id_k_v[1] == "styles")
    for id, _, visual in styles_visuals:
        item = get_item(d, id)
        default_item = get_default_item(d, defaults, item)
        for styleid, v in visual:
            if not "model_player" in v:
                continue
            fix_item_model(v, default_item, "model_player")

    return visuals

def invisualtypes(types):
    def filter(e):
        id, k, v = e
        return k.startswith("asset_modifier") and v.get("type") in types
    return filter

def isvisualtype(type):
    return invisualtypes([type])

def assetmodifier1(visual):
    type = visual.pop("type")
    asset = visual.pop("asset", None)
    modifier = visual.pop("modifier", None)
    frequency = visual.pop("frequency", None)
    assert frequency in [None, "1"], frequency
    style = visual.pop("style", None)
    force_display = visual.pop("force_display", None)
    assert force_display in [None, "1"], force_display
    ingame_scale = visual.pop("ingame_scale", None)
    loadout_scale = visual.pop("loadout_scale", None)
    loadout_default_offset = visual.pop("loadout_default_offset", None)
    loadout_hero_offsets = visual.pop("loadout_hero_offsets", None)
    levelup_rule = visual.pop("levelup_rule", None)
    assert levelup_rule in [None, "compendiumlevel", "killeater"], levelup_rule
    compendium_event_id = visual.pop("compendium_event_id", None)
    supports_coop_teleport = visual.pop("supports_coop_teleport", None)
    assert supports_coop_teleport in [None, "1"]
    assert len(visual) == 0, list(visual.keys())
    return (asset, modifier)

def assetmodifier(iterable):
    for id, key, visual in iterable:
        yield assetmodifier1(visual)

def fix_additional_wearables(d, visuals, defaults):
    additional_wearable_visuals, visuals = filtersplit(visuals, isvisualtype("additional_wearable"))
    additional_wearables = OrderedDict()
    for id, k, v in additional_wearable_visuals:
        asset, modifier = assetmodifier1(v)
        assert modifier is None, modifier
        assert id not in additional_wearables, id
        additional_wearables[id] = asset
    for id, asset in additional_wearables.items():
        item = get_item(d, id)
        hero = get_hero(d, item)
        slot = get_slot(d, item)
        default_id = defaults[(hero, slot)]
        if id == default_id:
            continue
        copy_model(additional_wearables[default_id], asset)
    return visuals

def fix_hex_models(d, visuals):
    hex_visuals, visuals = filtersplit(visuals, isvisualtype("hex_model"))
    for id, k, v in hex_visuals:
        asset, modifier = assetmodifier1(v)
        assert asset == "hex"
        item = get_item(d, id)
        hero = get_hero(d, item)
        if hero == "npc_dota_hero_lion":
            hex_model = "models/props_gameplay/frog.mdl"
        elif hero == "npc_dota_hero_shadow_shaman":
            hex_model = "models/props_gameplay/chicken.mdl"
        else:
            assert False, "Unknown hex model for hero {} item {}".format(hero, id)
        copy_model(hex_model, modifier)
    return visuals

def fix_pet_models(visuals):
    pet_visuals, visuals = filtersplit(visuals, isvisualtype("pet"))
    for id, key, visual in pet_visuals:
        pickup_model = visual.pop("pickup_item", None)
        strange_type = visual.pop("strange_type", None)
        skin = visual.pop("skin", None)
        asset, modifier = assetmodifier1(visual)
        copy_model("models/development/invisiblebox.mdl", asset)
        if pickup_model is not None:
            copy_model("models/development/invisiblebox.mdl", pickup_model)
    return visuals

def fix_portrait_models(visuals):
    portrait_visuals, visuals = filtersplit(visuals, isvisualtype("portrait_background_model"))
    for asset, modifier in assetmodifier(portrait_visuals):
        copy_model("models/heroes/pedestal/pedestal_1_small.mdl", asset)
    return visuals

def sound_files(sound):
    prefix_chars = "*#@<>^)(}$!?"
    if "wave" in sound:
        return [sound["wave"].lstrip(prefix_chars)]
    elif "rndwave" in sound:
        return [wave.lstrip(prefix_chars) for wave in sound["rndwave"].values()]

def copy_sound(src, dest):
    if src == dest:
        return
    if src.endswith(".wav") and dest.endswith(".wav"):
        copy_wave(src, dest)
    elif src.endswith(".mp3") and dest.endswith(".mp3"):
        copy(src, dest)
    else:
        if src == "sound/null.wav" and dest.endswith(".mp3"):
            copy("null.mp3", dest, dota=False)
        else:
            print("Warning: unknown sound extension copy for '{}' to '{}'".format(src, dest), file=stderr)

def copy_wave(src, dest):
    print("copy wave '{}' to '{}'".format(src, dest))

    orig_file = source_file(dest)
    orig_input = wave_open(orig_file, "rb")
    try:
        orig_nframes = orig_input.getnframes()
        orig_nchannels = orig_input.getnchannels()
        orig_framerate = orig_input.getframerate()
        orig_sampwidth = orig_input.getsampwidth()
    finally:
        orig_input.close()

    src_file = source_file(src)
    input = wave_open(src_file, "rb")
    try:
        nframes = input.getnframes()
        frames = input.readframes(nframes)
        nchannels = input.getnchannels()
        sampwidth = input.getsampwidth()
        framerate = input.getframerate()

        # convert null.wav into an empty copy of the original destination
        if src == "sound/null.wav":
            framerate = orig_framerate
            sampwidth = orig_sampwidth
            frames = bytearray()
            nframes = 0

        # sanity
        if framerate != orig_framerate:
            print("Warning: source {} has framerate {} but destination {} has framerate {}".format(src, framerate, dest, orig_framerate), file=stderr)
            return
        if sampwidth != orig_sampwidth:
            print("Warning: source {} has sampwidth {} but destination {} has sampwidth {}".format(src, sampwidth, dest, orig_sampwidth), file=stderr)
            return

        # fix number of channels
        if nchannels == orig_nchannels:
            pass
        elif nchannels == 1 and orig_nchannels == 2:
            # convert mono to stereo
            new_frames = bytearray()
            i = 0
            while i < len(frames):
                new_frames += frames[i:i+sampwidth]
                new_frames += frames[i:i+sampwidth]
                i += sampwidth
            assert i == len(frames)
            assert len(new_frames) == 2 * len(frames)
            frames = new_frames
            nchannels = orig_nchannels
        elif nchannels == 2 and orig_nchannels == 1:
            # convert stereo to mono
            assert sampwidth == 2, sampwidth
            new_frames = bytearray()
            for i in range(nframes):
                frame_i = i*2*sampwidth
                frame_left = int.from_bytes(frames[frame_i:frame_i+sampwidth], byteorder="little", signed=True)
                frame_right = int.from_bytes(frames[frame_i+sampwidth:frame_i+sampwidth*2], byteorder="little", signed=True)
                new_frame = (frame_left + frame_right) // 2
                new_frames += new_frame.to_bytes(2, byteorder="little", signed=True)
            assert len(new_frames) == len(frames) / 2
            frames = new_frames
            nchannels = orig_nchannels
        else:
            assert False, "Don't know how to convert from {} channels to {} channels".format(nchannels, orig_nchannels)

        # fill to original length, or at least two seconds, because of static noise
        frames_needed = max(orig_nframes, 2 * framerate)
        nfiller_frames = max(frames_needed - nframes, 0)
        nfiller_bytes = nfiller_frames * sampwidth * nchannels
        if "_loop" in src:
            filler_frames = bytearray()
            while len(filler_frames) < nfiller_bytes:
                filler_frame += frames
            filler_frames = filler_frames[:nfiller_bytes]
        else:
            if sampwidth == 1:
                filler_b = b"\x80"
            else:
                filler_b = b"\0"
            filler_frames = filler_b * nfiller_bytes
        frames += filler_frames

        orig_frames_len = orig_nframes * orig_sampwidth * orig_nchannels
        assert len(frames) >= orig_frames_len , "Converted {} has {} data bytes, but destination {} has {} data bytes".format(src, len(frames), dest, orig_frames_len)

        if nohats_dir is None:
            return
        dest_file = nohats_file(dest)
        dest_dir = dirname(dest_file)
        if not exists(dest_dir):
            makedirs(dest_dir)

        output = wave_open(dest_file, "wb")
        try:
            output.setparams(input.getparams())
            output.setnchannels(nchannels)
            output.setframerate(framerate)
            output.setsampwidth(sampwidth)
            output.writeframes(frames)
        finally:
            output.close()
    finally:
        input.close()

def sound_asset_layer(asset, layer):
    return asset.get("operator_stacks", {}).get("start_stack", {}).get(layer, {}).get("entry_name")

def copy_sound_asset(sounds, asset, modifier):
    if asset is None:
        asset_files = ["null.wav"]
    else:
        asset_files = sound_files(sounds[asset])
    modifier_files = sound_files(sounds[modifier])
    for i in range(len(modifier_files)):
        asset_file = asset_files[i % len(asset_files)]
        modifier_file = modifier_files[i]
        if modifier_file.startswith("weapons/hero/shared"):
            print("Warning: not copying '{}' to '{}' because it is shared".format(asset_file, modifier_file), file=stderr)
        else:
            copy_sound("sound/" + asset_file, "sound/" + modifier_file)

    for layer in ["play_second_layer", "play_third_layer"]:
        if asset is None:
            layer_asset = None
        else:
            layer_asset = sound_asset_layer(sounds[asset], layer)
        layer_modifier = sound_asset_layer(sounds[modifier], layer)

        if layer_asset != layer_modifier:
            if layer_modifier is not None:
                copy_sound_asset(sounds, layer_asset, layer_modifier)

def fix_sounds(visuals):
    # get sound list
    sounds = KVList()
    for root, _, files in chain(walk(dota_file("sound")), walk(dota_file("scripts"))):
        for f in files:
            if not (f.startswith("game_sounds") and f.endswith(".txt")):
                continue
            if f.endswith("_phonemes.txt"):
                continue
            if f.endswith("_manifest.txt"):
                continue
            with open(join(root, f), "rt", encoding="utf-8") as s:
                part_sounds = load(s)
            sounds.update(list(part_sounds))

    # fix sound visuals
    sound_visuals, visuals = filtersplit(visuals, isvisualtype("sound"))
    for asset, modifier in assetmodifier(sound_visuals):
        if not asset in sounds:
            print("Warning: can't find sound asset {}".format(asset), file=stderr)
            continue
        copy_sound_asset(sounds, asset, modifier)
    return visuals

def fix_hero_icons(visuals):
    # fix hero icon visuals (lina arcana)
    icon_visuals, visuals = filtersplit(visuals, isvisualtype("icon_replacement"))
    for asset, modifier in assetmodifier(icon_visuals):
        prefix = "npc_dota_hero_"
        if asset.startswith(prefix):
            asset = asset[len(prefix):]
            assert modifier.startswith(prefix)
            modifier = modifier[len(prefix):]
            for image_dir in ["resource/flash3/images/heroes", "resource/flash3/images/miniheroes"]:
                copy(image_dir + "/" + asset + ".png", image_dir + "/" + modifier + ".png")
        else:
            copy("resource/flash3/images/items/" + asset + ".png", "resource/flash3/images/items/" + modifier + ".png")

    return visuals

def fix_ability_icons(visuals):
    # fix spell icon visuals (lina arcana)
    ability_icon_visuals, visuals = filtersplit(visuals, isvisualtype("ability_icon"))
    for asset, modifier in assetmodifier(ability_icon_visuals):
        image_dir = "resource/flash3/images/spellicons"
        copy(image_dir + "/" + asset + ".png", image_dir + "/" + modifier + ".png")

    return visuals

def get_units():
    # get unit model list
    with open(dota_file("scripts/npc/npc_units.txt"), "rt", encoding="utf-8") as input:
        units = load(input)
    return units

def fix_summons(visuals, units, d, default_ids):
    # get default entity_model (tiny's tree)
    default_entity_models = {}
    for default_id in default_ids:
        item = get_item(d, default_id)
        if "visuals" in item:
            for k, v in item["visuals"]:
                if isvisualtype("entity_model")((default_id, k, v)):
                    asset, modifier = assetmodifier1(v)
                    default_entity_models[asset] = modifier

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
        elif asset in default_entity_models:
            asset_model = default_entity_models[asset]
        elif asset == "dota_death_prophet_exorcism_spirit":
            # wth?
            asset_model = "models/heroes/death_prophet/death_prophet_ghost.mdl"
        assert asset_model is not None, asset
        copy_model(asset_model, modifier)

    return visuals

def fix_base_models(visuals, heroes):
    # fix hero base model overrides (TB arcana)
    entity_model_visuals, visuals = filtersplit(visuals, isvisualtype("base_model"))
    for asset, modifier in assetmodifier(entity_model_visuals):
        asset_model = heroes["DOTAHeroes"][asset]["Model"]
        copy_model(asset_model, modifier)
        # special case to fix mismatched activities
        if modifier == "models/heroes/crystal_maiden/crystal_maiden_arcana.mdl":
            print("Applying activity fix to crystal_maiden_arcana.mdl")
            f = nohats_file(modifier)
            m = MDL()
            with open(f, "rb") as s:
                m.unpack(s)
            for seq in m["localsequence"]:
                if seq["labelindex"].data[1] == "cm_attack2" and seq["activitynameindex"].data[1] == "ACT_DOTA_ATTACK" and len(seq["activitymodifier"]) == 0:
                    sequence = seq
                    break
            else:
                assert False, "Can't find sequence to edit"
            with open(f, "r+b") as s:
                s.seek(0, SEEK_END)
                o = s.tell()
                s.write(b"ACT_DOTA_ATTACK2\0")
                while s.tell() % 4 != 0:
                    s.write(b"\0")
                total_size = s.tell()

                sequence["activitynameindex"].data = [o, "ACT_DOTA_ATTACK2"]
                s.seek(sequence["base"].data)
                sequence.pack(s)

                m["datalength"].data = total_size
                s.seek(0)
                m.pack(s)

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

def fix_couriers(visuals, units, courier_model):
    couriers = []
    courier_visuals, visuals = filtersplit(visuals, isvisualtype("courier"))
    for asset, modifier in assetmodifier(courier_visuals):
        if modifier not in couriers:
            couriers.append(modifier)
    for courier in couriers:
        copy_model(courier_model, courier)
    return visuals

def fix_flying_couriers(visuals, units, flying_courier_model):
    couriers = []
    flying_courier_visuals, visuals = filtersplit(visuals, isvisualtype("courier_flying"))
    for asset, modifier in assetmodifier(flying_courier_visuals):
        if modifier not in couriers:
            couriers.append(modifier)
    for courier in couriers:
        copy_model(flying_courier_model, courier)

    return visuals

def get_npc_heroes():
    with open(dota_file("scripts/npc/npc_heroes.txt"), "rt", encoding="utf-8") as input:
        npc_heroes = load(input)
    return npc_heroes

def fix_animations(d, visuals, npc_heroes):
    ignored = ["ACT_DOTA_STATUE_SEQUENCE"]

    item_activity_modifiers = set()

    activity_visuals, visuals = filtersplit(visuals, isvisualtype("activity"))
    for id, key, visual in activity_visuals:
        asset, modifier = assetmodifier1(visual)
        item_activity_modifiers.add(modifier)

    for k, v in npc_heroes["DOTAHeroes"]:
        if k == "Version":
            continue
        model = v["Model"]
        if not exists(source_file(model)):
            continue

        model_parsed = MDL()
        with open(source_file(model), "rb") as s:
            model_parsed.unpack(s)

        sequence_dict = OrderedDict()
        for sequence in model_parsed["localsequence"]:
            assert sequence["unused"].data == (0, 0, 0, 0, 0), sequence["unused"].data
            activity_name = sequence["activitynameindex"].data[1]
            activity_modifiers = frozenset(am["szindex"].data[1] for am in sequence["activitymodifier"])
            sequence_dict.setdefault((activity_name, activity_modifiers), sequence)

        copied = False
        for (activity_name, activity_modifiers), sequence in sequence_dict.items():
            if activity_name not in ignored and activity_modifiers & item_activity_modifiers:
                if not copied:
                    copy_model_always(model, model)
                    copied = True
                orig_activity_modifiers = activity_modifiers - item_activity_modifiers
                orig_seq = sequence_dict.get((activity_name, orig_activity_modifiers))
                if orig_seq is None:
                    orig_seq = sequence_dict.get((activity_name, frozenset()))
                idle_acts = ["ACT_DOTA_IDLE_RARE", "ACT_DOTA_VICTORY", "ACT_DOTA_TELEPORT", "ACT_DOTA_TELEPORT_END", "ACT_DOTA_SPAWN", "ACT_DOTA_KILLTAUNT", "ACT_DOTA_TAUNT", "ACT_DOTA_LOADOUT"]
                if orig_seq is None and activity_name in idle_acts:
                    orig_seq = sequence_dict.get(("ACT_DOTA_IDLE", orig_activity_modifiers))
                if orig_seq is None and activity_name in ["ACT_DOTA_MOMENT_OF_COURAGE"]:
                    orig_seq = sequence_dict.get(("ACT_DOTA_CAST_ABILITY_3", orig_activity_modifiers))
                if orig_seq is None and activity_name in ["ACT_DOTA_ATTACK_PARTICLE"]:
                    orig_seq = sequence_dict.get(("ACT_DOTA_ATTACK", orig_activity_modifiers))
                assert orig_seq is not None, (activity_name, orig_activity_modifiers)
                print("Replace sequence {} with {}".format(sequence["labelindex"].data[1], orig_seq and orig_seq["labelindex"].data[1]))
                if nohats_dir is None:
                    continue
                with open(nohats_file(model), "r+b") as s:
                    new_seq = LocalSequence()
                    new_seq.data = orig_seq.data
                    new_seq["labelindex"].data = sequence["labelindex"].data
                    new_seq["activitynameindex"].data = sequence["activitynameindex"].data
                    new_seq["numactivitymodifier"].data = sequence["numactivitymodifier"].data
                    new_seq["activitymodifierindex"].data = sequence["activitymodifierindex"].data
                    s.seek(sequence["base"].data)
                    new_seq.pack(s)
    return visuals

def get_particlesystems(item):
    pss = []
    if item is not None:
        for key, v in item.get("visuals", []):
            if key.startswith("attached_particlesystem"):
                system_name = v["system"].lower()
                if system_name == "chaos_knight_horse_ambient_parent":
                    pss.append("chaos_knight_horse_ambient")
                    pss.append("chaos_knight_ambient_tail")
                elif system_name not in pss:
                    pss.append(system_name)
    return pss

def get_particle_replacements(d, defaults, visuals, default_ids):
    particle_attachments = OrderedDict()
    for k, v in d["items_game"]["attribute_controlled_attached_particles"]:
        name = v["system"].lower()
        attach_type = v["attach_type"]
        attach_entity = v["attach_entity"]
        control_points = v.get("control_points")
        particle_attachments[name] = (attach_type, attach_entity, control_points)

    particle_replacements = OrderedDict()
    def add_replacement(system, default_system):
        attachment = particle_attachments.get(system)
        default_attachment = particle_attachments.get(default_system)
        if attachment and default_attachment and attachment != default_attachment:
            print("Warning: not using {} to replace {} because attachments differ ".format(default_system, system), file=stderr)
            default_system = None

        if system in particle_replacements:
            old_system = particle_replacements[system]
            if old_system != default_system:
                print("Warning: tried to replace system '{}' with '{}', but already replaced with '{}'".format(system, default_system, old_system), file=stderr)
        else:
            particle_replacements[system] = default_system

    default_particlesystems = set()
    for id, item in d["items_game"]["items"]:
        if not id in default_ids:
            continue
        for ps in get_particlesystems(item):
            default_particlesystems.add(ps)

    particle_visuals, visuals = filtersplit(visuals, isvisualtype("particle"))
    for id, k, v in particle_visuals:
        asset, modifier = assetmodifier1(v)
        add_replacement(modifier.lower(), asset.lower())

    for id, item in d["items_game"]["items"]:
        if id == "default" or id in default_ids:
            continue

        default_item = get_default_item(d, defaults, item)
        pss = get_particlesystems(item)
        default_pss = get_particlesystems(default_item)
        if default_pss and pss and len(pss) < len(default_pss):
            print("Warning: couldn't put default particle systems '{}' in '{}' ({})".format(default_pss, pss, id), file=stderr)

        for default_ps in list(default_pss):
            if default_ps in pss:
                default_pss.remove(default_ps)
                pss.remove(default_ps)

        while pss:
            ps = pss.pop(0)
            if ps in default_particlesystems:
                print("Warning: tried to override default particle system '{}' ({})".format(ps, id), file=stderr)
                continue
            known_default = particle_replacements.get(ps)
            if known_default and known_default in default_pss:
                default_pss.remove(known_default)
                default_ps = known_default
            elif default_pss:
                default_ps = default_pss.pop(0)
            else:
                default_ps = None
            add_replacement(ps, default_ps)

    for k, v in d["items_game"]["attribute_controlled_attached_particles"]:
        system_name = v["system"].lower()
        if "resource" in v and v["resource"].startswith("particles/econ/courier/"):
            add_replacement(system_name, None)

    # hard-coded stuff
    add_replacement("terrorblade_arcana_enemy_death", None)
    add_replacement("legion_commander_duel_arcana", None)
    add_replacement("techies_suicide_kills_arcana", None)
    add_replacement("techies_suicide_dud_arcana", None)
    add_replacement("pa_arcana_gravemarker_lvl1", None)
    add_replacement("pa_arcana_gravemarker_lvl2", None)
    add_replacement("pa_arcana_gravemarker_lvl3", None)
    add_replacement("frosty_effigy_ambient_radiant", None)
    add_replacement("frosty_effigy_ambient_l2_radiant", None)
    add_replacement("frosty_effigy_ambient_dire", None)
    add_replacement("frosty_effigy_ambient_l2_dire", None)
    add_replacement("jade_effigy_ambient_radiant", None)
    add_replacement("jade_effigy_ambient_dire", None)
    add_replacement("gold_effigy_ambient_radiant", None)
    add_replacement("gold_effigy_ambient_dire", None)
    add_replacement("gold_effigy_ambient_radiant_lvl2", None)
    add_replacement("gold_effigy_ambient_dire_lvl2", None)

    add_replacement("teleport_start_ti4", "teleport_start")
    add_replacement("teleport_end_ti4", "teleport_end")
    add_replacement("blink_dagger_start_ti4", "blink_dagger_start")
    add_replacement("blink_dagger_end_ti4", "blink_dagger_end")
    add_replacement("dagon_ti4", "dagon")
    add_replacement("radiant_fountain_regen_ti4", "radiant_fountain_regen")
    add_replacement("bottle_ti4", "bottle")

    add_replacement("teleport_start_ti5", "teleport_start")
    add_replacement("teleport_end_ti5", "teleport_end")
    add_replacement("teleport_start_lvl2_ti5", "teleport_start")
    add_replacement("teleport_end_lvl2_ti5", "teleport_end")
    add_replacement("blink_dagger_start_ti5", "blink_dagger_start")
    add_replacement("blink_dagger_end_ti5", "blink_dagger_end")
    add_replacement("blink_dagger_start_lvl2_ti5", "blink_dagger_start")
    add_replacement("blink_dagger_end_lvl2_ti5", "blink_dagger_end")
    add_replacement("dagon_ti5", "dagon")
    add_replacement("dagon_lvl2_ti5", "dagon")
    add_replacement("cyclone_ti5", "cyclone")
    add_replacement("radiant_fountain_regen_ti5", "radiant_fountain_regen")
    add_replacement("radiant_fountain_regen_lvl2_ti5", "radiant_fountain_regen")
    add_replacement("bottle_ti5", "bottle")

    forwarded_particle_replacements = OrderedDict()
    for system, default_system in particle_replacements.items():
        while default_system in particle_replacements:
            default_system = particle_replacements[default_system]
        forwarded_particle_replacements[system] = default_system

    return visuals, forwarded_particle_replacements

def get_particle_file_systems(d, units, npc_heroes):
    files = []

    with open(dota_file("particles/particles_manifest.txt"), "rt", encoding="utf-8") as s:
        l = s.readline().rstrip("\n")
        l = "\"" + l + "\""
        l += s.read()
    m = load(StringIO(l))
    for k, v in m["particles_manifest"]:
        assert k == "file", k
        if v.startswith("!"):
            v = v[1:]
        files.append(v)

    for id, item in chain(units["DOTAUnits"], npc_heroes["DOTAHeroes"]):
        if "ParticleFile" in item and item["ParticleFile"] not in files:
            files.append(item["ParticleFile"])

    with open(dota_file("scripts/precache.txt"), "rt", encoding="utf-8") as s:
        p = load(s)
        for k, v in p["precache"]:
            if k == "particlefile" and v not in files:
                files.append(v)

    for id, item in d["items_game"]["items"]:
        if "particle_file" in item and item["particle_file"] not in files:
            files.append(item["particle_file"])

    for id, v in d["items_game"]["attribute_controlled_attached_particles"]:
        if v.get("resource") is not None and v["resource"] not in files:
            files.append(v["resource"])

    for k, v in d["items_game"]["asset_modifiers"]:
        if "file" in v and v["file"] not in files:
            files.append(v["file"])

    particle_file_systems = OrderedDict()
    for file in files:
        if not exists(source_file(file)):
            print("Warning: referenced particle file '{}' doesn't exist.".format(file), file=stderr)
            continue
        particle_file_systems[file] = []
        pcf = PCF(include_attributes=False)
        with open(source_file(file), "rb") as s:
            pcf.unpack(s)
        for e in pcf["elements"]:
            if e["type"].data == "DmeParticleSystemDefinition":
                system_name = e["name"].data.lower()
                if system_name not in particle_file_systems[file]:
                    particle_file_systems[file].append(system_name)
                else:
                    print("Warning: double particle system definition '{}' in '{}'".format(system_name, file), file=stderr)

    return particle_file_systems

def edit_particle_file(f, file):
    p = PCF()
    with open(source_file(file), "rb") as s:
        p.unpack(s)
    p.minimize()
    main_element = p["elements"][0]
    assert main_element["type"].data == "DmElement"
    assert len(main_element.attribute) == 1
    main_attribute = main_element.attribute[0]
    assert main_attribute["name"].data == "particleSystemDefinitions"
    assert main_attribute["type"].data == 15
    psdl = main_attribute["data"]
    for i in range(len(psdl)):
        f(psdl, i)

    if nohats_dir:
        dest = nohats_file(file)
        dest_dir = dirname(dest)
        if not exists(dest_dir):
            makedirs(dest_dir)
        with open(dest, "wb") as s:
            p.full_pack(s)
    else:
        s = FakeWriteStream()
        p.full_pack(s)

def fix_particles(d, defaults, default_ids, visuals, units, npc_heroes):
    visuals, particle_replacements = get_particle_replacements(d, defaults, visuals, default_ids)

    particle_file_systems = get_particle_file_systems(d, units, npc_heroes)

    particlesystem_files = {}
    for file, systems in particle_file_systems.items():
        for system in systems:
            particlesystem_files.setdefault(system, [])
            particlesystem_files[system].append(file)

    file_replacements = OrderedDict()
    for system, default_system in particle_replacements.items():
        if system not in particlesystem_files:
            print("Warning: system '{}' is not in any particle file".format(system), file=stderr)
            continue
        system_files = particlesystem_files[system]
        if default_system is None:
            default_system_files = []
        else:
            default_system_files = particlesystem_files.get(default_system, [])
            if default_system_files == []:
                if "_active" in default_system or "_passive" in default_system:
                    # pseudo-system for item triggered particle effects
                    pass
                else:
                    print("Warning: default system '{}' is not in any particle file".format(default_system), file=stderr)

        for file in system_files:
            file_replacements.setdefault(file, OrderedDict())
            if default_system_files == []:
                file_replacements[file][system] = None
            else:
                file_replacements[file][system] = (default_system_files[0], default_system)

    for file, replacements in file_replacements.items():
        print("{}:".format(file))
        for system, replacement in replacements.items():
            if replacement is None:
                print("\t{} -> None".format(system))
            else:
                replacement_file, replacement_system = replacement
                print("\t{} -> {} ({})".format(system, replacement_system, replacement_file))

        def edit(psdl, i):
            psd = psdl[i].data
            assert psd["type"].data == "DmeParticleSystemDefinition"
            name = psd["name"].data.lower()
            if name in replacements:
                if replacements[name] is None:
                    psd.attribute.data = []
                else:
                    replacement_file, replacement_system = replacements[name]
                    o = PCF()
                    with open(source_file(replacement_file), "rb") as s:
                        o.unpack(s)
                    for e in o["elements"]:
                        if e["type"].data == "DmeParticleSystemDefinition" and e["name"].data.lower() == replacement_system:
                            psd.attribute.data = e.attribute.data
                            break
                    else:
                        assert False, "Could not find system {} in file {}".format(replacement_system, replacement_file)

                del replacements[name]

        edit_particle_file(edit, file)
        assert not replacements

    return visuals

def fix_skins(courier_model, flying_courier_model):
    skins = [
        courier_model,
        flying_courier_model,
        "models/heroes/bounty_hunter/bounty_hunter.mdl",
        "models/heroes/lina/lina.mdl",
        "models/heroes/legion_commander/legion_commander.mdl",
        ]
    for model in skins:
        m = MDL()
        with open(source_file(model), "rb") as s:
            m.unpack(s)
        assert m["numskinfamilies"] != 1, (model, m["numskinfamilies"])
        for i in range(1, m["numskinfamilies"].data):
            m["skin"].field[i].data = m["skin"].field[0].data
        copy_model_always(model, model)
        if nohats_dir is None:
            continue
        with open(nohats_file(model), "r+b") as s:
            s.seek(m["skinindex"].data)
            m["skin"].field.pack(s)

def fix_particle_color(npc_heroes):
    def get_key(l, name, value):
        l = [x for x in l if name in x and x[name].data == value]
        assert len(l) == 1, l
        return l[0]

    def edit1(psd):
        for name in ["initializers", "operators"]:
            a = get_key(psd.attribute, "name", name)
            assert a["type"].data == 15
            l = a["data"]
            for i in reversed(range(len(l))):
                attribute = l[i].data.attribute
                function_name = get_key(attribute, "name", "functionName")
                assert function_name["type"].data == 5
                if function_name["data"].data == "Remap Control Point to Vector":
                    control_point = get_key(attribute, "name", "input control point number")
                    assert control_point["type"].data == 2
                    assert control_point["data"].data == 15
                    del l[i]

        children = get_key(psd.attribute, "name", "children")
        assert children["type"].data == 15
        for child in children["data"]:
            real_child = get_key(child.data.attribute, "name", "child")
            edit1(real_child["data"].data)

    def edit(psdl, i):
        psd = psdl[i].data
        edit1(psd)

    for hero in ["terrorblade", "techies"]:
        particle_file = npc_heroes["DOTAHeroes"]["npc_dota_hero_"+hero]["ParticleFile"]
        print("{}".format(particle_file))
        edit_particle_file(edit, particle_file)

def fix_scaleform():
    if nohats_dir:
        makedirs(nohats_file("resource/flash3"))
    fix_scaleform_play()
    fix_scaleform_play_matchmaking_status()
    fix_scaleform_shared_heroselectorandloadout()
    fix_scaleform_challenges()

def find_methodbody(abcfile, instancename, methodname):
    for instance in abcfile["instance"]:
        if instance["name"].data["name"] == instancename:
            for trait in instance["trait"]:
                if trait["name"].data["name"] == methodname:
                    assert trait["kind"].data == 1
                    method_id = trait["method"].data
                    break
            else:
                assert False, "Can't find method {}".format(methodname)
            break
    else:
        assert False, "Can't find instance {}".format(instancename)
    for methodbody in abcfile["methodbody"]:
        if methodbody["method"].data == method_id:
            body = methodbody
            break
    else:
        assert False, "Can't find method body"
    return body

def edit_methodbody(abcfile, instancename, methodname, orig, edit, **kwargs):
    body = find_methodbody(abcfile, instancename, methodname)
    new_code, n = subn(orig, edit, body["code"].data, **kwargs)
    assert n == 1, n
    assert len(new_code) == len(body["code"].data)
    body["code"].data = new_code

def fix_scaleform_play():
    filename = "resource/flash3/play.gfx"
    print(filename)
    swf = ScaleFormSWF()
    with open(dota_file(filename), "rb") as s:
        swf.unpack(s)

    for tag in swf["content"]["tags"]:
        if tag["header"].data["tagcode"] == 82:
            abcfile = tag["content"]["abcdata"]
            edit_methodbody(abcfile, "MainTimeline", "BeginSetupAdvertisements", br"\xd1", b"\x27")
            edit_methodbody(abcfile, "MainTimeline", "updateAdPicker", br"\x62\x04\xd1\xad", b"\x02\x02\x02\x27")

    if nohats_dir:
        with open(nohats_file(filename), "wb") as s:
            swf.pack(s)

def fix_scaleform_play_matchmaking_status():
    filename = "resource/flash3/play_matchmaking_status.gfx"
    print(filename)
    swf = ScaleFormSWF()
    with open(dota_file(filename), "rb") as s:
        swf.unpack(s)

    for tag in swf["content"]["tags"]:
        if tag["header"].data["tagcode"] == 82:
            abcfile = tag["content"]["abcdata"]
            edit_methodbody(abcfile, "MainTimeline", "setChromeBrowserVisible", br"\xd1", b"\x27")

    if nohats_dir:
        with open(nohats_file(filename), "wb") as s:
            swf.pack(s)

def fix_scaleform_shared_heroselectorandloadout():
    filename = "resource/flash3/shared_heroselectorandloadout.gfx"
    print(filename)
    swf = ScaleFormSWF()
    with open(dota_file(filename), "rb") as s:
        swf.unpack(s)

    for tag in swf["content"]["tags"]:
        if tag["header"].data["tagcode"] == 82:
            abcfile = tag["content"]["abcdata"]
            edit_methodbody(abcfile, "MainTimeline", "setSuggestedItems", br"\x26", b"\x27", count=1)

    if nohats_dir:
        with open(nohats_file(filename), "wb") as s:
            swf.pack(s)

def fix_scaleform_challenges():
    filename = "resource/flash3/challenges.gfx"
    print(filename)
    swf = ScaleFormSWF()
    with open(dota_file(filename), "rb") as s:
        swf.unpack(s)

    for tag in swf["content"]["tags"]:
        if tag["header"].data["tagcode"] == 82:
            abcfile = tag["content"]["abcdata"]
            edit_methodbody(abcfile, "MainTimeline", "updateStatusSection", br"\xd1\x24\x00\xae", b"\x02\x02\x02\x27", count=1)

    if nohats_dir:
        with open(nohats_file(filename), "wb") as s:
            swf.pack(s)

def fix_effigies():
    peds = "models/heroes/pedestal/"
    ped_radiant = peds + "effigy_pedestal_radiant.mdl"
    ped_dire = peds + "effigy_pedestal_dire.mdl"

    # frost
    copy_model(ped_radiant, peds + "effigy_pedestal_frost_radiant.mdl")
    copy_model(ped_dire, peds + "effigy_pedestal_frosty_dire.mdl")

    # jade
    copy_model(ped_radiant, peds + "pedestal_effigy_jade.mdl")

    # ti5
    copy_model(ped_radiant, peds + "effigy_pedestal_ti5.mdl")
    copy_model(ped_dire, peds + "effigy_pedestal_ti5_dire.mdl")
    copy_model(ped_radiant, peds + "effigy_pedestal_ti5_lvl2.mdl")
    copy_model(ped_dire, peds + "effigy_pedestal_ti5_dire_lvl2.mdl")

if __name__ == "__main__":
    dota_dir = abspath(argv[1])
    try:
        nohats_dir = argv[2]
    except IndexError:
        nohats_dir = None
    try:
        seed_num = int(argv[3])
    except IndexError:
        seed_num = randint(0, 2**128 - 1)
    print("OS: {}".format(os_name))
    print("Python version: {}".format(version))
    print("Seed: {}".format(seed_num))
    seed(seed_num)
    if nohats_dir is not None:
        nohats_dir = abspath(nohats_dir)
        assert not exists(nohats_dir)
    nohats()
