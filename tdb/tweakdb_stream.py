class TweakDbStreamError(Exception):
    pass


class RedString(str):
    __slots__ = (
        "text",
        "encoding",
    )

    def __init__(self, text, encoding="utf8"):
        self.text = text
        self.encoding = encoding


class TweakDbStream:
    def get_reader(self, type_name):
        IRREGULARS = {
            "gamedataLocKeyWrapper": "uint64",
            "raRef:CResource": "cresource",
        }

        def reader(type_name):
            if type_name in IRREGULARS:
                nt = IRREGULARS[type_name]
            else:
                nt = type_name.lower()
            return getattr(self, f"read_{nt}")

        if type_name.startswith("array:"):
            return lambda: self.read_array(reader(type_name[6:]))

        return reader(type_name)

    def read_array(self, item_func):
        count = self.read_uint32()
        return [item_func() for _ in range(count)]

    def read_dict(self, key_func, val_func):
        count = self.read_uint32()
        return {key_func(): val_func() for _ in range(count)}

    def read_field(self):
        field = {
            "name": self.read_string(),
            "type": self.read_string(),
        }
        self.read_uint32()  # unkown, always 0x8
        match field["type"]:
            case "Float":
                field["value"] = self.read_float32()
            case _:
                raise TweakDbStreamError(f"Unknown field type {field['type']}")
        return field

    def read_struct(self, **kw):
        self.read_uint8()  # unknown byte
        fields = {name: reader() for name, reader in kw.items()}
        self.read_string()  # always "None"
        return fields

    def read_vint32(self):
        # first byte
        # 1-bit sign flag (used on VlqStr to check the encoding)
        # 1-bit continuation flag
        # 6-bit initial value
        b = self.read_uint8()
        negative = (b & 0b1000_0000) != 0
        has_next = (b & 0b0100_0000) != 0
        value = b & 0b0011_1111

        try:
            shift = iter((6, 13, 20, 27))  # we only read up to 4 bytes of data
            while has_next:
                # successive bytes
                # 1-bit continuation flag
                # 7-bit value
                b = self.read_uint8()
                has_next = (b & 0b1000_0000) != 0
                value |= (b & 0b0111_1111) << next(shift)
        except StopIteration:
            TweakDbStreamError("Continuation bit set on 4th byte")

        return -value if negative else value

    def read_bool(self):
        return self.read_uint8() > 0

    def read_byte(self):
        return self.read_uint8()

    def read_cname(self):
        return self.read_string()

    def read_color(self):
        return self.read_struct(
            Red=self.read_field,
            Green=self.read_field,
            Blue=self.read_field,
            Alpha=self.read_field,
        )

    def read_cresource(self):
        return self.read_uint64()

    def read_float(self):
        return self.read_float32()

    def read_eulerangles(self):
        return self.read_struct(
            Pitch=self.read_field,
            Roll=self.read_field,
            Yaw=self.read_field,
        )

    def read_quaternion(self):
        return self.read_struct(
            i=self.read_field,
            j=self.read_field,
            k=self.read_field,
            r=self.read_field,
        )

    def read_redtype(self):
        # keep it in hex for consistency with other type ids
        return hex(self.read_uint32())

    def read_string(self):
        # prefix length as a VLQ signed integer
        prefix = self.read_vint32()

        # string length in characters is the absolute value of the prefix
        length = abs(prefix)

        if length == 0:
            return ""

        # the character width is determined by the sign of the prefix
        if prefix > 0:
            return self.read(length * 2).decode("utf_16le")
        else:
            return self.read(length).decode("utf8")

    def read_vector2(self):
        return self.read_struct(
            X=self.read_field,
            Y=self.read_field,
        )

    def read_vector3(self):
        return self.read_struct(
            X=self.read_field,
            Y=self.read_field,
            Z=self.read_field,
        )

    def read_tweakdbid(self):
        return self.read_uint64()
