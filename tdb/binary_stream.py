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

    def read_int16(self):
        return unpack("<h", self.read(2))[0]

    def read_int32(self):
        return unpack("<i", self.read(4))[0]

    def read_int64(self):
        return unpack("<q", self.read(8))[0]

    def read_uint8(self):
        return unpack("<B", self.read(1))[0]

    def read_uint16(self):
        return unpack("<H", self.read(2))[0]

    def read_uint32(self):
        return unpack("<I", self.read(4))[0]

    def read_uint64(self):
        return unpack("<Q", self.read(8))[0]

    def seek(self, position, whence=0):
        self._stream.seek(position, whence)

    def tell(self):
        return self._stream.tell()
