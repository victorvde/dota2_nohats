from binary import Struct, Format, BaseField, Array, Blob, getbyte, getbytes

def unpack_variable(s):
    data = 0
    shift = 0
    while True:
        b = getbyte(s)[0]
        data |= (b & 0x7F) << shift
        shift += 7
        if not (b & 0x80):
            break
    return (data, shift)

def pack_variable(s, data, stop):
    bs = bytearray()
    while True:
        b = data & 0x7F
        data = data >> 7
        if not stop(data, b):
            b |= 0x80
            bs.append(b)
        else:
            bs.append(b)
            break
    s.write(bs)

class U32(BaseField):
    def unpack_data(self, s):
        (data, shift) = unpack_variable(s)
        return data

    def pack_data(self, s, data):
        def stop(d, b):
            return d == 0
        pack_variable(s, data, stop)

class U30(U32):
    def unpack_data(self, s):
        data = U32.unpack_data(self, s)
        return data

    def pack_data(self, s, data):
        assert data < (1 << 30), data
        U32.pack_data(self, s, data)

class S32(U32):
    def unpack_data(self, s):
        (data, shift) = unpack_variable(s)
        sign = data >> (shift - 1)
        if sign:
            data -= (1 << shift)
        return data

    def pack_data(self, s, data):
        def stop(d, b):
            if b & 0x40:
                return d == -1
            else:
                return d == 0
        pack_variable(s, data, stop)

class PrefixedString(BaseField):
    def __init__(self):
        self.prefix = U30()

    def unpack_data(self, s):
        self.prefix.unpack(s)
        data = getbytes(s, self.prefix.data)
        data = data.decode()
        return data

    def pack_data(self, s, data):
        data = data.encode()
        self.prefix.pack_data(s, len(data))
        s.write(data)

class ConstIndex(BaseField):
    def __init__(self, array):
        self.array = array
        self.index_field = U30()

    def unpack_data(self, s):
        self.index_field.unpack(s)
        if self.index_field.data == 0:
            return None
        else:
            return self.array[self.index_field.data - 1].data

    def pack_data(self, s, data):
        return self.index_field.pack(s)

class Namespace(Struct):
    def fields(self, s):
        self.F("kind", Format("B"))
        self.F("name", ConstIndex(s))

class NamespaceSet(Struct):
    def fields(self, ns):
        c = self.F("count", U30())
        self.F("ns", Array(c.data, lambda: ConstIndex(ns)))

class Multiname(Struct):
    def fields(self, s, ns, nss):
        k = self.F("kind", Format("B"))
        if k.data in [0x07, 0x0D]:
            self.F("ns", ConstIndex(ns))
            self.F("name", ConstIndex(s))
        elif k.data in [0x0F, 0x10]:
            self.F("name", ConstIndex(s))
        elif k.data in [0x11, 0x12]:
            pass
        elif k.data in [0x09, 0x0E]:
            self.F("name", ConstIndex(s))
            self.F("nsset", ConstIndex(nss))
        elif k.data in [0x1B, 0x1C]:
            self.F("nsset", ConstIndex(nss))
        elif k.data in [0x1D]:
            self.F("typedef", U30())
            c = self.F("numparams", U30())
            self.F("params", Array(c.data, U30))
        else:
            assert False, k.data

class ConstantPool(Struct):
    def fields(self):
        c = self.F("int_count", U30())
        self.F("integer", Array(c.data-1, S32))
        c = self.F("uint_count", U30())
        self.F("uinteger", Array(c.data-1, U32))
        c = self.F("double_count", U30())
        self.F("double", Array(c.data-1, lambda: Format("d")))
        c = self.F("string_count", U30())
        s = self.F("string", Array(c.data-1, PrefixedString))
        c = self.F("namespace_count", U30())
        ns = self.F("namespace", Array(c.data-1, lambda: Namespace(s)))
        c = self.F("namespaceset_count", U30())
        nss = self.F("namespaceset", Array(c.data-1, lambda: NamespaceSet(ns)))
        c = self.F("multiname_count", U30())
        self.F("multiname", Array(c.data-1, lambda: Multiname(s, ns, nss)))

class OptionDetail(Struct):
    def fields(self):
        self.F("val", U30())
        self.F("kind", Format("B"))

