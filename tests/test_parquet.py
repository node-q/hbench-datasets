import pathlib
import tempfile
import unittest

from adapters.common import parquet
from parquet_fixture import LIST_OF_STRINGS, STRING, UNCOMPRESSED, write_parquet

ROWS = [
    {"id": "a", "text": "first\r\nline", "tests": ["t1", "t2"]},
    {"id": "b", "text": None, "tests": []},
    {"id": "c", "text": "first\r\nline", "tests": None},
    {"id": "d", "text": "ünïcode", "tests": ["t3", None, "t4"]},
]
COLUMNS = [("id", STRING), ("text", STRING), ("tests", LIST_OF_STRINGS)]


class ParquetTest(unittest.TestCase):
    def setUp(self):
        self.directory = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))

    def read(self, **options):
        path = self.directory / "rows.parquet"
        write_parquet(path, COLUMNS, ROWS, **options)
        return parquet.read_rows(path)

    def test_reads_snappy_dictionary_pages_and_lists(self):
        self.assertEqual(self.read(), ROWS)

    def test_reads_uncompressed_plain_pages(self):
        self.assertEqual(self.read(codec=UNCOMPRESSED, dictionary=False), ROWS)

    def test_reads_version_2_data_pages(self):
        self.assertEqual(self.read(page_version=2), ROWS)
        self.assertEqual(self.read(page_version=2, dictionary=False, codec=UNCOMPRESSED), ROWS)

    def test_refuses_a_file_that_is_not_parquet(self):
        path = self.directory / "rows.parquet"
        path.write_bytes(b"not parquet at all")
        with self.assertRaises(parquet.ParquetError):
            parquet.read_rows(path)

    def test_snappy_copies_may_overlap_their_output(self):
        compressed = bytes([9, 0 << 2]) + b"a" + bytes([(3 << 2) | 2]) + (1).to_bytes(2, "little") + bytes([(0 << 2) | 1 | (0 << 5), 1])
        self.assertEqual(parquet.snappy_decompress(compressed), b"aaaaaaaaa")

    def test_snappy_refuses_a_copy_before_the_start(self):
        with self.assertRaises(parquet.ParquetError):
            parquet.snappy_decompress(bytes([4, (3 << 2) | 2]) + (5).to_bytes(2, "little"))

    def test_rle_and_bit_packed_runs(self):
        bit_packed = bytes([(1 << 1) | 1, 0b10001000, 0b11000110, 0b11111010])
        self.assertEqual(parquet.rle_bit_packed_hybrid(bit_packed, 3, 8), [0, 1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(parquet.rle_bit_packed_hybrid(bytes([5 << 1, 2]), 2, 5), [2] * 5)


if __name__ == "__main__":
    unittest.main()
