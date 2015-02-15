from binary import Struct, Magic, Format, BaseArray, String, Blob, FakeWriteStream
from itertools import count

class VPK(Struct):
    def fields(self):
        self.F("magic", Magic(b"\x34\x12\xaa\x55"))
        self.F("version", Format("I"))
        assert self["version"].data == 1
        self.F("index_size", Format("I"))
        self.F("index", NulTerminatedArray(FileType))

    def should_serialize(self, k, f):
        return k != "magic"

    def pack(self, s):
        if self["index_size"].data == 0:
            t = FakeWriteStream()
            self["index"].pack(t)
            self["index_size"].data = t.tell()
        Struct.pack(self, s)

class NulTerminatedArray(BaseArray):
    def unpack(self, s):
        self.field = []
        for i in count():
            f = self.field_fun(i, self)
            try:
                f.unpack(s)
            except StopIteration:
                break
            else:
                self.field.append(f)

    def pack(self, s):
        BaseArray.pack(self, s)
        s.write(b"\x00")

class FileType(Struct):
    def fields(self):
        t = self.F("type", String())
        if t.data == "":
            raise StopIteration
        self.F("directory", NulTerminatedArray(Directory))

class Directory(Struct):
    def fields(self):
        p = self.F("path", String())
        if p.data == "":
            raise StopIteration
        self.F("file", NulTerminatedArray(File))

class File(Struct):
    def fields(self):
        f = self.F("filename", String())
        if f.data == "":
            raise StopIteration
        self.F("crc", Format("I"))
        ps = self.F("preloadsize", Format("H"))
        self.F("archive_index", Format("H"))
        self.F("archive_offset", Format("I"))
        self.F("archive_size", Format("I"))
        self.F("terminator", Magic(b"\xFF\xFF"))
        self.F("preload_data", Blob(ps.data))

    def should_serialize(self, k, f):
        return k not in ["terminator", "preload_data"]
