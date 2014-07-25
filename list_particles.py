# Copyright (c) 2014 Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from argparse import ArgumentParser, FileType
from pcf import PCF

def main():
    parser = ArgumentParser(description="List particle systems in particle files")
    parser.add_argument("input_file", type=FileType("rb"), help="Input file, e.g. input.pcf")
    args = parser.parse_args()

    p = PCF(include_attributes=False)
    p.unpack(args.input_file)

    for e in p["elements"]:
        if e["type"].data == "DmeParticleSystemDefinition":
            print(e["name"].data.lower())

if __name__ == "__main__":
    main()
