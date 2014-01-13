# Copyright (c) 2014 Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from binary import Struct, Magic, Format, Array, String, Pointer, DataPointer, Index, PrefixedArray, BaseField, getbytes
from struct import pack
from lzma import decompress, FORMAT_ALONE

class LZMAField(BaseField):
    def __init__(self, uncompressed_size, compressed_size):
        self.uncompressed_size = uncompressed_size
        self.compressed_size = compressed_size

    def unpack_data(self, s):
        props = getbytes(s, 5)
        data = getbytes(s, self.compressed_size)
        alone_data = props + pack("Q", self.uncompressed_size) + data
        unpacked = decompress(alone_data, FORMAT_ALONE)
        return unpacked

class Scene(Struct):
    def __init__(self, strings, length):
        self.strings = strings
        self.length = length

    def fields(self):
        self.F("method", Magic("LZMA"))
        self.F("uncompressed_size", Format("I"))
        self.F("compressed_size", Format("I"))

        self.F("scene_data", LZMAField(self["uncompressed_size"].data, self["compressed_size"].data))

class SceneSummary(Struct):
    def __init__(self, strings):
        self.strings = strings

    def fields(self):
        self.F("milliseconds", Format("I"))
        self.F("milliseconds_2", Format("I"))
        self.F("sounds", PrefixedArray(Format("I"), lambda: Index(self.strings, Format("I"))))

class SceneEntry(Struct):
    def __init__(self, strings):
        self.strings = strings

    def fields(self):
        self.F("namecrc", Format("I"))
        self.F("offset", Format("I"))
        self.F("length", Format("I"))
        # self.F("scenesummary", Format("I"))
        self.F("scenesummary", DataPointer(Format("I"), SceneSummary(self.strings)))

        self.F("scene", Pointer(self["offset"].data, Scene(self.strings, self["length"].data)))

class VSIF(Struct):
    def fields(self):
        self.F("magic", Magic("VSIF"))
        self.F("version", Format("I"))
        assert self["version"].data == 3, "Expected version 3, got {}".format(self["version"].data)
        self.F("nscenes", Format("I"))
        self.F("nstrings", Format("I"))
        self.F("scenesoffset", Format("I"))
        self.F("strings", Array(self["nstrings"].data, lambda: DataPointer(Format("I"), String())))

        self.F("scenes", Pointer(self["scenesoffset"].data, Array(self["nscenes"].data, lambda: SceneEntry(self["strings"]))))

if __name__ == "__main__":
    from sys import argv, stderr
    from zlib import crc32
    from os import makedirs
    from os.path import dirname
    from re import match
    from itertools import chain

    d = VSIF()
    with open(argv[1], "rb") as s:
        d.unpack(s)

    names = set()
    with open(argv[2], "rt") as s:
        for line in s:
            name = line.rstrip()
            names.add(name)

    generated_names = set()
    dirs = set()
    for name in names:
        m = match(r"scenes/([a-z0-9_]+)/", name)
        if m:
            dirs.add(m.group(1))
    for scene in d["scenes"]:
        sounds = scene["scenesummary"]["sounds"].data
        for sound in sounds:
            for dir in dirs:
                if sound.startswith(dir):
                    generated_name = "scenes/{}/{}.vcd".format(dir, sound)
                    generated_names.add(generated_name)

    crcs = {}
    for name in chain(names, generated_names):
        crc = crc32(name.replace('/', '\\').encode())
        if crc in crcs:
            if crcs[crc] != name:
                print("CRC {:x} for both '{}' and '{}'".format(crc, crcs[crc], name), file=stderr)
        else:
            crcs[crc] = name

    found = 0
    not_found = 0
    for scene in d["scenes"]:
        crc = scene["namecrc"].data
        if crc in crcs:
            found += 1
            name = crcs[crc]
        else:
            not_found += 1
            # print("Can't find CRC {:x} with sounds {}".format(crc, scene["scenesummary"]["sounds"].data))
            name = "scenes/unknown-{:x}.vcd".format(crc)

        dir = dirname(name)
        if dir:
            makedirs(dir, exist_ok=True)
        with open(name, "wb") as s:
            s.write(scene["scene"]["scene_data"].data)

    print("Found {} scene names, couldn't find {} scene names".format(found, not_found))
