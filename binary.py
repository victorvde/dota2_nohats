from struct import pack, unpack, calcsize
from collections import OrderedDict

def getbytes(s, n):
    b = s.read(n)
    assert len(b) == n, "Unexpected EOF"
    return b

def getbyte(s):
    return getbytes(s, 1)

class BaseField(object):
    def unpack(self, s):
        raise NotImplementedError

    def pack(self, s):
        raise NotImplementedError

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, v):
        return self._data

class Struct(BaseField):
    def add_field(self, name, f):
        assert name not in self.field, name
        self.field[name] = f
        input_type, v = self.input
        if input_type == "data":
            f.data = v.get(name, None)
        elif input_type == "stream":
            f.unpack(v)
        else:
            assert False, input_type

    def F(self, name, f):
        return self.add_field(name, f)

    def unpack(self, s):
        self.field = OrderedDict()
        self.input = ("stream", s)
        self.fields()
        del self.input

    def pack(self, s):
        for name, f in self.field.iteritems():
            f.pack(s)

    @property
    def data(self):
        data = OrderedDict()
        for k, v in self.field.iteritems():
            data[k] = v.data
        return data

    @data.setter
    def data(self, v):
        self.field = OrderedDict()
        self.input = ("data", v)
        self.fields()
        del self.input

    def fields(self):
        raise NotImplementedError

class Magic(BaseField):
    def __init__(self, magic):
        self.magic = magic

    def unpack(self, s):
        data = getbytes(s, len(self.magic))
        assert data == self.magic

    def pack(self, s):
        data = s.write(self.magic)

    @property
    def data(self):
        return self.magic

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

    def unpack(self, s):
        fmt = self.bosa + self.fmt
        size = calcsize(fmt)
        b = getbytes(s, size)
        self._data = unpack(fmt, b)

    def pack(self, s):
        s.write(pack(self.fmt, *self._data))

    @property
    def data(self):
        if self.single == 1:
            assert len(self._data) == 1
            return self._data[0]
        else:
            return self._data

    @data.setter
    def data(self, v):
        if self.single:
            self._data = (v,)
        else:
            self._data = v

class BaseArray(BaseField):
    def __init__(self, field_function=None, indexed_function=None):
        if indexed_function is None:
            indexed_function = lambda i: field_function()
        self.field_fun = indexed_function

    def array_size(self):
        raise NotImplementedError

    def unpack(self, s):
        self.field = [self.field_fun(i) for i in xrange(self.array_size())]
        for f in self.field:
            f.unpack(s)

    def pack(self, s):
        for f in self.field:
            f.pack(s)

    @property
    def data(self):
        return [f.data for f in self.field]

    @data.setter
    def data(self, v):
        self.field = [self.field_fun(i) for i in xrange(self.array_size())]
        for f, fv in zip(self.field, v):
            f.data = fv

class Array(BaseArray):
    def __init__(self, size, *args, **kwargs):
        self.size = size
        BaseArray.__init__(self, *args, **kwargs)

    def array_size(self):
        return self.size

class DependentArray(BaseArray):
    def __init__(self, prefix_field, *args, **kwargs):
        self.prefix_field = prefix_field
        BaseArray.__init__(self, *args, **kwargs)

    def array_size(self):
        return self.prefix_field.data

    @BaseArray.data.setter
    def data(self, v):
        self.prefix_field.data = len(v)
        BaseArray.data.__set__(v)

class PrefixedArray(DependentArray):
    def unpack(self, s):
        self.prefix_field.unpack(s)
        DependentArray.unpack(self, s)

    def pack(self, s):
        self.prefix_field.pack(s)
        DependentArray.pack(self, s)

class Blob(BaseField):
    def __init__(self, size):
        self.size = size

    def unpack(self, s):
        self._data = getbytes(s, self.size)

    def pack(self, s):
        s.write(self._data)

class DependentBlob(BaseField):
    def __init__(self, prefix_field):
        self.prefix_field = prefix_field

    def unpack(self, s):
        self._data = getbytes(s, self.prefix_field.data)

    def pack(self, s):
        s.write(self._data)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, v):
        self.prefix_field.data = len(v)
        self._data = v

class PrefixedBlob(DependentBlob):
    def unpack(self, s):
        self.prefix_field.unpack(s)
        DependentBlob.unpack(self, s)

    def pack(self, s):
        self.prefix_field.pack(s)
        DependentBlob.pack(self, s)

class String(BaseField):
    def unpack(self, s):
        lc = []
        c = getbyte(s)
        while c != "\0":
            lc.append(c)
            c = getbyte(s)
        self._data = "".join(lc)

    def pack(self, s):
        s.write(self._data)
        s.write('\0')

class Index(Format):
    def __init__(self, array, *args, **kwargs):
        self.array = array
        Format.__init__(self, *args, **kwargs)

    @property
    def data(self):
        return self.array[Format.data.__get__(self)]

    @data.setter
    def data(self, v):
        Format.data.__set__(self, self.array.index(v))
