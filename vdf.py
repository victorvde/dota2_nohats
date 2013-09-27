from collections import OrderedDict
from binary import getbyte, getstring

def skip_space(s):
    c = getbyte(s)
    while(c.isspace()):
        c = getbyte(s)
    return c

def load(s):
    c = skip_space(s)
    assert c == '"', u"Expected string literal, got {}".format(c)
    return OrderedDict([parse_item(s, [])])

def parse_dict(s, context):
    d = OrderedDict()
    while True:
        c = skip_space(s)
        if c == '}':
            break
        elif c == '"':
            k, v = parse_item(s, context)
            if k in d:
                del d[k]
            d[k] = v
        else:
            assert False, u"Expected '\"' or '}', got '{}' in {}".format(c, context)
    return d

def parse_item(s, context):
    k = getstring(s, '"')
    c = skip_space(s)
    if c == '"':
        v = getstring(s, '"')
    elif c == '{':
        v = parse_dict(s, context+[k])
    else:
        assert False, u"Expected a string or a dict, got '{}' in {}".format(c, repr(context))
    return k, v

def indent(i, s):
    for j in xrange(i):
        s.write('\t')

def dump(d, s, i=0):
    for k, v in d.iteritems():
        indent(i, s)
        s.write('"')
        s.write(k)
        s.write('"')
        if isinstance(v, OrderedDict):
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
            assert False, u"Expected OrderedDict or basestring, got {}".format(type(v))

if __name__ == "__main__":
    with open("items_game.txt", "rb") as input:
        d = load(input)
    with open("items_game_dump.txt", "wb") as output:
        dump(d, output)