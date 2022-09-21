from struct import unpack


class BinaryStreamError(Exception):
    pass


class BinaryStream:
    def __init__(self, stream):
        self._stream = stream

    def read(self, length):
        if length < 0:
            raise BinaryStreamError(f"length must be non-negative, found {length}")

        try:
            data = self._stream.read(length)
        except IOError as exc:
            raise BinaryStreamError(
                f"stream.read() failed, requested {length} bytes. {exc!r}"
            )

        if len(data) != length:
            raise BinaryStreamError(
                f"stream read less than specified amount, expected {length}, found {len(data)}"
            )

        return data

    def read_const(self, expected):
        actual = self.read(len(expected))
        if expected != actual:
            raise BinaryStreamError(f"Expected {expected!r}. Got: {actual!r}")

    def read_float32(self):
        return unpack("<f", self.read(4))[0]

    def read_float64(self):
        return unpack("<d", self.read(8))[0]

    def read_int8(self):
        return unpack("<b", self.read(1))[0]

    def read_int32(self):
        return unpack("<i", self.read(4))[0]

    def read_int64(self):
        return unpack("<q", self.read(8))[0]

    def read_uint8(self):
        return unpack("<B", self.read(1))[0]

    def read_uint32(self):
        return unpack("<I", self.read(4))[0]

    def read_uint64(self):
        return unpack("<Q", self.read(8))[0]

    def seek(self, position, whence=0):
        self._stream.seek(position, whence)

    def tell(self):
        self._stream.tell()


class TweakDbReader(BinaryStream):
    def __init__(self, stream):
        super().__init__(stream)

    def read_array(self, item_func):
        count = self.read_uint32()
        return [item_func() for _ in range(count)]

    def read_bool(self):
        return self.read_uint8() > 0

    def read_field(self):
        field = {
            "name": self.read_vstring(),
            "type": self.read_vstring(),
        }
        self.read_uint32()  # unkown, always 0x8
        match field["type"]:
            case "Float":
                field["value"] = self.read_float32()
            case _:
                raise BinaryStreamError(f"Unknown field type {field['type']}")
        return field

    def read_struct(self, **kw):
        self.read_uint8()  # unknown byte
        fields = {name: reader() for name, reader in kw.items()}
        self.read_vstring()  # always "None"
        return fields

    def read_array_bool(self):
        return self.read_array(self.read_bool)

    def read_array_float32(self):
        return self.read_array(self.read_float32)

    def read_array_int32(self):
        return self.read_array(self.read_int32)

    def read_array_uint64(self):
        return self.read_array(self.read_uint64)

    def read_array_vector2(self):
        return self.read_array(self.read_vector2)

    def read_array_vector3(self):
        return self.read_array(self.read_vector3)

    def read_array_vstring(self):
        count = self.read_int32()
        return [self.read_vstring() for _ in range(count)]

    def read_euler_angle(self):
        return self.read_struct(
            Pitch=self.read_field,
            Roll=self.read_field,
            Yaw=self.read_field,
        )

    def read_flat_reference(self):
        return (self.read_uint64(), self.read_int32())

    def read_quaternion(self):
        return self.read_struct(
            i=self.read_field,
            j=self.read_field,
            k=self.read_field,
            r=self.read_field,
        )

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
            BinaryStreamError("Continuation bit set on 4th byte")

        return -value if negative else value

    def read_vstring(self):
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


class TweakDbError(Exception):
    pass


class TweakDb:
    MAGIC = 0xBB1DB47
    BLOB_VERSION = 0x5
    PARSER_VERSION = 0x4

    FLAT_TYPES_MAP = {
        6391931600911426104: ("String", "read_vstring"),
        11668106722466800856: ("array:Int32", "read_array_int32"),
        2653155825417086166: ("array:CName", "read_array_vstring"),
        15884043155579033811: ("array:Vector2", "read_array_vector2"),
        13406927278374487654: ("array:Float", "read_array_float32"),
        13805995923452593981: ("array:raRef:CResource", "read_array_uint64"),
        10513770639939565077: ("array:String", "read_array_vstring"),
        15884042056067405600: ("array:Vector3", "read_array_vector3"),
        17419964233870898637: ("Quaternion", "read_quaternion"),
        2822982213297947788: ("array:Bool", "read_array_bool"),
        3339382240749630511: ("array:TweakDBID", "read_array_uint64"),
        5941472664459999062: ("EulerAngles", "read_euler_angle"),
        7466806054564151715: ("Vecto3", "read_vector3"),
        12644094645938822750: ("raRef:CResource", "read_uint64"),
        7466804955052523504: ("Vector2", "read_vector2"),
        11953184404591180537: ("CName", "read_vstring"),
        4643797392751916988: ("TweakDBID", "read_uint64"),
        14218562033234752749: ("gamedataLocKeyWrapper", "read_uint64"),
        13376016304518341055: ("Int32", "read_int32"),
        13136800048308857029: ("Float", "read_float32"),
        17851659414560344221: ("Bool", "read_bool"),
    }

    def __init__(self, stream):
        self.stream = TweakDbReader(stream)

    def read(self):
        db = {"header": self.read_header()}
        db.update(
            flats=self.read_flats(db["header"]["flats_offset"]),
            records=self.read_records(db["header"]["records_offset"]),
            queries=self.read_queries(db["header"]["queries_offset"]),
            group_tags=self.read_group_tags(db["header"]["group_tags_offset"]),
        )
        return db

    def read_header(self):
        if (magic := self.stream.read_uint32()) != TweakDb.MAGIC:
            raise TweakDbError(f"Unkown format {magic:0x}")

        if (blob_version := self.stream.read_uint32()) != TweakDb.BLOB_VERSION:
            raise TweakDbError(f"Unsupported BLOB format {blob_version:0x}")

        if (parser_version := self.stream.read_uint32()) != TweakDb.PARSER_VERSION:
            raise TweakDbError(f"Unsupported BLOB format {parser_version:0x}")

        return {
            "magic": magic,
            "blob_version": blob_version,
            "parser_version": parser_version,
            "records_checksum": self.stream.read_uint32(),
            "flats_offset": self.stream.read_uint32(),
            "records_offset": self.stream.read_uint32(),
            "queries_offset": self.stream.read_uint32(),
            "group_tags_offset": self.stream.read_uint32(),
        }

    def read_flats(self, offset):
        self.stream.seek(offset)
        flat_types = self.stream.read_array(self.stream.read_flat_reference)

        flats = {}
        for flat_type, _ in flat_types:
            name, func = self.FLAT_TYPES_MAP[flat_type]
            flats[name] = {
                "values": self.stream.read_array(getattr(self.stream, func)),
                "keys": self.stream.read_array(self.stream.read_flat_reference),
            }

        return flats

    def read_group_tags(self, offset):
        self.stream.seek(offset)
        return self.stream.read_array(
            lambda: (self.stream.read_uint64(), self.stream.read_uint8())
        )

    def read_records(self, offset):
        self.stream.seek(offset)
        return self.stream.read_array(
            lambda: (self.stream.read_uint64(), self.stream.read_uint32())
        )

    def read_queries(self, offset):
        self.stream.seek(offset)
        return self.stream.read_array(
            lambda: (self.stream.read_uint64(), self.stream.read_array_uint64())
        )

if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    tweakdb_file = Path(__file__).parent.absolute() / "tweakdb.bin"
    with tweakdb_file.open("rb") as fd:
        try:
            tdb = TweakDb(fd).read()
        except TweakDbError as exc:
            print(exc, file=sys.stderr)

    json.dump(tdb, sys.stdout)
