from binary import getbytes, skipbytes, getstring, getunpack

class Element(object):
    def __init__(self, type, name, guid):
        self.type = type
        self.name = name
        self.guid = guid
        self.attributes = []

class Attribute(object):
    def __init__(self, name, type, data):
        self.name = name
        self.type = type
        self.data = data

with open("x.pcf", "rb") as s:
    skipbytes(s, "<!-- dmx encoding binary 5 format pcf 2 -->\n\0")
    #skipbytes(s, "<!-- dmx encoding binary 5 format dmx 1 -->\n\0")
    (nstrings,) = getunpack(s, "<I")
    strings = []
    for i in xrange(nstrings):
        strings.append(getstring(s, '\0'))

    def gettablestring():
        (index,) = getunpack(s, "<I")
        return strings[index]

    (nelements,) = getunpack(s, "<I")
    elements = []
    for i in xrange(nelements):
        e_type = gettablestring()
        e_name = gettablestring()
        e_guid = getunpack(s, "<16B")
        elements.append(Element(e_type, e_name, e_guid))

    def get_Element():
        return getunpack(s, "<I")[0]
    def get_int():
        return getunpack(s, "<I")[0]
    def get_float():
        return getunpack(s, "<f")[0]
    def get_bool():
        return getunpack(s, "<?")[0]
    def get_str():
        return gettablestring()
    def get_Binary():
        size = getunpack(s, "<I")[0]
        return getbytes(size)
    def get_Time():
        return getunpack(s, "<I")[0]
    def get_Color():
        return getunpack(s, "<4B")
    def get_Vector2():
        return getunpack(s, "<2f")
    def get_Vector3():
        return getunpack(s, "<3f")
    def get_Vector4():
        return getunpack(s, "<4f")
    def get_Angle():
        return getunpack(s, "<3f")
    def get_Quaternion():
        return getunpack(s, "<4f")
    def get_Matrix():
        return getunpack(s, "<16f")
    attribute_types = [get_Element, get_int, get_float, get_bool, get_str, get_Binary, get_Time, get_Color, get_Vector2, get_Vector3, get_Vector4, get_Angle, get_Quaternion, get_Matrix]

    for i in xrange(nelements):
        (nattributes,) = getunpack(s, "<I")
        attributes = []
        for j in xrange(nattributes):
            a_name = gettablestring()
            (a_type,) = getunpack(s, "<B")
            a_type -= 1
            if a_type >= len(attribute_types):
                a_type -= len(attribute_types)
                (size,) = getunpack(s, "<I")
                a_data = []
                for k in xrange(size):
                    a_data.append(attribute_types[a_type]())
            else:
                a_data = attribute_types[a_type]()
            elements[i].attributes.append(Attribute(a_name, a_type, a_data))

    for i in xrange(len(elements)):
        e = elements[i]
        print u'Element {} "{}" type {}'.format(i, e.name, e.type, e.guid)
        for a in e.attributes:
            print u'\t"{}"  type {} data {}'.format(a.name, a.type, repr(a.data))

