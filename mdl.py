from binary import Struct, Magic, Format, Offset, Seek, Array, FixedString, String, Pointer

class MDL(Struct):
    def fields(self):
        self.F("magic", Magic("IDST"))
        self.F("version", Format("I"))
        self.F("checksum", Format("I"))
        self.F("name", FixedString(64))
        self.F("datalength", Format("I"))

        self.F("eyepos", Format("3f"))
        self.F("illum", Format("3f"))
        self.F("hull_min", Format("3f"))
        self.F("hull_max", Format("3f"))
        self.F("view_bbmin", Format("3f"))
        self.F("view_bbmax", Format("3f"))

        self.F("flags", Format("I"))

        self.F("bone", Format("II"))
        self.F("bonecontroller", Format("II"))
        self.F("hitbox", Format("II"))

        self.F("numlocalanim", Format("I"))
        self.F("localanimoffset", Format("I"))

        self.F("numlocalsequence", Format("I"))
        self.F("localsequenceoffset", Format("I"))

        self.F("texture", Format("II"))
        self.F("cdtexture", Format("II"))

        self.F("unknown", Format("II"))

        self.F("numskinref", Format("I"))
        self.F("numskinfamilies", Format("I"))
        self.F("skinindex", Format("I"))

        self.F("bodypart", Format("II"))
        self.F("localattachment", Format("II"))

        self.F("numlocalnodes", Format("I"))
        self.F("localnodeindex", Format("I"))
        self.F("localnodenameindex", Format("I"))

        # pointed fields
        # self.F("localanim", Pointer(self["localanimoffset"].data, Array(self["numlocalanim"].data, LocalAnim)))
        self.F("localsequence", Pointer(self["localsequenceoffset"].data, Array(self["numlocalsequence"].data, LocalSequence)))
        self.F("skin",
            Pointer(self["skinindex"].data,
                Array(self["numskinfamilies"].data,
                    lambda: Array(self["numskinref"].data,
                        lambda: Format("h")))))

        # rest broken due to unkown fields added
        return

        self.F("flexdesc", Format("II"))
        self.F("flexcontroller", Format("II"))
        self.F("flexrule", Format("II"))
        self.F("ikchain", Format("II"))
        self.F("mouth", Format("II"))

        self.F("keyvalueindex", Format("I"))
        self.F("keyvaluesize", Format("I"))

        self.F("localikautoplaylock", Format("II"))

        self.F("mass", Format("f"))
        self.F("contents", Format("I"))

        self.F("includemodels", Format("II"))

        self.F("bonetablebynameindex", Format("I"))
        self.F("vertexbase", Format("I"))
        self.F("indexbase", Format("I"))
        self.F("constdirectionallightdot", Format("B"))
        self.F("rootLOD", Format("B"))
        self.F("numAllowedRootLODs", Format("B"))
        self.F("unused", Format("B"))
        self.F("unused4", Format("I"))

        self.F("flexcontrollerui", Format("II"))

        self.F("unused3", Format("2I"))
        self.F("studiohdr2index", Format("I"))
        self.F("unused2", Format("1I"))

class BasePointer(Format):
    def __init__(self, fmt):
        Format.__init__(self, fmt)

    def unpack_data(self, s):
        this = s.tell()
        data = Format.unpack_data(self, s)
        assert data == -this
        return data

    def pack(self, s):
        this = s.tell()
        self.data = s
        Format.pack(self, s)

class Relative(Format):
    def __init__(self, field, fmt):
        self.field = field
        Format.__init__(self, fmt)

    def unpack_data(self, s):
        data = Format.unpack_data(self, s)
        if data != 0:
            data += self.field.data
        return data

    def pack_data(self, s, data):
        if data != 0:
            data += self.field.data
        Format.pack_data(self, s, data)

class RelativeString(Relative):
    def unpack_data(self, s):
        data = Relative.unpack_data(self, s)
        with Seek(s, data):
            string = String().unpack_data(s)
        return [data, string]

    def pack_data(self, s, data):
        data = data[0]
        Relative.pack_data(self, s, data)

