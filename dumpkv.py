from mdl import MDL
from sys import argv

def main():
    (_, filename,) = argv
    m = MDL()
    with open(filename, "rb") as s:
        m.unpack(s)
    print(m["keyvalue"].data)

if __name__ == "__main__":
    main()
