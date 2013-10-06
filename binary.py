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

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, v):
        return self._data

class Struct(BaseField):
    def __init__(self):
        self.given_data = None
        self.stream = None

    def add_field(self, name, f):
        assert name not in self.field, name
        self.field[name] = f
        if self.given_data:
            f.data = self.given_data.get(name, None)
        elif self.stream:
            f.unpack(self.stream)
        else:
            assert False, "no data or stream"

    def unpack(self, s):
        self.field = OrderedDict()
        self.stream = s
        self.fields()
        self.stream = None

    @property
    def data(self):
        data = OrderedDict()
        for k, v in self.field.iteritems():
            data[k] = v.data
        return data

    @data.setter
    def data(self, v):
        self.field = OrderedDict()
        self.given_data = v
        self.fields()
        self.given_data = None

    def fields(self):
        raise NotImplementedError

class MagicField(BaseField):
    def __init__(self, magic):
        self.magic = magic

    def unpack(self, s):
        data = getbytes(s, len(self.magic))
        assert data == self.magic
        return

    @property
    def data(self):
        return self.magic

    @data.setter
    def data(self, v):
        assert v == self.magic or v is None, v

class FormatField(BaseField):
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
        lc = s.read(size)
        assert len(lc) == size, "Unexpected EOF"
        self._data = unpack(fmt, lc)

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

class BaseArrayField(BaseField):
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

    @property
    def data(self):
        return [f.data for f in self.field]

    @data.setter
    def data(self, v):
        self.field = [self.field_fun(i) for i in xrange(self.array_size())]
        for f, fv in zip(self.field, v):
            f.data = fv

class ArrayField(BaseArrayField):
    def __init__(self, size, *args, **kwargs):
        self.size = size
        BaseArrayField.__init__(self, *args, **kwargs)

    def array_size(self):
        return self.size

class DependentArrayField(BaseArrayField):
    def __init__(self, prefix_field, *args, **kwargs):
        self.prefix_field = prefix_field
        BaseArrayField.__init__(self, *args, **kwargs)

    def array_size(self):
        return self.prefix_field.data

    @BaseArrayField.data.setter
    def data(self, v):
        self.prefix_field.data = len(v)
        BaseArrayField.data.__set__(v)

class PrefixedArrayField(DependentArrayField):
    def unpack(self, s):
        self.prefix_field.unpack(s)
        DependentArrayField.unpack(self, s)

class BlobField(BaseField):
    def __init__(self, size):
        self.size = size

    def unpack(self, s):
        self._data = getbytes(s, self.size)

class DependentBlobField(BaseField):
    def __init__(self, prefix_field):
        self.prefix_field = prefix_field

    def unpack(self, s):
        self._data = getbytes(s, self.prefix_field.data)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, v):
        self.prefix_field.data = len(v)
        self._data = v

class PrefixedBlobField(DependentBlobField):
    def unpack(self, s):
        self.prefix_field.unpack(s)
        DependentBlobField.unpack(self, s)

class StringField(BaseField):
    def unpack(self, s):
        lc = []
        c = getbyte(s)
        while c != "\0":
            lc.append(c)
            c = getbyte(s)
        self._data = "".join(lc)

class IndexField(FormatField):
    def __init__(self, array, *args, **kwargs):
        self.array = array
        FormatField.__init__(self, *args, **kwargs)

    @property
    def data(self):
        return self.array[FormatField.data.__get__(self)]

    @data.setter
    def data(self, v):
        FormatField.data.__set__(self, self.array.index(v))

def fieldmaker(field):
    def maker(i, name, *args, **kwargs):
        f = field(*args, **kwargs)
        i.add_field(name, f)
    return maker

Magic = fieldmaker(MagicField)
Format = fieldmaker(FormatField)
Array = fieldmaker(ArrayField)
DependentArray = fieldmaker(DependentArrayField)
PrefixedArray = fieldmaker(PrefixedArrayField)
String = fieldmaker(StringField)
Blob = fieldmaker(BlobField)
DependentBlob = fieldmaker(DependentBlobField)
PrefixedBlob = fieldmaker(PrefixedBlobField)
Index = fieldmaker(IndexField)
