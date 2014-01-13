# Copyright (c) 2014 Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from binary import Struct, Magic, Format, Array, String, Pointer, DataPointer, Index, PrefixedArray, BaseField, Mapping, Flags, getbytes
from struct import pack
from lzma import decompress, FORMAT_ALONE

from itertools import chain
from os import makedirs
from os.path import dirname
from re import match
from sys import argv, stderr
from zlib import crc32

from pprint import pprint

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
    def fields(self, strings):
        self.F("milliseconds", Format("I"))
        self.F("milliseconds_2", Format("I"))
        self.F("sounds", PrefixedArray(Format("I"), lambda: Index(self.strings, Format("I"))))

class SceneEntry(Struct):
    def fields(self, strings):
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

class ScaledField(BaseField):
    def __init__(self, field, scale):
        self.field = field
        self.scale = scale

    def unpack_data(self, s):
        data = self.field.unpack_data(s)
        return data / scale

class BVCDTag(Struct):
    def fields(self, strings, paramfield):
        self.F("name", Index(strings, Format("H")))
        self.F("param", paramfield)

class BVCDRamp(Struct):
    def fields(self):
        self.F("p", Format("f"))
        self.F("t", ScaledField(Format("f"), 255.))

class BVCDFlexSample(Struct):
    curve_types = [
        "default",
        "catmullrom_normalize_x",
        "easein",
        "easeout",
        "easeinout",
        "bspline",
        "linear_interp",
        "kochanek",
        "kochanek_early",
        "kochanek_late",
        "simple_cubic",
        "catmullrom",
        "catmullrom_normalize",
        "catmullrom_tangent",
        "exponential_decay",
        "hold",
        ]

    def fields(self):
        self.F("p", Format("f"))
        self.F("t", ScaledField(Format("f"), 255.))
        self.F("from_type", Mapping(Format("B"), self.curve_types))
        self.F("to_type", Mapping(Format("B"), self.curve_types))

class BVCDFlexTrack(Struct):
    flag_types = [
        (1, "disabled"),
        (2, "combo"),
    ]

    def fields(self, strings):
        self.F("name", Index(strings, Format("H")))
        self.F("flags", Flags(Format("B"), self.flag_types))
        self.F("range", Format("ff"))
        self.F("samples", PrefixedArray(Format("H"), BVCDFlexSample))
        if "combo" in self["flags"].data:
            self.F("combo_samples", PrefixedArray(Format("H"), BVCDFlexSample))

class BVCDEvent(Struct):
    event_types = [
        "unspecified",
        "section",
        "expression",
        "lookat",
        "moveto",
        "speak",
        "gesture",
        "sequence",
        "face",
        "firetrigger",
        "flexanimation",
        "subscene",
        "loop",
        "interrupt",
        "stoppoint",
        "permitresponses",
        "generic",
    ]

    flag_types = [
        (0x1, "resumecondition"),
	    (0x2, "lockbodyfacing"),
	    (0x4, "fixedlength"),
        (0x8, "inactive"),
		(0x10, "forceshortmovement"),
        (0x20, "playoverscript"),
    ]

    cc_flag_types = [
        (1, "cc_usingcombinedfile"),
        (2, "cc_combinedusesgender"),
        (4, "cc_noattenuate"),
    ]

    def fields(self, strings):
        self.F("type", Mapping(Format("B"), self.event_types))
        self.F("name", Index(strings, Format("H")))
        self.F("time", Format("ff"))
        self.F("params", Array(3, lambda: Index(strings, Format("H"))))
        self.F("ramp", PrefixedArray(Format("B", BVCDRamp)))
        self.F("flags", Flags(Format("B"), self.flag_types))
        self.F("distancetotarget", Format("f"))
        self.F("tags", PrefixedArray(Format("B"), lambda: BVCDTag(strings, ScaledField(Format("B"), 255.))))
        self.F("flextimingtags", PrefixedArray(Format("B"), lambda: BVCDTag(strings, ScaledField(Format("B"), 255.))))
        self.F("shifted_time", PrefixedArray(Format("B"), lambda: BVCDTag(strings, ScaledField(Format("H"), 4096.))))
        self.F("playback_time", PrefixedArray(Format("B"), lambda: BVCDTag(strings, ScaledField(Format("H"), 4096.))))
        if self["type"].data == "gesture":
            self.F("sequenceduration", Format("f"))
        self.F("relativetag", PrefixedArray(Format("B"), lambda: BVCDTag(strings, Index(strings, Format("H")))))

        self.F("flex", PrefixedArray(Format("B"), lambda: BVCDFlexTrack(strings)))

        if self["type"].data == "loop":
            self.F("loopcount", Format("B"))

        if self["type"].data == "speak":
            self.F("cctype", Format("B"))
            self.F("cctoken", Index(strings, Format("H")))
            self.F("ccflags", Flags(Format("B"), self.cc_flag_types))

class BVCD(Struct):
    def fields(self):
        self.F("magic", Magic("bvcd"))
        self.F("version", Format("B"))
        assert self["version"].data == 4, "Expected version 4, got {}".format(self["version"].data)
        self.F("unknown", Format("I"))

        self.F("events", PrefixedArray(Format("B"), BVCDEvent))
        # self.F("actors", PrefixedArray(Format("B"), BVCDActors))

def create_crc_mapping(d, scene_list):
    names = set()
    with open(scene_list, "rt") as s:
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

    return crcs

def unpack(vsif, scene_list):
    d = VSIF()
    with open(vsif, "rb") as s:
        d.unpack(s)

    crcs = create_crc_mapping(d, scene_list)

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
            name = "scenes/unknown-{:08x}.vcd".format(crc)

        dir = dirname(name)
        if dir:
            makedirs(dir, exist_ok=True)
        with open(name, "wb") as s:
            s.write(scene["scene"]["scene_data"].data)

    print("Found {} scene names, couldn't find {} scene names".format(found, not_found))

if __name__ == "__main__":
    # unpack(argv[1], argv[2])
    v = VSIF()
    with open(argv[1], "rb") as s:
        v.unpack(s)

    d = BVCD(v["strings"])
    with open(argv[2], "rb") as s:
        d.unpack(s)
    pprint(d.data)
