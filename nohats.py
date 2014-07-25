# Copyright (c) 2013 Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from vdf import load, dump
from os.path import abspath, exists, dirname, join
from sys import argv, stdout, stderr, version
from shutil import copyfile
from os import makedirs, listdir, walk, name as os_name
from kvlist import KVList
from mdl import MDL
from pcf import PCF
from socket import parse_socket_value
from wave import open as wave_open
from collections import OrderedDict
from io import StringIO
from itertools import chain
from binary import FakeWriteStream
from random import randint, seed

def header(s):
    print("== {} ==".format(s))

def dota_file(p):
    return join(dota_dir, p.lower().replace("\\", "/"))

def nohats_file(p):
    return join(nohats_dir, p)

def source_file(src):
    if exists(nohats_file(src)):
        src = nohats_file(src)
    else:
        src = dota_file(src)
    return src

def nohats():
    header("Loading items_game.txt")
    with open(dota_file("scripts/items/items_game.txt"), "rt") as input:
        d = load(input)

    header("Getting defaults")
    defaults = get_defaults(d)
    default_ids = set(defaults.values())
    header("Getting visuals")
    visuals = get_visuals(d, default_ids)
    visuals = filter_visuals(visuals)
    header("Getting sockets")
    sockets = get_sockets(d)
    header("Loading npc_units.txt")
    units = get_units()
    header("Loading npc_heroes.txt")
    npc_heroes = get_npc_heroes()

    header("Fixing simple model files")
    fix_models(d, defaults, default_ids)
    header("Fixing alternate style models")
    visuals = fix_style_models(d, visuals, defaults)
    header("Fixing hex models")
    visuals = fix_hex_models(visuals)
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
    header("Fixing alternate base models")
    visuals = fix_base_models(visuals, npc_heroes)
    header("Fixing animations")
    visuals = fix_animations(d, visuals, npc_heroes)
    header("Fixing skins")
    courier_model = units["DOTAUnits"]["npc_dota_courier"]["Model"]
    flying_courier_model = units["DOTAUnits"]["npc_dota_flying_courier"]["Model"]
    fix_skins(courier_model, flying_courier_model)
    header("Fixing couriers")
    visuals = fix_couriers(visuals, units, courier_model)
    visuals = fix_flying_couriers(visuals, units, flying_courier_model)
    header("Fixing Terrorblade color")
    fix_terrorblade_color(npc_heroes)
    header("Fixing particles")
    visuals = fix_particles(d, defaults, default_ids, visuals, sockets, units, npc_heroes)

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
    assert len(heroes) == 1
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
            if slot == "weather":
                continue
            assert slot is not None, id
            hero = get_hero(d, item)
            assert hero is not None, id
            if (hero, slot) in defaults:
                print("Warning: id '{}' is a duplicate default for '{}'".format(id, (hero, slot)), file=stderr)
            else:
                defaults[(hero, slot)] = id
            if "visuals" in item:
                if "additional_wearable" in item["visuals"]:
                    additional_id, _ = find_item_by_name(d, item["visuals"]["additional_wearable"])
                    defaults[(hero, slot + "_additional_wearable")] = additional_id
    return defaults

def get_default_item(d, defaults, item):
    hero = get_hero(d, item)
    slot = get_slot(d, item)
    default_id = defaults.get((hero, slot))
    if default_id is None:
        return None
    default_item = get_item(d, default_id)
    return default_item

def copy(src, dest):
    print("copy '{}' to '{}'".format(src, dest))
    if nohats_dir is None:
        return
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
    elif exists(dota_file(dest + ".cloth")):
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
        if "visuals" in item:
            if "additional_wearable" in item["visuals"]:
                _, additional_item = find_item_by_name(d, item["visuals"]["additional_wearable"])
                _, additional_default_item = find_item_by_name(d, default_item["visuals"]["additional_wearable"])
                fix_item_model(additional_item, additional_default_item, "model_player")

def get_visuals(d, default_ids):
    # get visual modifiers
    visuals = []
    for id, item in d["items_game"]["items"]:
        if id == "default" or id in default_ids:
            continue
        if "visuals" in item:
            for k, v in item["visuals"]:
                visuals.append((id, k, v))

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
        "additional_wearable",
        "player_card",
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
        "weather",
        "soundscape",
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
    asset = visual.pop("asset")
    modifier = visual.pop("modifier")
    if "frequency" in visual:
        frequency = visual.pop("frequency")
        assert frequency == "1"
    if "style" in visual:
        style = visual.pop("style")
    assert len(visual) == 0, list(visual.keys())
    return (asset, modifier)

