# Copyright (c) 2013 Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from kvlist import KVList

def skip_space(s):
    while True:
        c = s.read(1)
        if c == "/":
            while True:
                c = s.read(1)
                if c == "\n" or c == "":
                    break
        elif not c.isspace():
            break
    return c

def getstring(s):
    lc = []
    while True:
        c = s.read(1)
        assert c != "", "unexpected EOF"
        if c == "\"":
            break
        lc.append(c)
    return "".join(lc)

def load(s):
    items = KVList()
    while True:
        c = skip_space(s)
        if c == "":
            break
        elif c == "\"":
            k, v = parse_item(s, [])
            items[k] = v
        else:
            assert False, u"Unexpected character '{}'".format(c)
    return items

def parse_dict(s, context):
    d = KVList()
    while True:
        c = skip_space(s)
        if c == '}':
            break
        elif c == '"':
            k, v = parse_item(s, context)
            d[k] = v
        else:
            assert False, u"Expected '\"' or '}', got '{}' in {}".format(c, context)
    return d

def parse_item(s, context):
    k = getstring(s)
    c = skip_space(s)
    if c == '"':
        v = getstring(s)
    elif c == '{':
        v = parse_dict(s, context+[k])
    else:
        assert False, u"Expected a string or a dict, got '{}' in {}".format(c, repr(context))
    return k, v

def indent(i, s):
    for j in xrange(i):
        s.write('\t')

def dump(d, s, i=0):
    for k, v in d:
        indent(i, s)
        s.write('"')
        s.write(k)
        s.write('"')
        if isinstance(v, KVList):
            s.write('\n')
            indent(i, s)
            s.write('{')
            s.write('\n')
            dump(v, s, i+1)
            indent(i, s)
            s.write('}')
            s.write('\n')
        elif isinstance(v, basestring):
            s.write('\t\t')
            s.write('"')
            s.write(v)
            s.write('"')
            s.write('\n')
        else:
            assert False, u"Expected KVList or basestring, got {}".format(type(v))
