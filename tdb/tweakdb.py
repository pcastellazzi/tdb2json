class TweakDbError(Exception):
    pass


class TweakDb:
    MAGIC = 0xBB1DB47
    BLOB_VERSION = 0x5
    PARSER_VERSION = 0x4

    def __init__(self, stream, record_hashes, type_hashes):
        self.record_hashes = record_hashes
        self.type_hashes = type_hashes
        self.stream = stream

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
            raise TweakDbError(f"Unknown format {magic:0x}")

        if (blob_version := self.stream.read_uint32()) != TweakDb.BLOB_VERSION:
            raise TweakDbError(f"Unsupported BLOB format {blob_version:0x}")

        if (parser_version := self.stream.read_uint32()) != TweakDb.PARSER_VERSION:
            raise TweakDbError(f"Unsupported PARSER format {parser_version:0x}")

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

        flat_type_counts = self.stream.read_dict(
            self.stream.read_uint64, self.stream.read_uint32
        )

        flats = {}
        flat_type_values = {}
        for type_hash, _ in flat_type_counts.items():
            type_name = self.type_hashes[type_hash]
            flat_type_values[type_hash] = self.stream.read_array(
                self.stream.get_reader(type_name)
            )

            flat_type_key_count = self.stream.read_int32()
            for _ in range(flat_type_key_count):
                key_hash = self.stream.read_tweakdbid()
                val_index = self.stream.read_int32()
                flats[key_hash] = (type_name, flat_type_values[type_hash][val_index])

        return flats

    def read_group_tags(self, offset):
        self.stream.seek(offset)
        return self.stream.read_dict(self.stream.read_tweakdbid, self.stream.read_byte)

    def read_records(self, offset):
        self.stream.seek(offset)
        return self.stream.read_dict(
            self.stream.read_tweakdbid,
            lambda: self.record_hashes[self.stream.read_redtype()],
        )

    def read_queries(self, offset):
        self.stream.seek(offset)
        return self.stream.read_dict(
            self.stream.read_tweakdbid,
            lambda: self.stream.read_array(self.stream.read_tweakdbid),
        )