def assetmodifier(iterable):
    for id, key, visual in iterable:
        yield assetmodifier1(visual)

def fix_hex_models(visuals):
    sound_visuals, visuals = filtersplit(visuals, isvisualtype("hex_model"))
    for asset, modifier in assetmodifier(sound_visuals):
        assert asset == "hex"
        copy_model("models/props_gameplay/frog.mdl", modifier)
    return visuals

def sound_files(sound):
    prefix_chars = "*#@<>^)(}$!?"
    if "wave" in sound:
        return [sound["wave"].lstrip(prefix_chars)]
    elif "rndwave" in sound:
        return [wave.lstrip(prefix_chars) for wave in sound["rndwave"].values()]

def copy_sound(src, dest):
    if src.endswith(".wav") and dest.endswith(".wav"):
        copy_wave(src, dest)
    elif src.endswith(".mp3") and dest.endswith(".mp3"):
        copy(src, dest)
    else:
        print("Unknown sound extension copy for '{}' to '{}'".format(src, dest), file=stderr)
        #assert False, "Unknown sound extension copy for '{}' to '{}'".format(src, dest)

def copy_wave(src, dest):
    print("copy wave '{}' to '{}'".format(src, dest))
    src = source_file(src)
    input = wave_open(src, "rb")
    try:
        frames_available = input.getnframes()
        # fill to two seconds because of noise
        frames_needed = 2 * input.getframerate()
        empty_frame = b"\0" * input.getsampwidth() * input.getnchannels()
        filler_frames = empty_frame * max(frames_needed - frames_available, 0)

        if nohats_dir is None:
            return
        dest = nohats_file(dest)
        dest_dir = dirname(dest)
        if not exists(dest_dir):
            makedirs(dest_dir)

        output = wave_open(dest, "wb")
        try:
            output.setparams(input.getparams())
            output.writeframes(input.readframes(frames_available) + filler_frames)
        finally:
            output.close()
    finally:
        input.close()

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
            with open(join(root, f), "rt") as s:
                part_sounds = load(s)
            sounds.update(list(part_sounds))

    # fix sound visuals
    sound_visuals, visuals = filtersplit(visuals, isvisualtype("sound"))
    for asset, modifier in assetmodifier(sound_visuals):
        asset_files = sound_files(sounds[asset])
        modifier_files = sound_files(sounds[modifier])
        for modifier_file in modifier_files:
            copy_sound("sound/" + asset_files[0], "sound/" + modifier_file)

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
    ability_icon_visuals, visuals = filtersplit(visuals, isvisualtype("ability_icon_replacement"))
    for asset, modifier in assetmodifier(ability_icon_visuals):
        image_dir = "resource/flash3/images/spellicons"
        copy(image_dir + "/" + asset + ".png", image_dir + "/" + modifier + ".png")

    return visuals

def get_units():
    # get unit model list
    with open(dota_file("scripts/npc/npc_units.txt"), "rt") as input:
        units = load(input)
    return units

def fix_summons(visuals, units, d, default_ids):
    # get default entity_model (tiny's tree)
    default_entity_models = {}
    for default_id in default_ids:
        item = d["items_game"]["items"][default_id]
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
    assets = []
    courier_visuals, visuals = filtersplit(visuals, isvisualtype("courier"))
    for asset, modifier in assetmodifier(courier_visuals):
        if asset not in assets:
            assets.append(asset)
    for asset in assets:
        copy_model(courier_model, asset)
    return visuals

def fix_flying_couriers(visuals, units, flying_courier_model):
    assets = []
    flying_courier_visuals, visuals = filtersplit(visuals, isvisualtype("courier_flying"))
    for asset, modifier in assetmodifier(flying_courier_visuals):
        if asset not in assets:
            assets.append(asset)
    for asset in assets:
        copy_model(flying_courier_model, asset)

    return visuals

def get_npc_heroes():
    with open(dota_file("scripts/npc/npc_heroes.txt"), "rt") as input:
        npc_heroes = load(input)
    return npc_heroes

def get_sockets(d):
    sockets = []
    for id, item in d["items_game"]["items"]:
        for key, attribute in item.get("attributes", []):
            if attribute.get("attribute_class") == "socket":
                sockets.append((id, parse_socket_value(attribute["value"])))
    return sockets

