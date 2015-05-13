# Copyright (c) Victor van den Elzen
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
        if c == '"':
            break
        if c == "\\":
            c = s.read(1)
            if c != '"':
                lc.append("\\")
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
            assert False, "Unexpected character '{}'".format(c)
    return items

def parse_dict(s, context):
    d = KVList()
    while True:
        c = skip_space(s)
        if c == "}":
            break
        elif c == '"':
            k, v = parse_item(s, context)
            d[k] = v
        else:
            assert False, "Expected '\"' or '}}', got '{}' in {}".format(c, context)
    return d

def parse_item(s, context):
    k = getstring(s)
    c = skip_space(s)
    if c == '"':
        v = getstring(s)
    elif c == "{":
        v = parse_dict(s, context+[k])
    else:
        assert False, "Expected a string or a dict, got '{}' in {}".format(c, repr(context))
    return k, v

def indent(i, s):
    for j in range(i):
        s.write("\t")

def dump(d, s, i=0):
    for k, v in d:
        indent(i, s)
        s.write('"')
        s.write(k)
        s.write('"')
        if isinstance(v, KVList):
            s.write("\n")
            indent(i, s)
            s.write("{")
            s.write("\n")
            dump(v, s, i+1)
            indent(i, s)
            s.write("}")
            s.write("\n")
        elif isinstance(v, str):
            s.write("\t\t")
            s.write('"')
            s.write(v)
            s.write('"')
            s.write("\n")
        else:
            assert False, "Expected KVList or string, got {}".format(type(v))
