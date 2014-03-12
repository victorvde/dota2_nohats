from pcf import PCF, Attribute

new_color = None

def get_key(d, name, value):
    l = [x for x in d if name in x and x[name].data == value]
    if len(l) == 1:
        return l[0]
    else:
        return None

def clamp(x):
    return min(255, max(0, round(x)))

def fix_colors(psd):
    modify = False

    initializers = get_key(psd.attribute, "name", "initializers")
    assert initializers["type"].data == 15
    l = initializers["data"]

    for i in reversed(range(len(l))):
        attribute = l[i].data.attribute
        function_name = get_key(attribute, "name", "functionName")
        assert function_name["type"].data == 5
        if function_name["data"].data == "Remap Control Point to Vector":
            output_field = get_key(attribute, "name", "output field")
            assert output_field["type"].data == 2
            assert output_field["data"].data == 6
            modify = "copy"
            scale = get_key(attribute, "name", "output is scalar of initial random range")
            if scale:
                assert scale["type"].data == 4
                if scale["data"].data is True:
                    modify = "scale"
            del l[i]

    for i in reversed(range(len(l))):
        attribute = l[i].data.attribute
        function_name = get_key(attribute, "name", "functionName")
        assert function_name["type"].data == 5
        if function_name["data"].data == "Color Random":
            if modify == "scale":
                color1 = get_key(attribute, "name", "color1")
                if color1:
                    assert color1["type"].data == 8
                    color1["data"].data = tuple(clamp(new_color[i] / 255. * color1["data"].data[i]) for i in range(4))
                else:
                    attribute.append_data({
                        "name": "color1",
                        "type": 8,
                        "data": new_color,
                    })
                color2 = get_key(attribute, "name", "color2")
                if color2:
                    assert color2["type"].data == 8
                    color2["data"].data = tuple(clamp(new_color[i] / 255. * color2["data"].data[i]) for i in range(4))
                else:
                    attribute.append_data({
                        "name": "color2",
                        "type": 8,
                        "data": new_color,
                    })
                modify = False
            elif modify == "copy":
                del l[i]

    if modify in ["scale", "copy"]:
        attribute = psd.attribute
        color = get_key(attribute, "name", "color")
        if color:
            assert color["type"].data == 8
            color["data"].data = (new_color[0], new_color[1], new_color[2], color["data"].data[3])
        else:
            attribute.append_data({
                "name": "color",
                "type": 8,
                "data": new_color,
            })
        modify = False

    assert modify is False, modify

def recursive_edit(psd, psdl):
    fix_colors(psd)

    children = get_key(psd.attribute, "name", "children")
    assert children["type"].data == 15
    for child in children["data"]:
        real_child = get_key(child.data.attribute, "name", "child")
        if real_child["data"] not in psdl:
            recursive_edit(real_child["data"].data, psdl)

def main(src, dest):
    p = PCF()
    with open(src, "rb") as s:
        p.unpack(s)
    p.minimize()
    main_element = p["elements"][0]
    assert main_element["type"].data == "DmElement"
    assert len(main_element.attribute) == 1
    main_attribute = main_element.attribute[0]
    assert main_attribute["name"].data == "particleSystemDefinitions"
    assert main_attribute["type"].data == 15
    psdl = main_attribute["data"]
    for i in range(len(psdl)):
        psd = psdl[i].data
        recursive_edit(psd, psdl)

    with open(dest, "wb") as s:
        p.full_pack(s)

if __name__ == "__main__":
    from sys import argv
    src = argv[1]
    dest = argv[2]
    new_color = [int(argv[3]), int(argv[4]), int(argv[5]), 255]
    main(src, dest)