class LocalAnim(Struct):
    def fields(self):
        base = self.F("base", Offset())
        self.F("baseptr", BasePointer("i"))
        self.F("nameindex", RelativeString(base, "i"))
        self.F("fps", Format("f"))
        self.F("flags", Format("I"))
        self.F("numframes", Format("I"))
        self.F("nummovements", Format("I"))
        self.F("movementindex", Relative(base, "i"))
        self.F("unused", Format("6I"))
        self.F("animblock", Format("i"))
        self.F("animindex", Relative(base, "i"))
        self.F("numikrules", Format("I"))
        self.F("ikruleindex",Relative(base, "i"))
        self.F("animblockikruleindex", Relative(base, "i"))
        self.F("numlocalhierarchy", Format("I"))
        self.F("localhierarchyindex", Relative(base, "i"))
        self.F("sectionindex", Relative(base, "i"))
        self.F("sectionframes", Format("I"))
        self.F("zeroframespan", Format("h"))
        self.F("zeroframecount", Format("h"))
        self.F("zeroframeindex", Relative(base, "i"))
        self.F("zeroframestalltime", Format("f"))

class LocalSequence(Struct):
    def fields(self):
        base = self.F("base", Offset())
        self.F("baseptr", BasePointer("i"))
        self.F("labelindex", RelativeString(base, "i"))
        self.F("activitynameindex", RelativeString(base, "i"))
        self.F("flags", Format("I"))
        self.F("activity", Format("i"))
        self.F("actweight", Format("I"))
        self.F("numevents", Format("I"))
        self.F("eventindex", Relative(base, "i"))
        self.F("bbmin", Format("3f"))
        self.F("bbmax", Format("3f"))
        self.F("numblends", Format("I"))
        self.F("animindex", Relative(base, "i"))
        self.F("movementindex", Relative(base, "i"))
        self.F("groupsize", Format("2I"))
        self.F("paramindex", Format("2i"))
        self.F("paramstart", Format("2f"))
        self.F("paramend", Format("2f"))
        self.F("paremparent", Format("I"))
        self.F("fadeintime", Format("f"))
        self.F("fadeouttime", Format("f"))
        self.F("localentrynode", Format("I"))
        self.F("localexitnode", Format("I"))
        self.F("nodeflags", Format("I"))
        self.F("entryphase", Format("f"))
        self.F("exitphase", Format("f"))
        self.F("lastframe", Format("f"))
        self.F("nextseg", Format("I"))
        self.F("pose", Format("I"))
        self.F("numikrules", Format("I"))
        self.F("numautolayers", Format("I"))
        self.F("autolayerindex", Relative(base, "i"))
        self.F("weightlistindex", Relative(base, "i"))
        self.F("posekeyindex", Relative(base, "i"))
        self.F("numiklocks", Format("I"))
        self.F("iklockindex", Format("I"))
        self.F("keyvalueindex", Relative(base, "i"))
        self.F("keyvaluesize", Format("I"))
        self.F("cycleposeindex", Relative(base, "i"))
        self.F("activitymodifierindex", Relative(base, "i"))
        self.F("numactivitymodifier", Format("I"))
        self.F("unused", Format("5I"))

        # self.F("event", Pointer(self["eventindex"].data, Array(self["numevents"].data, Event)))
        self.F("activitymodifier", Pointer(self["activitymodifierindex"].data, Array(self["numactivitymodifier"].data, ActivityModifier)))

class ActivityModifier(Struct):
    def fields(self):
        base = self.F("base", Offset())
        self.F("szindex", RelativeString(base, "i"))

class Event(Struct):
    def fields(self):
        base = self.F("base", Offset())
        self.F("cycle", Format("f"))
        self.F("event", Format("I"))
        self.F("type", Format("I"))
        self.F("options", FixedString(64))
        self.F("szeventindex", RelativeString(base, "i"))
