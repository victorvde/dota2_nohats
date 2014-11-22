from io import BytesIO
from zlib import decompress

from binary import Struct, Magic, Format, ContainerField, BaseField, BaseArray, Blob

class ZlibField(ContainerField):
    def __init__(self, unpacked_size, field):
        self.unpacked_size = unpacked_size
        self.field = field

    def unpack(self, s):
        b = s.read()
        u = decompress(b)
        assert len(u) >= self.unpacked_size, "Incorrect decompressed size: {} instead of {}".format(len(u), self.unpacked_size)
        u = u[:self.unpacked_size]
        with BytesIO(u) as s:
            self.field.unpack(s)

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
                assert len(b) == 1, "Unexpected number of bytes {}".format(len(b))
                self.buffered_byte = b[0]
                self.bits_left = 8
            bits_taken =  min(self.bits_left, n)
            new_bits = (self.buffered_byte >> (self.bits_left - bits_taken)) & ((1 << bits_taken) - 1)
            bits = (bits << bits_taken) | new_bits
            self.bits_left -= bits_taken
            n -= bits_taken
        return bits

class BitStruct(Struct):
    def unpack(self, s):
        Struct.unpack(self, BitReadStream(s))

class Bits(BaseField):
    def __init__(self, n):
        self.n = n

    def unpack_data(self, s):
        return s.read_bits(self.n)

class SBits(BaseField):
    def __init__(self, n):
        self.n = n

    def unpack_data(self, s):
        sign = s.read_bits(1)
        bits = s.read_bits(self.n - 1)
        if sign == 1:
            bits = bits - (1 << (self.n - 1))
        return bits

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
        return {
            "tagcode": tagcode,
            "length": length,
        }

class Tag(Struct):
    def fields(self):
        h = self.F("header", RecordHeader())
        self.F("blob", Blob(h.data["length"]))

    def serialize(self):
        return {"header": self["header"].serialize()}

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
        l = self.F("length", Format("I"))
        self.F("tags", ZlibField(l.data, SWFContent()))

if __name__ == "__main__":
    import json
    swf = ScaleFormSWF()
    with open("x.gfx", "rb") as s:
        swf.unpack(s)
    print(json.dumps(swf.serialize(), indent=4))
