from tdb import BinaryStream, TweakDbStream


class TweakStringReader(BinaryStream, TweakDbStream):
    def __init__(self, stream):
        super().__init__(stream)


if __name__ == "__main__":
    import json
    import sys
    from binascii import crc32
    from pathlib import Path

    from tdb import BinaryStreamError, TweakDbStreamError, TweakString, TweakStringError

    SCRIPT_DIR = Path(__file__).parent.absolute()
    TWEAKSTRING_FILE = SCRIPT_DIR / "tweakstr.bin"

    with TWEAKSTRING_FILE.open("rb") as fd:
        try:
            tstr = TweakString(TweakStringReader(fd)).read()

            for strtype in ("flats", "records", "queries"):
                for _, strval in tstr[strtype].items():
                    strcrc = crc32(bytes(strval, "utf8"))
                    print(f"{strval},0x{strcrc:X},ToTweakDBID{{ hash = 0x{strcrc:X}, length = {len(strval)} }}")

            # json.dump(tstr, sys.stdout)
        except (BinaryStreamError, TweakDbStreamError, TweakStringError) as exc:
            print(exc, file=sys.stderr)

