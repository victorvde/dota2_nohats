# Copyright (c) 2013 Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from kvlist import KVList

def read_until(s, i, l):
    start = i
    while i < len(s) and s[i] not in l:
        i+=1
    return (s[start:i], i)

def skip_while(s, i, l):
    while i < len(s) and s[i] in l:
        i+=1
    return i

def parse_socket_value(s):
    data = KVList()
    i = 0
    while True:
        i = skip_while(s, i, " ")
        if i >= len(s):
            break
        token, i = read_until(s, i, ": ")
        if s[i] == ":":
            i += 1
            i = skip_while(s, i, " ")
            if s[i] == "'":
                i += 1
                value, i = read_until(s, i, "'")
                assert s[i] == "'"
                i += 1
            else:
                value, i = read_until(s, i, " ")
            data[token] = value
        elif s[i] == " ":
            i = skip_while(s, i, " ")
            lbracket, i = read_until(s, i, " ")
            assert lbracket == "{", token
            subsocket, i = read_until(s, i, "}")
            assert s[i] == "}", s[i]
            i += 1
            value = parse_socket_value(subsocket)
            data[token] = value
    return data
