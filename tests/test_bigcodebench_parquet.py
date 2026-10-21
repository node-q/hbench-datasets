import pathlib
import tempfile
import unittest

from adapters.bigcodebench import parquet
from bigcodebench_fixture import parquet_bytes, snappy_literals

ROWS = [
    {"name": "alpha", "text": "first\nline", "note": None},
    {"name": "beta", "text": "ünïcode ✓", "note": "kept"},
    {"name": "alpha", "text": "", "note": None},
    {"name": "gamma", "text": "x" * 70000, "note": "long"},
    {"name": "beta", "text": "last", "note": ""},
]
COLUMNS = ("name", "text", "note")


class ParquetReaderTest(unittest.TestCase):
    def setUp(self):
        self.directory = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))

    def read(self, data, columns=COLUMNS):
        path = self.directory / "file.parquet"
        path.write_bytes(data)
        return parquet.read_string_columns(path, columns)

    def test_reads_every_layout_a_dataset_file_uses(self):
        for encoding in ("plain", "dictionary"):
            for codec in ("uncompressed", "snappy", "gzip"):
                for page_version in (1, 2):
                    with self.subTest(encoding=encoding, codec=codec, page_version=page_version):
                        data = parquet_bytes(
                            ROWS,
                            COLUMNS,
                            optional=("note",),
                            encoding=encoding,
                            codec=codec,
                            page_version=page_version,
                            rows_per_group=3,
                            rows_per_page=2,
                        )
                        self.assertEqual(self.read(data), ROWS)

    def test_reads_only_the_columns_asked_for(self):
        data = parquet_bytes(ROWS, COLUMNS, optional=("note",), extra_int64_column="count")
        self.assertEqual(self.read(data, ("text",)), [{"text": row["text"]} for row in ROWS])

    def test_snappy_copies_repeat_earlier_output(self):
        literal = bytes([(3 - 1) << 2]) + b"abc"
        one_byte_offset = bytes([(8 - 4) << 2 | 0x01, 3])
        two_byte_offset = bytes([(4 - 1) << 2 | 0x02, 6, 0])
        overlapping = bytes([(6 - 1) << 2 | 0x02, 1, 0])
        block = bytes([21]) + literal + one_byte_offset + two_byte_offset + overlapping
        self.assertEqual(parquet.snappy_decompressed(block), b"abc" + b"abcabcab" + b"cabc" + b"cccccc")

    def test_snappy_literals_round_trip(self):
        data = bytes(range(256)) * 300
        self.assertEqual(parquet.snappy_decompressed(snappy_literals(data)), data)

    def test_refuses_what_it_does_not_read(self):
        data = parquet_bytes(ROWS, COLUMNS, optional=("note",), extra_int64_column="count")
        for broken, message in (
            (b"not a parquet file", "not a Parquet file"),
            (data[:-8] + b"\xff\xff\xff\x7f" + b"PAR1", "footer is longer than the file"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(parquet.ParquetError, message):
                self.read(broken)
        with self.assertRaisesRegex(parquet.ParquetError, "no column missing"):
            self.read(data, ("name", "missing"))
        with self.assertRaisesRegex(parquet.ParquetError, "count is not a byte array"):
            self.read(data, ("count",))
        with self.assertRaisesRegex(parquet.ParquetError, "copies from before its start"):
            parquet.snappy_decompressed(bytes([4, 0x00 << 2 | 0x01, 0x05]))
        with self.assertRaisesRegex(parquet.ParquetError, "codec 6 is not supported"):
            parquet.decompressed(6, b"", 0)


if __name__ == "__main__":
    unittest.main()
