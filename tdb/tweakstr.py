from binascii import crc32


class TweakStringError(Exception):
    pass


class TweakString:
    MAGIC = 0x0BB1DB57
    VERSION = 1

    def __init__(self, stream):
        self.stream = stream

    def read(self):
        db = {"header": self.read_header()}
        db.update(
            records=self.read_collection(db["header"]["record_count"]),
            flats=self.read_collection(db["header"]["flat_count"]),
            queries=self.read_collection(db["header"]["query_count"]),
        )
        return db

    def read_collection(self, items):
        collection = {}
        for _ in range(items):
            text = self.stream.read_string()
            csum = crc32(bytes(text, "utf8")) + (len(text) << 32)
            collection[hex(csum)] = text
        return collection

    def read_header(self):
        if (magic := self.stream.read_uint32()) != TweakString.MAGIC:
            raise TweakStringError(f"Unknown format {magic:0x}")

        if (version := self.stream.read_uint32()) != TweakString.VERSION:
            raise TweakStringError(f"Ukknown version {version:0x}")

        return {
            "magic": magic,
            "version": version,
            "record_count": self.stream.read_uint32(),
            "flat_count": self.stream.read_uint32(),
            "query_count": self.stream.read_uint32(),
        }
