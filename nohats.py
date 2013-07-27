from vdf import process_items_game
from collections import OrderedDict

def get_hero(d, item):
    if "used_by_heroes" not in item or item["used_by_heroes"] in ["0", "1"]:
        return None
    heroes = item["used_by_heroes"].keys()
    assert len(heroes) == 1
    hero = heroes[0]
    assert item["used_by_heroes"][hero] == "1"
    return hero

def get_slot(d, item):
    slot = item.get("item_slot")
    if slot is None and "prefab" in item:
        slot = d["items_game"]["prefabs"][item["prefab"]]["item_slot"]
    assert slot is not None
    return slot

def conditional_set(item, name, value, override):
    if value is None:
        if name in item:
            item[name] = override
    else:
        item[name] = value

def remove_hats(d):
    defaults = {}
    for id, item in d["items_game"]["items"].iteritems():
        if item.get("prefab") == "default_item":
            hero = get_hero(d, item)
            assert hero is not None
            slot = get_slot(d, item)
            defaults[(hero, slot)] = (item.get("model_player"), item.get("particle_file"), item.get("visuals"))

    for id, item in d["items_game"]["items"].iteritems():
        if id == "default" or item.get("prefab") == "default_item":
            continue
        hero = get_hero(d, item)
        slot = get_slot(d, item)
        if hero is None:
            assert slot == "none" or slot in d["items_game"]["player_loadout_slots"].values(), slot
        model_player, particle_file, visuals = defaults.get((hero, slot), (None, None, None))
        conditional_set(item, "model_player", model_player, "")
        conditional_set(item, "particle_file", particle_file, "")
        conditional_set(item, "visuals", visuals, OrderedDict())
        conditional_set(item, "portraits", None, OrderedDict())

if __name__ == "__main__":
    process_items_game(remove_hats)