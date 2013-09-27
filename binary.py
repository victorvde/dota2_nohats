from struct import unpack, calcsize

def getbytes(s, n):
    b = s.read(n)
    assert len(b) == n, "Unexpected EOF"
    return b

def getbyte(s):
    return getbytes(s, 1)

def getstring(s, delimiter):
    lc = []
    c = getbyte(s)
    while c != delimiter:
        lc.append(c)
        c = getbyte(s)
    return ''.join(lc)

def getunpack(s, fmt):
    size = calcsize(fmt)
    lc = s.read(size)
    assert len(lc) == size, "Unexpected EOF"
    return unpack(fmt, lc)

def skipbytes(s, bs):
    b = getbytes(s, len(bs))
    assert b == bs
