# Copyright (c) 2013 Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from binary import Struct, Magic, Format, String, Blob, PrefixedBlob, PrefixedArray, Array, Index, FixedString, BaseField
import json
from uuid import UUID
from random import randint

class UUIDField(Blob):
    def __init__(self):
        Blob.__init__(self, 16)

    def unpack_data(self, s):
        data = Blob.unpack_data(self, s)
        return UUID(bytes=data).urn

    def pack_data(self, s, data):
        Blob.pack_data(self, s, UUID(data).bytes)

class ElementIndex(BaseField):
    def __init__(self, elements, attributes, index_field):
        self.elements = elements
        self.attributes = attributes
        self.index_field = index_field

    def unpack_data(self, s):
        self.index_field.unpack(s)
        return self.elements[self.index_field.data]

    def pack_data(self, s, data):
        try:
            index = self.elements.index(data)
        except KeyError:
            data.new_guid()
            index = len(self.elements)
            self.elements.append_data(data.data)
            self.attributes.append_data(data.attribute.data)
            self.elements[index].attribute = self.attributes[index]
        self.index_field.data = index
        self.index_field.pack(s)

    def serialize(self):
        return {
            "element": self.data.serialize(),
            "attrib": self.data.attribute.serialize(),
        }

class Attribute(Struct):
    def fields(self, namefield, stringfield, elementindexfield):
        self.F("name", namefield())
        type = self.F("type", Format("B")).data

        attribute_types = {
            1 : elementindexfield, # element index
            2 : lambda: Format("I"), # integer
            3 : lambda: Format("f"), # float
            4 : lambda: Format("?"), # bool
            5 : stringfield, # string
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
    def fields(self, namefield, stringfield):
        self.F("type", namefield())
        self.F("name", stringfield())
        self.F("guid", UUIDField())

    def __key(self):
        return self["guid"].data

    def __eq__(self, other):
        return isinstance(other, Element) and self.__key() == other.__key()

    def __hash__(self):
        return hash(self.__key())

    def new_guid(self):
        random_bytes = bytes([randint(0, 255) for i in range(16)])
        uuid = UUID(bytes=random_bytes, version=4)
        self["guid"].data = uuid.urn

class PCF(Struct):
    def fields(self, include_attributes=True):
        self.F("magic", Magic("<!-- dmx encoding "))
        self.F("version", FixedString(len("binary 2 format pcf 1")))
        self.F("magic2", Magic(" -->\n\0"))
        version = self["version"].data
        assert version in ["binary 2 format pcf 1", "binary 5 format pcf 2"], version

        if version == "binary 2 format pcf 1":
            prefix = Format("h")
        else:
            prefix = Format("I")
        strings = self.F("strings", PrefixedArray(prefix, String))

        if version == "binary 2 format pcf 1":
            namefield = lambda: Index(strings, Format("h"))
            stringfield = String
        else:
            namefield = lambda: Index(strings, Format("I"))
            stringfield = namefield
        self.F("elements", PrefixedArray(Format("I"), lambda: Element(namefield, stringfield)))
        if include_attributes:
            self.F("attributes",
                Array(len(self["elements"]),
                    field_function=lambda i, f: PrefixedArray(
                        Format("I"),
                        lambda: Attribute(
                            namefield,
                            stringfield,
                            lambda: ElementIndex(self["elements"], f, Format("I"))))))
            for i in range(len(self["elements"])):
                self["elements"][i].attribute = self["attributes"][i]

    def minimize(self):
        self["strings"].data = []
        self["elements"].data = [self["elements"].data[0]]
        self["attributes"].data = [self["attributes"].data[0]]
        self["elements"][0].attribute = self["attributes"][0]

if __name__ == "__main__":
    import json
    p = PCF()
    with open("x.pcf", "rb") as s:
        p.unpack(s)
    p.minimize()
    print(json.dumps(p.serialize(), indent=4))
