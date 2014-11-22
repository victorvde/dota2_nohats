# Copyright (c) 2013 Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from struct import pack, unpack, calcsize
from collections import OrderedDict

def getbytes(s, n):
    b = s.read(n)
    assert len(b) == n, "Unexpected EOF"
    return b

def getbyte(s):
    return getbytes(s, 1)

class Seek(object):
    def __init__(self, s, *args, **kwargs):
        self.old_pos = None
        self.s = s
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        self.old_pos = self.s.tell()
        self.s.seek(*self.args, **self.kwargs)

    def __exit__(self, exc_type, exc_value, traceback):
        self.s.seek(self.old_pos)

class FakeWriteStream(object):
    def __init__(self, offset, name):
        self.offset = offset
        self.name = name

    def seek(self, offset):
        self.offset = offset

    def tell(self):
        return self.offset

    def write(self, data):
        self.offset += len(data)

class BaseField(object):
    def unpack(self, s):
        self.data = self.unpack_data(s)

    def unpack_data(self, s):
        raise notImplementedError

    def pack(self, s):
        self.pack_data(s, self.data)

    def pack_data(self, s, data):
        raise NotImplementedError(self)

    def full_pack(self, s):
        new_data = self.data
        while True:
            old_data = new_data
            self.pack(FakeWriteStream(s.tell(), s.name))
            new_data = self.data
            if old_data == new_data:
                break
        self.pack(s)

    def serialize(self):
        return self.data

class ContainerField(BaseField):
    def __getitem__(self, key):
        return self.field[key]

    def __setitem__(self, key, value):
        self.field[key] = value

    def __delitem__(self, key):
        del self.field[key]

    def __len__(self):
        return len(self.field)

    def __iter__(self):
        return iter(self.field)

    def __contains__(self, key):
        return key in self.field

    def serialize(self):
        return self.field.serialize()

class Struct(ContainerField):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def add_field(self, name, f):
        assert name not in self, name
        self[name] = f
        input_type, v = self.input
        if input_type == "data":
            f.data = v.get(name, None)
        elif input_type == "stream":
            f.unpack(v)
        else:
            assert False, input_type
        return f

    def F(self, name, f):
        return self.add_field(name, f)

    def unpack(self, s):
        self.field = OrderedDict()
        self.input = ("stream", s)
        self.fields(*self.args, **self.kwargs)
        del self.input

    def pack(self, s):
        for name, f in self.field.items():
            f.pack(s)

    @property
    def data(self):
        data = OrderedDict()
        for k, v in self.field.items():
            data[k] = v.data
        return data

    @data.setter
    def data(self, v):
        self.field = OrderedDict()
        self.input = ("data", v)
        self.fields(*self.args, **self.kwargs)
        del self.input

    def serialize(self):
        data = OrderedDict()
        for k, v in self.field.items():
            data[k] = v.serialize()
        return data

    def fields(self):
        raise NotImplementedError(self)

class Magic(BaseField):
    def __init__(self, magic):
        if isinstance(magic, str):
            magic = magic.encode()
        self.magic = magic

    def unpack(self, s):
        data = getbytes(s, len(self.magic))
        assert data == self.magic

    def pack(self, s):
        s.write(self.magic)

    @property
    def data(self):
        return self.magic.decode()

    @data.setter
    def data(self, v):
        assert v == self.magic or v is None, v

class Format(BaseField):
    def __init__(self, fmt):
        if fmt[0] in "@=<>!":
            bosa = fmt[0]
            fmt = fmt[1:]
        else:
            bosa = "<"
        self.bosa = bosa
        self.fmt = fmt
        self.single = len(fmt) == 1

    def unpack_data(self, s):
        fmt = self.bosa + self.fmt
        size = calcsize(fmt)
        b = getbytes(s, size)
        data = unpack(fmt, b)
        if self.single:
            assert len(data) == 1
            data = data[0]
        return data

    def pack_data(self, s, data):
        if self.single:
            data = (data,)
        s.write(pack(self.fmt, *data))

