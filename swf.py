from io import BytesIO
from zlib import compress, decompress

from binary import Struct, Magic, Format, ContainerField, BaseField, BaseArray, Blob, String, FakeWriteStream
from collections import OrderedDict
from swf_abc import ABCFile

class ZlibField(ContainerField):
    def __init__(self, unpacked_size_field, field):
        self.unpacked_size_field = unpacked_size_field
        self.field = field

    def unpack(self, s):
        self.unpacked_size_field.unpack(s)
        unpacked_size =  self.unpacked_size_field.data
        b = s.read()
        u = decompress(b)
        assert len(u) + 8 >= unpacked_size, "Incorrect decompressed size: {} instead of {}".format(len(u), unpacked_size)
        u = u[:unpacked_size]
        with BytesIO(u) as s:
            self.field.unpack(s)

    def pack(self, s):
        with BytesIO() as us:
            self.field.pack(us)
            u = us.getvalue()
        self.unpacked_size_field.pack_data(s, len(u) + 8)
        b = compress(u, 9)
        s.write(b)

    @property
    def data(self):
        return self.field.data

    @data.setter
    def data(self, v):
        self.field.data = v

class BitField(Struct):
    def unpack(self, s):
        self.bits_left = 0
        self.buffer_byte = None
        Struct.unpack(self, s)

class BitReadStream(object):
    def __init__(self, s):
        self.s = s
        self.bits_left = 0
        self.buffered_byte = None

    def read_bits(self, n):
        bits = 0
        while n > 0:
            if self.bits_left == 0:
                b = self.s.read(1)
                assert len(b) == 1, "Unexpected number of bytes read ({})".format(len(b))
                self.buffered_byte = b[0]
                self.bits_left = 8
            bits_taken =  min(self.bits_left, n)
            self.bits_left -= bits_taken
            n -= bits_taken
            new_bits = (self.buffered_byte >> self.bits_left) & ((1 << bits_taken) - 1)
            bits = (bits << bits_taken) | new_bits
        return bits

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

class BitWriteStream(object):
    def __init__(self, s):
        self.s = s
        self.bits_left = 8
        self.buffered_byte = 0

    def write_bits(self, n, bits):
        assert bits < (1 << n), bits
        while n > 0:
            if self.bits_left == 0:
                wn = self.s.write(bytes([self.buffered_byte]))
                assert wn == 1, "Unexpected number of bytes written ({})".format(wn)
                self.buffered_byte = 0
                self.bits_left = 8
            bits_taken =  min(self.bits_left, n)
            self.bits_left -= bits_taken
            n -= bits_taken
            new_bits = (bits >> n)
            self.buffered_byte |= (new_bits << self.bits_left)
            bits &= (1 << n) - 1
        return bits

    def flush(self):
        if self.bits_left < 8:
            wn = self.s.write(bytes([self.buffered_byte]))
            assert wn == 1, "Unexpected number of bytes written ({})".format(wn)

    def close(self):
        self.flush()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

class BitStruct(Struct):
    def unpack(self, s):
        with BitReadStream(s) as bs:
            Struct.unpack(self, bs)

    def pack(self, s):
        with BitWriteStream(s) as bs:
            Struct.pack(self, bs)

class Bits(BaseField):
    def __init__(self, n):
        self.n = n

    def unpack_data(self, s):
        return s.read_bits(self.n)

    def pack_data(self, s, data):
        return s.write_bits(self.n, data)

class SBits(BaseField):
    def __init__(self, n):
        self.n = n

    def unpack_data(self, s):
        if self.n == 0:
            return 0
        sign = s.read_bits(1)
        bits = s.read_bits(self.n - 1)
        if sign == 1:
            bits = bits - (1 << (self.n - 1))
        return bits

    def pack_data(self, s, bits):
        if self.n == 0:
            assert bits == 0, bits
            return
        sign = 1 if bits < 0 else 0
        if sign == 1:
            bits = bits + (1 << (self.n - 1))
        s.write_bits(1, sign)
        s.write_bits(self.n - 1, bits)


class Rect(BitStruct):
    def fields(self):
        nbits = self.F("nbits", Bits(5))
        self.F("xmin", SBits(nbits.data))
        self.F("xmax", SBits(nbits.data))
        self.F("ymin", SBits(nbits.data))
        self.F("ymax", SBits(nbits.data))

class RecordHeader(BaseField):
    def unpack_data(self, s):
        data = Format("H").unpack_data(s)
        tagcode = (data >> 6)
        length = (data & ((1 << 6) -1))
        if length == 63:
            length = Format("I").unpack_data(s)
        return OrderedDict([
            ("tagcode", tagcode),
            ("length", length),
            ])

    def pack_data(self, s, data):
        tagcode = data["tagcode"]
        length = data["length"]
        if length > 62:
            taglength = 63
        else:
            taglength = length
        Format("H").pack_data(s, (tagcode << 6)  | taglength)
        if length > 62:
            Format("I").pack_data(s, length)

