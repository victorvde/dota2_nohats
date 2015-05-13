# Copyright (c) Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from argparse import ArgumentParser, FileType
from collections import OrderedDict
from pcf import PCF
from os.path import expanduser

def main():
    parser = ArgumentParser(description="Replace or delete particle systems in particle files")
    parser.add_argument("output_file", type=FileType("wb"), help="Output file, e.g. output.pcf")
    parser.add_argument("input_file", type=FileType("rb"), help="Input file, e.g. input.pcf")
    parser.add_argument("--delete", "-d", action="append", metavar="NAME", default=[], help="Replace particle system NAME with an empty particle system.")
    parser.add_argument("--replace", "-r", nargs=3, action="append", metavar=("NAME", "SOURCE_FILE", "SOURCE_NAME"), help="Replace particle system NAME with particle system SOURCE_NAME from SOURCE_FILE.", default=[])
    parser.add_argument("--file", "-f", type=FileType("r"), help="Read the lines of FILE for commands. Line format: COMMAND NAME [SOURCE_FILE SOURCE_NAME], where COMMAND is delete or replace.")
    args = parser.parse_args()

    replacements = OrderedDict()
    def add_replacement(name, r):
        assert name not in replacements, "Double definition for particle system {}".format(name)
        replacements[name] = r

    for name in args.delete:
        add_replacement(name, None)
    for (name, source_file, source_name) in args.replace:
        add_replacement(name, (source_file, source_name))

    if args.file:
        for line in args.file:
            l = line.split()
            assert len(l) >= 1, "No command in line: {}".format(line)
            command = l[0]

            if command == "delete":
                assert len(l) == 2, "Wrong number of arguments in line: {}".format(line)
                add_replacement(l[1], None)
            elif command == "replace":
                assert len(l) == 4, "Wrong number of arguments in line: {}".format(line)
                add_replacement(l[1], (expanduser(l[2]), l[3]))
            else:
                assert False, "Invalid command {} in line: {}".format(command, line)

    p = PCF()
    p.unpack(args.input_file)
    p.minimize()

    main_element = p["elements"][0]
    assert main_element["type"].data == "DmElement"
    assert len(main_element.attribute) == 1
    main_attribute = main_element.attribute[0]
    assert main_attribute["name"].data == "particleSystemDefinitions"
    assert main_attribute["type"].data == 15
    psl = main_attribute["data"]
    for ps in psl:
        psd = ps.data
        assert psd["type"].data == "DmeParticleSystemDefinition"
        name = psd["name"].data.lower()
        if name in replacements:
            if replacements[name] is None:
                psd.attribute.data = []
            else:
                replacement_file, replacement_system = replacements[name]
                o = PCF()
                with open(replacement_file, "rb") as s:
                    o.unpack(s)
                for e in o["elements"]:
                    if e["type"].data == "DmeParticleSystemDefinition" and e["name"].data.lower() == replacement_system:
                        psd.attribute.data = e.attribute.data
                        break
                else:
                    assert False, "Could not find system {} in file {}".format(replacement_system, replacement_file)

            del replacements[name]

    p.full_pack(args.output_file)

if __name__ == "__main__":
    main()
