from vdf import load
from collections import OrderedDict
from sys import argv
import csv

with open(argv[1] + "/scripts/npc/npc_heroes.txt", "rt", encoding="utf-8") as input:
    d = load(input)

with open(argv[2] + "dota/resource/dota_english.txt", "rt", encoding="utf-16") as input:
    l = load(input)

fields = OrderedDict([
    ("id", "HeroID"),
    ("name",  None),
    ("team",  "Team"),
    ("cm_enabled",  "CMEnabled"),
    ("base_armor",  "ArmorPhysical"),
    ("magical_resistance",  "MagicalResistance"),
    ("ranged",  None),
    ("attack_damage_min",  "AttackDamageMin"),
    ("attack_damage_max",  "AttackDamageMax"),
    ("base_attack_time",  "AttackRate"),
    ("attack_range",  "AttackRange"),
    ("projectile_speed",  "ProjectileSpeed"),
    ("primary_attribute",  None),
    ("base_str",  "AttributeBaseStrength"),
    ("gain_str",  "AttributeStrengthGain"),
    ("base_int",  "AttributeBaseIntelligence"),
    ("gain_int",  "AttributeIntelligenceGain"),
    ("base_agi",  "AttributeBaseAgility"),
    ("gain_agi",  "AttributeAgilityGain"),
    ("base_hp",  "StatusHealth"),
    ("base_hp_regen",  "StatusHealthRegen"),
    ("base_mana",  "StatusMana"),
    ("base_mana_regen",  "StatusManaRegen"),
    ("movement_speed",  "MovementSpeed"),
    ("movement_turnrate",  "MovementTurnRate"),
    ("day_vision",  "VisionDaytimeRange"),
    ("night_vision",  "VisionNighttimeRange"),
    ("ardm_disabled",  "ARDMDisabled"),
    ])

heroes = OrderedDict()

for internal_name, data in d["DOTAHeroes"]:
    if internal_name == "Version":
        continue

    def get_key(hero_data, name):
        value = hero_data.get(name)
        if value is None:
            value = d["DOTAHeroes"]["npc_dota_hero_base"][name]
        return value

    if get_key(data, "Enabled") == "0":
        continue

    heroes[internal_name] = OrderedDict()
    for k, v in fields.items():          
        if v is not None:
            heroes[internal_name][k] = get_key(data, v)
        elif k == "name":
            heroes[internal_name][k] = l["lang"]["Tokens"][internal_name]
        elif k == "ranged":
            cap = get_key(data, "AttackCapabilities")
            if cap == "DOTA_UNIT_CAP_RANGED_ATTACK":
                ranged = "1"
            elif cap == "DOTA_UNIT_CAP_MELEE_ATTACK":
                ranged = "0"
            else:
                assert False, cap
            heroes[internal_name][k] = ranged
        elif k == "primary_attribute":
            primary = get_key(data, "AttributePrimary")
            if primary == "DOTA_ATTRIBUTE_STRENGTH":
                attr = "str"
            elif primary == "DOTA_ATTRIBUTE_INTELLECT":
                attr = "int"
            elif primary == "DOTA_ATTRIBUTE_AGILITY":
                attr = "agi"
            else:
                assert False, primary
            heroes[internal_name][k] = attr

with open("hero_stats.csv", "w", newline="") as csvfile:
    w = csv.DictWriter(csvfile, fieldnames=fields.keys())

    w.writeheader()
    for k, v in heroes.items():
        w.writerow(v)