class PlaceObject2Flags(BitStruct):
    def fields(self):
        self.F("clip_actions", Bits(1))
        self.F("clip_depth", Bits(1))
        self.F("name", Bits(1))
        self.F("ratio", Bits(1))
        self.F("color_transform", Bits(1))
        self.F("matrix", Bits(1))
        self.F("character", Bits(1))
        self.F("move", Bits(1))

class Matrix(BitStruct):
    def fields(self):
        self.F("has_scale", Bits(1))
        if self["has_scale"].data == 1:
            self.F("nscalebits", Bits(5))
            self.F("scalex", SBits(self["nscalebits"].data))
            self.F("scaley", SBits(self["nscalebits"].data))
        self.F("has_rotate", Bits(1))
        if self["has_rotate"].data == 1:
            self.F("nrotatebits", Bits(5))
            self.F("rotateskew0", SBits(self["nrotatebits"].data))
            self.F("rotateskew1", SBits(self["nrotatebits"].data))
        self.F("ntranslatebits", Bits(5))
        self.F("translatex", SBits(self["ntranslatebits"].data))
        self.F("translatey", SBits(self["ntranslatebits"].data))

class CXFormWithAlpha(BitStruct):
    def fields(self):
        self.F("has_addterms", Bits(1))
        self.F("has_multterms", Bits(1))
        self.F("numbits", Bits(4))
        if self["has_multterms"].data == 1:
            self.F("redmultterm", SBits(self["numbits"].data))
            self.F("greenmultterm", SBits(self["numbits"].data))
            self.F("bluemultterm", SBits(self["numbits"].data))
            self.F("alphamultterm", SBits(self["numbits"].data))
        if self["has_addterms"].data == 1:
            self.F("redaddterm", SBits(self["numbits"].data))
            self.F("greenaddterm", SBits(self["numbits"].data))
            self.F("blueaddterm", SBits(self["numbits"].data))
            self.F("alphaaddterm", SBits(self["numbits"].data))

class DefineSprite(Struct):
    def fields(self):
        self.F("sprite_id", Format("H"))
        self.F("frame_count", Format("H"))
        self.F("tags", TagArray())

class PlaceObject2(Struct):
    def fields(self):
        f = self.F("flags", PlaceObject2Flags())
        self.F("depth", Format("H"))
        if f["character"].data == 1:
            self.F("character", Format("H"))
        if f["matrix"].data == 1:
            self.F("matrix", Matrix())
        if f["color_transform"].data == 1:
            self.F("color_transform", CXFormWithAlpha())
        if f["ratio"].data == 1:
            self.F("ratio", Format("H"))
        if f["name"].data == 1:
            self.F("name", String())
        if f["clip_depth"].data == 1:
            self.F("clip_depth", Format("H"))
        assert f["clip_actions"].data == 0

class DoABC(Struct):
    def fields(self):
        self.F("flags", Format("I"))
        self.F("name", String())
        self.F("abcdata", ABCFile())

class Tag(Struct):
    def fields(self):
        h = self.F("header", RecordHeader())
        if h.data["tagcode"] == 39:
            self.F("content", DefineSprite())
        elif h.data["tagcode"] == 26:
            self.F("content", PlaceObject2())
        elif h.data["tagcode"] == 82:
            self.F("content", DoABC())
        else:
            self.F("content", Blob(h.data["length"]))

    def pack(self, s):
        fs = FakeWriteStream()
        self["content"].pack(fs)
        self["header"].data["length"] = fs.tell()
        Struct.pack(self, s)

class TagArray(BaseArray):
    def __init__(self):
        BaseArray.__init__(self, Tag)

    def unpack(self, s):
        i = 0
        self.field = []
        while True:
            f = self.field_fun(i, self)
            self.field.append(f)
            f.unpack(s)
            if f["header"].data["tagcode"] == 0:
                break
            i += 1

class SWFContent(Struct):
    def fields(self):
        self.F("frame_size", Rect())
        self.F("frame_rate", Format("H"))
        self.F("frame_count", Format("H"))
        self.F("tags", TagArray())

class ScaleFormSWF(Struct):
    def fields(self):
        self.F("magic", Magic(b"CFX\x0a"))
        self.F("content", ZlibField(Format("I"), SWFContent()))

if __name__ == "__main__":
    import json

    swf = ScaleFormSWF()
    with open("x.gfx", "rb") as s:
        swf.unpack(s)

    for tag in swf["content"]["tags"]:
        if tag["header"].data["tagcode"] == 82:
            pass

    with open("y.gfx", "wb") as s:
        swf.pack(s)

    print(json.dumps(swf.serialize(), indent=4))