class BaseArray(ContainerField):
    def __init__(self, field_maker=None, field_function=None):
        if field_function is None:
            field_function = lambda i, f: field_maker()
        self.field_fun = field_function
        self._dict = None

    def unpack(self, s):
        self.field = [self.field_fun(i, self) for i in range(self.size)]
        for f in self:
            f.unpack(s)

    def pack(self, s):
        for f in self:
            f.pack(s)

    @property
    def data(self):
        return [f.data for f in self]

    def index(self, field):
        if self._dict is None:
            self._dict = {}
            for i in range(len(self.field)):
                self._dict[self.field[i]] = i
        return self._dict[field]

    @data.setter
    def data(self, v):
        self.field = [self.field_fun(i, self) for i in range(len(v))]
        for f, fv in zip(self.field, v):
            f.data = fv
        self._dict = None

    def serialize(self):
        return [f.serialize() for f in self]

    def append_data(self, v):
        idx = len(self.field)
        f = self.field_fun(idx, self)
        self.field.append(f)
        f.data = v
        if self._dict is not None:
            self._dict[f] = idx

class Array(BaseArray):
    def __init__(self, size, *args, **kwargs):
        self.size = size
        BaseArray.__init__(self, *args, **kwargs)

class PrefixedArray(BaseArray):
    def __init__(self, prefix_field, *args, **kwargs):
        self.prefix_field = prefix_field
        BaseArray.__init__(self, *args, **kwargs)

    @property
    def size(self):
        return self.prefix_field.data

    def unpack(self, s):
        self.prefix_field.unpack(s)
        BaseArray.unpack(self, s)

    def pack(self, s):
        self.prefix_field.data = len(self)
        self.prefix_field.pack(s)
        BaseArray.pack(self, s)

class BaseBlob(BaseField):
    def unpack_data(self, s):
        return getbytes(s, self.size)

    def pack_data(self, s, data):
        s.write(data)

class Blob(BaseBlob):
    def __init__(self, size):
        self.size = size

class PrefixedBlob(BaseBlob):
    def __init__(self, prefix_field, *args, **kwargs):
        self.prefix_field = prefix_field
        BaseBlob.__init__(self, *args, **kwargs)

    @property
    def size(self):
        return self.prefix_field.data

    def unpack(self, s):
        self.prefix_field.unpack(s)
        BaseBlob.unpack(self, s)

    def pack(self, s):
        self.prefix_field.data = len(self)
        self.prefix_field.pack(s)
        BaseBlob.pack(self, s)

class String(BaseField):
    def unpack_data(self, s):
        lc = []
        c = getbyte(s)
        while c != b"\0":
            lc.append(c)
            c = getbyte(s)
        return b"".join(lc).decode()

    def pack_data(self, s, data):
        s.write(data.encode())
        s.write(b"\0")

class FixedString(BaseField):
    def __init__(self, size):
        self.size = size

    def unpack_data(self, s):
        data = getbytes(s, self.size)
        data = data.rstrip(b"\0").decode()
        return data

    def pack_data(self, s, data):
        data = data.encode().ljust(self.size, b"\0")
        s.write(data)

class Index(BaseField):
    def __init__(self, array, index_field):
        self.array = array
        self.index_field = index_field

    def unpack_data(self, s):
        self.index_field.unpack(s)
        return self.array[self.index_field.data].data

    def pack_data(self, s, data):
        try:
            index = self.array.data.index(data)
        except ValueError:
            index = len(self.array)
            self.array.append_data(data)
        self.index_field.data = index
        self.index_field.pack(s)

class Offset(BaseField):
    def unpack_data(self, s):
        return s.tell()

    def pack_data(self, s, data):
        self.data = s.tell()

class Pointer(ContainerField):
    def __init__(self, offset, field):
        self.offset = offset
        self.field = field

    def unpack(self, s):
        with Seek(s, self.offset):
            self.field.unpack(s)

    @property
    def data(self):
        return self.field.data

    @data.setter
    def data(self, v):
        self.field.data = v

    def pack_data(self, s, data):
        pass

class DataPointer(ContainerField):
    def __init__(self, offset_field, field):
        self.offset_field = offset_field
        self.field = field

    def unpack(self, s):
        self.offset_field.unpack(s)
        with Seek(s, self.offset_field.data):
            self.field.unpack(s)

    @property
    def data(self):
        return self.field.data

    @data.setter
    def data(self, v):
        self.field.data = v

class Mapping(BaseField):
    def __init__(self, field, mapping):
        self.field = field
        self.mapping = mapping

    def unpack_data(self, s):
        data = self.field.unpack_data(s)
        return self.mapping[data]

class Flags(BaseField):
    def __init__(self, field, flags):
        self.field = field
        self.flags = flags

    def unpack_data(self, s):
        data = self.field.unpack_data(s)
        flag_data = []
        for mask, name in self.flags:
            if mask & data:
                flag_data.append(name)
        return flag_data
