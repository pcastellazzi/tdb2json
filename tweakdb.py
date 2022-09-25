import csv

from tdb import BinaryStream, TweakDbStream


def csv2dict(path):
    with path.open("rt") as fd:
        return {k: v for k, v in csv.reader(fd)}


class TweakDbReader(BinaryStream, TweakDbStream):
    def __init__(self, stream):
        super().__init__(stream)

    def read_uint64(self):
        # JSON will overflow with true 64 bit integers, use hex instead
        return hex(super().read_uint64())


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    from tdb import BinaryStreamError, TweakDb, TweakDbError, TweakDbStreamError

    SCRIPT_DIR = Path(__file__).parent.absolute()
    RECORD_HASHES_CSV = SCRIPT_DIR / "resources" / "record_hashes.csv"
    TYPE_HASHES_CSV = SCRIPT_DIR / "resources" / "type_hashes.csv"
    TWEAKDB_FILE = SCRIPT_DIR / "tweakdb.bin"

    with TWEAKDB_FILE.open("rb") as fd:
        try:
            record_hashes = csv2dict(RECORD_HASHES_CSV)
            type_hashes = csv2dict(TYPE_HASHES_CSV)
            tdb = TweakDb(TweakDbReader(fd), record_hashes, type_hashes).read()
            json.dump(tdb, sys.stdout)
        except (BinaryStreamError, TweakDbStreamError, TweakDbError) as exc:
            print(exc, file=sys.stderr)
