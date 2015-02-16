from vpklib import VPK

from collections import OrderedDict
from json import dumps
from os import walk
from os.path import relpath, join
from sys import argv
from zlib import crc32

def test_vpk(f):
    assert f.endswith("_dir.vpk")
    prefix = f[0:-len("_dir.vpk")]

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

def canonical_file(p):
    return p.lower().replace("\\", "/")

def create_vpk(prefix, pack_dir):
    filelist = []
    for (p, ds, fs) in walk(pack_dir):
        rel_p = canonical_file(relpath(p, pack_dir))
        for f in fs:
            filelist.append((rel_p, canonical_file(f)))

    file_types = OrderedDict()
    crc_index = {}
    i = 0
    max_o = 2**20 * 100
    archive_file = "{}_{:03}.vpk".format(prefix, i)
    s = open(archive_file, "wb")
    try:
        for p, f in filelist:
            o = s.tell()
            if o > max_o:
                s.close()
                i += 1
                archive_file = "{}_{:03}.vpk".format(prefix, i)
                s = open(archive_file, "wb")
                o = 0

            with open(join(pack_dir, p, f), "rb") as t:
                d = t.read()
            size = len(d)
            crc = crc32(d)
            name, extension = f.rsplit(".", 1)
            if (crc, size) in crc_index:
                # TODO: actually check equality in case of CRC+size collisions!
                our_i, our_o = crc_index[(crc, size)]
            else:
                crc_index[(crc, size)] = (i, o)
                s.write(d)
                our_i = i
                our_o = o
            file_types.setdefault(extension, OrderedDict()).setdefault(p, []).append((name, our_i, our_o, size, crc))
    finally:
        s.close()

    types = []
    for t, ds in file_types.items():
        dirs = []
        for d, fs in ds.items():
            files = []
            for (name, i, o, size, crc) in fs:
                files.append({
                    "filename": name,
                    "crc": crc,
                    "preloadsize": 0,
                    "archive_index": i,
                    "archive_offset": o,
                    "archive_size": size,
                    "preload_data": b"",
                    })
            dirs.append({
                "path": d,
                "file": files,
                })
        types.append({
            "type": t,
            "directory": dirs,
            })
    v = VPK()
    v.data = {
        "version": 1,
        "index_size": 0,
        "index": types,
        }
    with open("{}_dir.vpk".format(prefix), "wb") as s:
        v.pack(s)

if __name__ == "__main__":
    if argv[1] == "t": # test
        test_vpk(argv[2])
    elif argv[1] == "j": # json
        v = VPK()
        with open(argv[2], "rb") as s:
            v.unpack(s)
        print(dumps(v.serialize(), indent=4))
    elif argv[1] == "a": # create a vpk file
        create_vpk(argv[2], argv[3])
    else:
        assert False, "wrong command line options"
