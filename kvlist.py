# Copyright (c) 2013 Victor van den Elzen
# Released under the Expat license, see LICENSE file for details

from collections import MutableMapping

class KVList(MutableMapping):
    def __init__(self, *args, **kwargs):
        self.list = []
        self.update(*args, **kwargs)

    def last_index(self, key):
        l = len(self.list)
        for i in xrange(l):
            if self.list[l-i-1][0] == key:
                return l-i-1
        return None

    def __getitem__(self, key):
        idx = self.last_index(key)
        if idx is None:
            raise KeyError(key)
        return self.list[idx][1]

    def __setitem__(self, key, value):
        self.list.append((key, value))

    def __delitem__(self, key):
        idx = self.last_index(key)
        if idx is None:
            raise KeyError(key)
        del self.list[idx]

    def __iter__(self):
        for e in self.list:
            yield e

    def __len__(self):
        return len(self.list)

    def keys(self):
        keys = []
        for k, v in self:
            if k not in keys:
                keys.append(k)
        return keys

    def values(self):
        return [v for k, v in self]
