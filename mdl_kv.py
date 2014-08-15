from mdl import MDL
from argparse import ArgumentParser, FileType
from io import SEEK_END

def model_set_kv(s, kv):
    m = MDL()
    m.unpack(s)

    s.seek(0, SEEK_END)

    b = kv.encode("ascii") + b"\0"

    print(kv)
    print(s.tell())
    print(len(b))

    m["keyvalueindex"].data = s.tell()
    m["keyvaluesize"].data = len(b)

    s.write(b)
    s.seek(0)
    m.pack(s)

def model_attach_effect(s, effect, attachment):
    new_kv = """mdlkeyvalue
{{
    particles {{
        effect {{
            "name" "{}"
            "attachment_type" "follow_attachment"
            "attachment_point" "{}"
        }}
    }}
}}
""".format(effect, attachment)

    model_set_kv(s, new_kv)

def main():
    parser = ArgumentParser(description="Add an effect to a model")
    parser.add_argument("model_file", type=FileType("r+b"))
    parser.add_argument("effect_name")
    parser.add_argument("attachment")
    args = parser.parse_args()

    model_attach_effect(args.model_file, args.effect_name, args.attachment)

if __name__ == "__main__":
    main()
