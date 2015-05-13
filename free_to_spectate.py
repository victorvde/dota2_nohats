# Copyright (c) Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from vdf import load
from sys import argv
from operator import itemgetter

with open(argv[1] + "/scripts/items/items_game.txt", "rt", encoding="utf-8") as input:
    d = load(input)
fts = {}
for k, v in d["items_game"]["items"]:
    tool = v.get("tool")
    if tool is not None:
        if tool.get("type") == "league_view_pass":
            usage = tool["usage"]
            free_to_spectate = usage.get("free_to_spectate")
            if free_to_spectate == "1":
                tier = usage["tier"]
                location = usage.get("location", "")
                if location == "unset":
                    location = ""
                league_id = usage["league_id"]
                url = v["tournament_url"]
                name = v["name"]
                date = v["creation_date"]
                fts.setdefault(tier, {}).setdefault(location, []).append({"name": name, "url": url, "date": date, "id": league_id})
            else:
                assert free_to_spectate in [None, "0"], v
for tier in sorted(fts, key=lambda t: ["premium", "professional", "amateur"].index(t)):
    print()
    print("# {}".format(tier))
    for location in sorted(fts[tier]):
        if location:
            print()
            print("## {}".format(location))
        for d in sorted(fts[tier][location], key=itemgetter("date"), reverse=True):
            print("* [{}](http://www.dotabuff.com/esports/leagues/{})".format(d["name"], d["id"]))
