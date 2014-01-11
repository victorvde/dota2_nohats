# Copyright (c) 2014 Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from binary import Struct, Magic, Format, Array, String, Pointer, DataPointer, Index, PrefixedArray, BaseField, getbytes
from struct import pack
try:
    from lzma import decompress, FORMAT_ALONE
except ImportError:
    from backports.lzma import decompress, FORMAT_ALONE

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
    def fields(self):
        self.F("method", Magic("LZMA"))
        self.F("uncompressed_size", Format("I"))
        self.F("compressed_size", Format("I"))

        self.F("scene_data", LZMAField(self["uncompressed_size"].data, self["compressed_size"].data))

class SceneSummary(Struct):
    def fields(self, strings):
        self.F("milliseconds", Format("I"))
        self.F("milliseconds_2", Format("I"))
        self.F("sounds", PrefixedArray(Format("I"), lambda: Index(strings, Format("I"))))

class SceneEntry(Struct):
    def fields(self, strings):
        self.F("namecrc", Format("I"))
        self.F("offset", Format("I"))
        self.F("length", Format("I"))
        # self.F("scenesummary", Format("I"))
        self.F("scenesummary", DataPointer(Format("I"), SceneSummary(strings)))

        self.F("scene", Pointer(self["offset"].data, Scene()))

class VSIF(Struct):
    def fields(self):
        self.F("magic", Magic("VSIF"))
        self.F("version", Format("I"))
        assert self["version"].data == 3
        self.F("nscenes", Format("I"))
        self.F("nstrings", Format("I"))
        self.F("scenesoffset", Format("I"))
        self.F("strings", Array(self["nstrings"].data, lambda: DataPointer(Format("I"), String())))

        self.F("scenes", Pointer(self["scenesoffset"].data, Array(self["nscenes"].data, lambda: SceneEntry(self["strings"]))))

if __name__ == "__main__":
    from sys import argv
    d = VSIF()
    with open(argv[1], "rb") as s:
        d.unpack(s)
    import json
    print(json.dumps(d.data, indent=4))
