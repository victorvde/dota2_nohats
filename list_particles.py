# Copyright (c) 2014 Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from argparse import ArgumentParser, FileType
from pcf import PCF
from collections import Counter

def main():
    parser = ArgumentParser(description="List particle systems in particle files")
    parser.add_argument("input_file", type=FileType("rb"), help="Input file, e.g. input.pcf")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    p = PCF(include_attributes=args.full)
    p.unpack(args.input_file)

    if not args.full:
        for e in p["elements"]:
            if e["type"].data == "DmeParticleSystemDefinition":
                print(e["name"].data.lower())
    else:
        main_element = p["elements"][0]
        assert main_element["type"].data == "DmElement"
        assert len(main_element.attribute) == 1
        main_attribute = main_element.attribute[0]
        assert main_attribute["name"].data == "particleSystemDefinitions"
        assert main_attribute["type"].data == 15
        psdl = main_attribute["data"]
        counter = Counter()
        for i in range(len(psdl)):
            psd = psdl[i].data
            recursive_count(psd, counter)
        for i in range(len(psdl)):
            psd = psdl[i].data
            name = psd["name"].data.lower()
            if counter[name] != 2:
                recursive_print(psd, 0, counter)

def recursive_count(psd, counter):
    name = psd["name"].data.lower()
    counter.update([name])
    if counter[name] > 1:
        return
    children = get_key(psd.attribute, "name", "children")
    assert children["type"].data == 15
    for child in children["data"]:
        real_child = get_key(child.data.attribute, "name", "child")
        name = real_child["data"].data["name"].data.lower()
        recursive_count(real_child["data"].data, counter)

def recursive_print(psd, indent, counter):
    print("{}{}".format("    "*indent, psd["name"].data.lower()))

    children = get_key(psd.attribute, "name", "children")
    assert children["type"].data == 15
    for child in children["data"]:
        real_child = get_key(child.data.attribute, "name", "child")
        name = real_child["data"].data["name"].data.lower()
        if counter[name] == 2:
            recursive_print(real_child["data"].data, indent+1, counter)
        else:
            print("{}{}".format("    "*(indent+1), name))

def get_key(l, name, value):
    l = [x for x in l if name in x and x[name].data == value]
    assert len(l) == 1, l
    return l[0]

if __name__ == "__main__":
    main()