def fix_animations(d, visuals, npc_heroes):
    ignored = ["ACT_DOTA_TAUNT", "ACT_DOTA_LOADOUT"]

    item_activities = set()

    activity_visuals, visuals = filtersplit(visuals, isvisualtype("activity"))
    for id, key, visual in activity_visuals:
        asset, modifier = assetmodifier1(visual)
        item_activities.add(modifier)

    for id, gem in d["items_game"]["anim_modifiers"]:
        modifier = gem["name"]
        item_activities.add(modifier)

    for k, v in npc_heroes["DOTAHeroes"]:
        if k == "Version":
            continue
        model = v["Model"]
        if not exists(source_file(model)):
            continue

        mung_offsets = set()
        mung_sequence_names = set()
        model_parsed = MDL()
        with open(source_file(model), "rb") as s:
            model_parsed.unpack(s)
        for sequence in model_parsed.data["localsequence"]:
            if sequence["activitynameindex"][1] in ignored:
                continue
            for activitymodifier in sequence["activitymodifier"]:
                if activitymodifier["szindex"][1] in item_activities:
                    mung_offsets.add(activitymodifier["szindex"][0])
                    mung_sequence_names.add(sequence["labelindex"][1])

        if not mung_offsets:
            continue

        copy_model_always(model, model)
        for mung_sequence_name in sorted(list(mung_sequence_names)):
            print("Munging sequence '{}'".format(mung_sequence_name))
        if nohats_dir is None:
            continue
        with open(nohats_file(model), "r+b") as s:
            for offset in mung_offsets:
                s.seek(offset)
                assert s.read(1) not in [b"X", b""]
                s.seek(offset)
                s.write(b"X")

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

def get_particle_replacements(d, defaults, visuals, sockets, default_ids):
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
            if default_pss:
                default_ps = default_pss.pop(0)
            else:
                default_ps = None
            add_replacement(ps, default_ps)

    particle_visuals, visuals = filtersplit(visuals, isvisualtype("particle"))
    for id, k, v in particle_visuals:
        asset, modifier = assetmodifier1(v)
        item = get_item(d, id)
        add_replacement(modifier.lower(), asset.lower())

    for k, v in d["items_game"]["attribute_controlled_attached_particles"]:
        system_name = v["system"].lower()
        if system_name.startswith("courier_") and "resource" in v and v["resource"].startswith("particles/econ/courier/"):
            add_replacement(system_name, None)

    for k, v in d["items_game"]["particle_modifiers"]:
        if "num_effects" in v:
            n = int(v["num_effects"])
            i = 0
            while n > 0:
                l = str(i)
                if l in v:
                    n -= 1
                    u = v[l]
                    add_replacement(u["modifier"].lower(), u["effect"].lower())
                i += 1
        else:
            add_replacement(v["modifier"].lower(), v["effect"].lower())

    for id, socket in sockets:
        if "effect" in socket:
            effect_id = socket["effect"]
            effect = d["items_game"]["attribute_controlled_attached_particles"][effect_id]["system"].lower()
            add_replacement(effect, None)

    # hard-coded stuff
    add_replacement("terrorblade_arcana_enemy_death", None)
    add_replacement("teleport_start_ti4", "teleport_start")
    add_replacement("teleport_end_ti4", "teleport_end")
    add_replacement("blink_dagger_start_ti4", "blink_dagger_start")
    add_replacement("blink_dagger_end_ti4", "blink_dagger_end")
    add_replacement("dagon_ti4", "dagon")
    add_replacement("radiant_fountain_regen_ti4", "radiant_fountain_regen")
    add_replacement("bottle_ti4", "bottle")

    forwarded_particle_replacements = OrderedDict()
    for system, default_system in particle_replacements.items():
        while default_system in particle_replacements:
            default_system = particle_replacements[default_system]
        forwarded_particle_replacements[system] = default_system

    return visuals, forwarded_particle_replacements

def get_particle_file_systems(d, units, npc_heroes):
    files = []

    with open(dota_file("particles/particles_manifest.txt"), "rt") as s:
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

    with open(dota_file("scripts/precache.txt"), "rt") as s:
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

    for k, v in d["items_game"]["particle_modifiers"]:
        if v["file"] not in files:
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
        s = FakeWriteStream(0, file)
        p.full_pack(s)

def fix_particles(d, defaults, default_ids, visuals, sockets, units, npc_heroes):
    visuals, particle_replacements = get_particle_replacements(d, defaults, visuals, sockets, default_ids)

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

def fix_terrorblade_color(npc_heroes):
    particle_file = npc_heroes["DOTAHeroes"]["npc_dota_hero_terrorblade"]["ParticleFile"]

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

    edit_particle_file(edit, particle_file)

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
