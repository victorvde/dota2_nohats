from binary import skipbytes, getunpack, getstring

class Seek(object):
    def __init__(self, s, *args, **kwargs):
        self.old_pos = None
        self.s = s
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        self.old_pos = s.tell()
        s.seek(*self.args, **self.kwargs)

    def __exit__(self, exc_type, exc_value, traceback):
        s.seek(self.old_pos)

with open("windrunner.mdl", "rb") as s:
    skipbytes(s, "IDST")
    version, checksum, name, datalength = getunpack(s, "<II64sI")

    eyepos = getunpack(s, "<3f")
    illum = getunpack(s, "<3f")
    hull_min = getunpack(s, "<3f")
    hull_max = getunpack(s, "<3f")
    view_bbmin = getunpack(s, "<3f")
    view_bbmax = getunpack(s, "<3f")

    (flags,) = getunpack(s, "<I")

    bone_count, bone_offset = getunpack(s, "<II")
    bonecontroller_count, bonecontroller_offset = getunpack(s, "<II")
    hitbox_count, hitbox_offset = getunpack(s, "<II")
    localanim_count, localanim_offset = getunpack(s, "<II")
    with Seek(s, localanim_offset):
        for i in xrange(localanim_count):
            this = s.tell()
            baseptr, nameindex, fps, flags, numframes = getunpack(s, "<iifII")
            assert baseptr == -this
            with Seek(s, this + nameindex):
                print 'animname', i, getstring(s, '\0')
            nummovements, movementindex = getunpack(s, "<Ii")
            unused = getunpack(s, "<6I")
            animblock, animindex, numikrules, ikruleindex, animblockikruleindex = getunpack(s, "<iiIii")
            numlocalhierarchy, localhierarchyindex, sectionindex, sectionframes = getunpack(s, "<IiiI")
            zeroframespan, zeroframecount, zeroframeindex, zeroframestalltime = getunpack(s, "<hhif")

    localseq_count, localseq_offset = getunpack(s, "<II")

    with Seek(s, localseq_offset):
        for i in xrange(localseq_count):
            this = s.tell()
            baseptr, labelindex, activitynameindex, flags = getunpack(s, "<iiiI")
            assert baseptr == -this

            activity, actweight, numevents, eventindex = getunpack(s, "<iIIi")
            bbmin = getunpack(s, "<3f")
            bbmax = getunpack(s, "<3f")

            numblends, animindex, movementindex = getunpack(s, "<Iii")
            groupsize = getunpack(s, "<2I")
            paramindex = getunpack(s, "<2I")
            paramstart = getunpack(s, "<2f")
            paramend = getunpack(s, "<2f")
            paramparent = getunpack(s, "<I")

            fadeintime, fadeouttime = getunpack(s, "<ff")
            localentrynode, localexitnode, nodeflags = getunpack(s, "<III")
            entryphase, exitphase, lastframe, nextseq, pose = getunpack(s, "<fffII")
            numikrules, numautolayers, autolayerindex, weightlistindex = getunpack(s, "<IIii")
            posekeyindex, numiklocks, iklockindex = getunpack(s, "<iIi")
            keyvalueindex, keyvaluesize, cycleposeindex = getunpack(s, "<iIi")

            unused = getunpack(s, "<7i")

            with Seek(s, this + labelindex):
                label = getstring(s, '\0')

            with Seek(s, this + activitynameindex):
                activityname = getstring(s, '\0')

            print "label =", label, "+ activity =", activityname