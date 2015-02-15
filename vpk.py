from binary import Struct, Magic, Format, BaseArray, String, Blob
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

if __name__ == "__main__":
    from sys import argv
    from json import dumps
    from zlib import crc32

    assert argv[1].endswith("_dir.vpk")
    prefix = argv[1][0:-len("_dir.vpk")]

    v = VPK()
    with open(prefix+"_dir.vpk", "rb") as s:
        v.unpack(s)
    for ft in v["index"]:
        for p in ft["directory"]:
            for f in p["file"]:
                print("File {}/{}.{}".format(p["path"].data, f["filename"].data, ft["type"].data))
                if f["archive_index"].data == 0x7FFF:
                    archive_file = "{}_dir.vpk".format(prefix)
                    o = f["archive_offset"].data + v["index_size"].data + 12
                else:
                    archive_file = "{}_{:03}.vpk".format(prefix, f["archive_index"].data)
                    o = f["archive_offset"].data
                n = f["archive_size"].data
                print("Archive {} offset {} size {}".format(archive_file, o, n))
                with open(archive_file, "rb") as s:
                    s.seek(o)
                    d = s.read(n)
                    assert len(d) == n, (len(d), n)
                d = f["preload_data"].data + d
                my_crc = crc32(d) & 0xFFFFFFFF
                print("CRC {} = {}, {}".format(my_crc, f["crc"].data, my_crc == f["crc"].data))

    print(dumps(v.serialize(), indent=4))
