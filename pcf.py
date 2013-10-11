from binary import Struct, Magic, Format, String, Blob, PrefixedBlob, PrefixedArray, Array, Index, FixedString
import json
from uuid import UUID

class UUIDField(Blob):
    def __init__(self):
        Blob.__init__(self, 16)

    def _unpack(self, s):
        data = Blob._unpack(self, s)
        return UUID(bytes=data).urn

    def _pack(self, s, data):
        Blob._pack(self, s, UUID(data).bytes)

class Attribute(Struct):
    def __init__(self, namefield, stringfield):
        self.namefield = namefield
        self.stringfield = stringfield

    def fields(self):
        self.F("name", self.namefield())
        type = self.F("type", Format("B")).data

        attribute_types = {
            1 : lambda: Format("I"), # element index
            2 : lambda: Format("I"), # integer
            3 : lambda: Format("f"), # float
            4 : lambda: Format("?"), # bool
            5 : self.stringfield, # string
            6 : lambda: PrefixedBlob(Format("I")), # blob
            7 : lambda: Format("I"), # time
            8 : lambda: Format("4B"), # color
            9 : lambda: Format("2f"), # vector2
            10 : lambda: Format("3f"), # vector3
            11 : lambda: Format("4f"), # vector4
            12 : lambda: Format("3f"), # angle
            13 : lambda: Format("4f"), # quaternion
            14 : lambda: Format("16f"), # matrix
        }

        if 1 <= type <= 14:
            self.F("data", attribute_types[type]())
        elif 14 < type <= 28:
            self.F("data", PrefixedArray(Format("I"), attribute_types[type - 14]))
        else:
            assert False, type

class Element(Struct):
    def __init__(self, namefield, stringfield):
        self.namefield = namefield
        self.stringfield = stringfield

    def fields(self):
        self.F("type", self.namefield())
        self.F("name", self.stringfield())
        self.F("guid", UUIDField())

class PCF(Struct):
    def fields(self):
        self.F("magic", Magic("<!-- dmx encoding "))
        self.F("version", FixedString(len("binary 2 format pcf 1")))
        self.F("magic2", Magic(" -->\n\0"))
        version = self.field["version"].data
        assert version in ["binary 2 format pcf 1", "binary 5 format pcf 2"], version

        if version == "binary 2 format pcf 1":
            prefix = Format("h")
        else:
            prefix = Format("I")
        strings = self.F("strings", PrefixedArray(prefix, String))

        if version == "binary 2 format pcf 1":
            namefield = lambda: Index(strings.data, Format("h"))
            stringfield = String
        else:
            namefield = lambda: Index(strings.data, Format("I"))
            stringfield = namefield
        self.F("elements", PrefixedArray(Format("I"), lambda: Element(namefield, stringfield)))
        self.F("attributes", Array(len(self.field["elements"].field), lambda: PrefixedArray(Format("I"), lambda: Attribute(namefield, stringfield))))