class Method(Struct):
    def fields(self, const):
        param_c = self.F("param_count", U30())
        self.F("return_type", ConstIndex(const["multiname"]))
        self.F("param_types", Array(param_c.data, lambda: ConstIndex(const["multiname"])))
        self.F("name", ConstIndex(const["string"]))
        f = self.F("flags", Format("B"))
        if f.data & 0x08:
            c = self.F("option_count", U30())
            self.F("option", Array(c.data, OptionDetail))
        if f.data & 0x80:
            self.F("param_names", Array(param_c.data, lambda: ConstIndex(const["string"])))

class Item(Struct):
    def fields(self, const):
        self.F("key", ConstIndex(const["string"]))
        self.F("value", ConstIndex(const["string"]))

class MetaData(Struct):
    def fields(self, const):
        self.F("name", ConstIndex(const["string"]))
        c = self.f("item_count", U30())
        self.F("items", Array(c.data, lambda: Item(const)))

class Trait(Struct):
    def fields(self, const):
        self.F("name", ConstIndex(const["multiname"]))
        k = self.F("kind", Format("B"))
        kind = k.data & 0x0F
        f = k.data >> 4
        if kind in [0, 6]:
            self.F("slot_id", U30())
            self.F("type_name", ConstIndex(const["multiname"]))
            v = self.F("vindex", U30())
            if v.data != 0:
                self.F("vkind", Format("B"))
        elif kind in [4]:
            self.F("slot_id", U30())
            self.F("classi", U30())
        elif kind in [5]:
            self.F("slot_id", U30())
            self.F("function", U30())
        elif kind in [1, 2, 3]:
            self.F("disp_id", U30())
            self.F("method", U30())
        else:
            assert False, kind
        if f & 0x04:
            c = self.F("metadata_count", U30())
            self.F("metadata", Array(c.data, U30))

class Instance(Struct):
    def fields(self, const):
        self.F("name", ConstIndex(const["multiname"]))
        self.F("super_name", ConstIndex(const["multiname"]))
        f = self.F("flags", Format("B"))
        if f.data & 0x08:
            self.F("protected_ns", ConstIndex(const["namespace"]))
        c = self.F("intrf_count", U30())
        self.F("interface", Array(c.data, lambda: ConstIndex(const["multiname"])))
        self.F("iinit", U30())
        c = self.F("trait_count", U30())
        self.F("trait", Array(c.data, lambda: Trait(const)))

class Class(Struct):
    def fields(self, const):
        self.F("cinit", U30())
        c = self.F("trait_count", U30())
        self.F("trait", Array(c.data, lambda: Trait(const)))

class Script(Struct):
    def fields(self, const):
        self.F("init", U30())
        c = self.F("trait_count", U30())
        self.F("trait", Array(c.data, lambda: Trait(const)))

class Exception(Struct):
    def fields(self, const):
        self.F("from", U30())
        self.F("to", U30())
        self.F("target", U30())
        self.F("exc_type", ConstIndex(const["string"]))
        self.F("var_name", ConstIndex(const["string"]))

class MethodBody(Struct):
    def fields(self, const):
        self.F("method", U30())
        self.F("max_stack", U30())
        self.F("local_count", U30())
        self.F("init_scope_depth", U30())
        self.F("max_scope_depth", U30())
        c = self.F("code_length", U30())
        self.F("code", Blob(c.data))
        c = self.F("exception_count", U30())
        self.F("exception", Array(c.data, lambda: Exception(const)))
        c = self.F("trait_count", U30())
        self.F("trait", Array(c.data, lambda: Trait(const)))

class ABCFile(Struct):
    def fields(self):
        self.F("minor", Format("H"))
        self.F("major", Format("H"))
        const = self.F("constant_pool", ConstantPool())
        c = self.F("method_count", U30())
        self.F("method", Array(c.data, lambda: Method(const)))
        c = self.F("metadatacount", U30())
        self.F("metadata", Array(c.data, lambda: MetaData(const)))
        c = self.F("class_count", U30())
        self.F("instance", Array(c.data, lambda: Instance(const)))
        self.F("class", Array(c.data, lambda: Class(const)))
        c = self.F("script_count", U30())
        self.F("script", Array(c.data, lambda: Script(const)))
        c = self.F("methodbody_count", U30())
        self.F("methodbody", Array(c.data, lambda: MethodBody(const)))
