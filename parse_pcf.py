from binary import Struct, Magic, Format, FormatField, StringField, BlobField, PrefixedBlobField, PrefixedArray, PrefixedArrayField, DependentArray, DependentArrayField, Index
import json
from uuid import UUID

attribute_types = {
    1 : lambda: FormatField("I"), # element index
    2 : lambda: FormatField("I"), # integer
    3 : lambda: FormatField("f"), # float
    4 : lambda: FormatField("?"), # bool
    5 : lambda: FormatField("I"), # string
    6 : lambda: PrefixedBlobField(FormatField("I")), # blob
    7 : lambda: FormatField("I"), # time
    8 : lambda: FormatField("4B"), # color
    9 : lambda: FormatField("2f"), # vector2
    10 : lambda: FormatField("3f"), # vector3
    11 : lambda: FormatField("4f"), # vector4
    12 : lambda: FormatField("3f"), # angle
    13 : lambda: FormatField("4f"), # quaternion
    14 : lambda: FormatField("16f"), # matrix
    }

class UUIDField(BlobField):
    def __init__(self):
        BlobField.__init__(self, 16)

    @property
    def data(self):
        return UUID(bytes=self._data).urn

    @data.setter
    def data(self, v):
        self._data = UUID(v).bytes

class Attribute(Struct):
    def __init__(self, strings):
        self.strings = strings
        Struct.__init__(self)

    def fields(self):
        Index(self, "name", self.strings, "I")
        Format(self, "type", "B")
        type = self.data["type"]
        if 1 <= type <= 14:
            self.add_field("data", attribute_types[type]())
        elif 14 < type <= 28:
            PrefixedArray(self, "data", FormatField("I"), attribute_types[type - 14])
        else:
            assert False, type

class Element(Struct):
    def __init__(self, strings):
        self.strings = strings
        Struct.__init__(self)

    def fields(self):
        Index(self, "type", self.strings, "I")
        Index(self, "name", self.strings, "I")
        self.add_field("guid", UUIDField())

class PCF(Struct):
    def fields(self):
        Magic(self, "magic", "<!-- dmx encoding binary 5 format pcf 2 -->\n\0")
        strings = PrefixedArray(self, "strings", FormatField("I"), StringField)
        Format(self, "nelements", "I")
        DependentArray(self, "elements", self.field["nelements"], lambda: Element(strings.data))
        DependentArray(self, "attributes", self.field["nelements"], lambda: PrefixedArrayField(FormatField("I"), lambda: Attribute(strings.data)))

with open("x.pcf", "rb") as s:
    p = PCF()
    p.unpack(s)
    assert s.read(1) == ""
    print(json.dumps(p.data, indent=4))
with open("y.pcf", "wb") as s:
    p.pack(s)
