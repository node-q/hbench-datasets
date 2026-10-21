"""Read the string columns of a flat Parquet file with the Python standard library.

BigCodeBench is published on Hugging Face as Parquet. This reads what such a file holds: a flat schema of
required or optional UTF-8 byte-array columns, in data pages of version 1 or 2, PLAIN or dictionary
encoded, uncompressed, Snappy or gzip. Anything else is refused with ParquetError.
"""

import gzip
import struct

MAGIC = b"PAR1"
FOOTER_LENGTH_BYTES = 4

COMPACT_STOP = 0
COMPACT_TRUE = 1
COMPACT_FALSE = 2
COMPACT_BYTE = 3
COMPACT_I16 = 4
COMPACT_I32 = 5
COMPACT_I64 = 6
COMPACT_DOUBLE = 7
COMPACT_BINARY = 8
COMPACT_LIST = 9
COMPACT_SET = 10
COMPACT_MAP = 11
COMPACT_STRUCT = 12

BYTE_ARRAY = 6
REQUIRED = 0
OPTIONAL = 1

UNCOMPRESSED = 0
SNAPPY = 1
GZIP = 2

DATA_PAGE = 0
DICTIONARY_PAGE = 2
DATA_PAGE_V2 = 3

PLAIN = 0
PLAIN_DICTIONARY = 2
RLE = 3
RLE_DICTIONARY = 8
DICTIONARY_ENCODINGS = (PLAIN_DICTIONARY, RLE_DICTIONARY)

FILE_SCHEMA = 2
FILE_NUM_ROWS = 3
FILE_ROW_GROUPS = 4
SCHEMA_TYPE = 1
SCHEMA_REPETITION = 3
SCHEMA_NAME = 4
SCHEMA_NUM_CHILDREN = 5
ROW_GROUP_COLUMNS = 1
ROW_GROUP_NUM_ROWS = 3
CHUNK_META_DATA = 3
META_TYPE = 1
META_PATH = 3
META_CODEC = 4
META_NUM_VALUES = 5
META_TOTAL_COMPRESSED_SIZE = 7
META_DATA_PAGE_OFFSET = 9
META_DICTIONARY_PAGE_OFFSET = 11
PAGE_TYPE = 1
PAGE_UNCOMPRESSED_SIZE = 2
PAGE_COMPRESSED_SIZE = 3
PAGE_DATA_HEADER = 5
PAGE_DICTIONARY_HEADER = 7
PAGE_DATA_HEADER_V2 = 8
DATA_NUM_VALUES = 1
DATA_ENCODING = 2
DATA_DEFINITION_ENCODING = 3
DICTIONARY_NUM_VALUES = 1
DICTIONARY_ENCODING = 2
V2_NUM_VALUES = 1
V2_NUM_NULLS = 2
V2_ENCODING = 4
V2_DEFINITION_LENGTH = 5
V2_REPETITION_LENGTH = 6
V2_IS_COMPRESSED = 7


class ParquetError(ValueError):
    pass


class CompactReader:
    def __init__(self, data, position=0):
        self.data = data
        self.position = position

    def byte(self):
        if self.position >= len(self.data):
            raise ParquetError("the file ends inside its metadata")
        value = self.data[self.position]
        self.position += 1
        return value

    def varint(self):
        result = 0
        shift = 0
        while True:
            value = self.byte()
            result |= (value & 0x7F) << shift
            if not value & 0x80:
                return result
            shift += 7

    def zigzag(self):
        value = self.varint()
        return (value >> 1) ^ -(value & 1)

    def binary(self):
        length = self.varint()
        end = self.position + length
        if end > len(self.data):
            raise ParquetError("the file ends inside its metadata")
        value = self.data[self.position : end]
        self.position = end
        return value

    def value(self, compact_type):
        if compact_type == COMPACT_TRUE:
            return True
        if compact_type == COMPACT_FALSE:
            return False
        if compact_type == COMPACT_BYTE:
            return self.byte()
        if compact_type in (COMPACT_I16, COMPACT_I32, COMPACT_I64):
            return self.zigzag()
        if compact_type == COMPACT_DOUBLE:
            end = self.position + 8
            value = struct.unpack("<d", self.data[self.position : end])[0]
            self.position = end
            return value
        if compact_type == COMPACT_BINARY:
            return self.binary()
        if compact_type in (COMPACT_LIST, COMPACT_SET):
            return self.list()
        if compact_type == COMPACT_MAP:
            return self.map()
        if compact_type == COMPACT_STRUCT:
            return self.struct()
        raise ParquetError(f"unknown Thrift compact type {compact_type}")

    def list(self):
        header = self.byte()
        size = header >> 4
        element_type = header & 0x0F
        if size == 15:
            size = self.varint()
        if element_type in (COMPACT_TRUE, COMPACT_FALSE):
            return [self.byte() == COMPACT_TRUE for _ in range(size)]
        return [self.value(element_type) for _ in range(size)]

    def map(self):
        size = self.varint()
        if size == 0:
            return {}
        types = self.byte()
        return {self.value(types >> 4): self.value(types & 0x0F) for _ in range(size)}

    def struct(self):
        fields = {}
        field_id = 0
        while True:
            header = self.byte()
            compact_type = header & 0x0F
            if compact_type == COMPACT_STOP:
                return fields
            delta = header >> 4
            field_id = field_id + delta if delta else self.zigzag()
            fields[field_id] = self.value(compact_type)


def snappy_decompressed(data):
    reader = CompactReader(data)
    expected_length = reader.varint()
    position = reader.position
    output = bytearray()
    while position < len(data):
        tag = data[position]
        position += 1
        element_type = tag & 0x03
        if element_type == 0:
            length = (tag >> 2) + 1
            if length > 60:
                extra_bytes = length - 60
                length = int.from_bytes(data[position : position + extra_bytes], "little") + 1
                position += extra_bytes
            output += data[position : position + length]
            position += length
            continue
        if element_type == 1:
            length = ((tag >> 2) & 0x07) + 4
            offset = ((tag >> 5) << 8) | data[position]
            position += 1
        else:
            offset_bytes = 2 if element_type == 2 else 4
            length = (tag >> 2) + 1
            offset = int.from_bytes(data[position : position + offset_bytes], "little")
            position += offset_bytes
        if offset == 0 or offset > len(output):
            raise ParquetError("a Snappy block copies from before its start")
        start = len(output) - offset
        for index in range(length):
            output.append(output[start + index])
    if len(output) != expected_length:
        raise ParquetError(f"a Snappy block holds {len(output)} bytes, its header says {expected_length}")
    return bytes(output)


def decompressed(codec, data, uncompressed_size):
    if codec == UNCOMPRESSED:
        result = data
    elif codec == SNAPPY:
        result = snappy_decompressed(data)
    elif codec == GZIP:
        result = gzip.decompress(data)
    else:
        raise ParquetError(f"compression codec {codec} is not supported")
    if len(result) != uncompressed_size:
        raise ParquetError(f"a page decompresses to {len(result)} bytes, its header says {uncompressed_size}")
    return result


def hybrid_values(data, bit_width, count):
    reader = CompactReader(data)
    values = []
    value_bytes = (bit_width + 7) // 8
    mask = (1 << bit_width) - 1
    while len(values) < count:
        header = reader.varint()
        if header & 1:
            groups = header >> 1
            packed_length = groups * bit_width
            packed = int.from_bytes(data[reader.position : reader.position + packed_length], "little")
            reader.position += packed_length
            values += [(packed >> (index * bit_width)) & mask for index in range(groups * 8)]
        else:
            run_length = header >> 1
            value = int.from_bytes(data[reader.position : reader.position + value_bytes], "little")
            reader.position += value_bytes
            values += [value] * run_length
    return values[:count]


def plain_byte_arrays(data, count):
    values = []
    position = 0
    for _ in range(count):
        if position + 4 > len(data):
            raise ParquetError("a PLAIN page ends inside a value")
        length = struct.unpack_from("<I", data, position)[0]
        position += 4
        values.append(data[position : position + length])
        position += length
    return values


def page_values(encoding, data, count, dictionary):
    if encoding == PLAIN:
        return plain_byte_arrays(data, count)
    if encoding in DICTIONARY_ENCODINGS:
        if dictionary is None:
            raise ParquetError("a dictionary-encoded page comes before its dictionary")
        if count == 0:
            return []
        indices = hybrid_values(data[1:], data[0], count)
        try:
            return [dictionary[index] for index in indices]
        except IndexError:
            raise ParquetError("a dictionary index is out of range") from None
    raise ParquetError(f"value encoding {encoding} is not supported")


def with_nulls(values, definition_levels):
    present = iter(values)
    return [next(present) if level else None for level in definition_levels]


def data_page_v1(header, page, optional, dictionary):
    count = header[DATA_NUM_VALUES]
    definition_levels = [1] * count
    if optional:
        if header[DATA_DEFINITION_ENCODING] != RLE:
            raise ParquetError(f"definition level encoding {header[DATA_DEFINITION_ENCODING]} is not supported")
        levels_length = struct.unpack_from("<I", page, 0)[0]
        definition_levels = hybrid_values(page[4 : 4 + levels_length], 1, count)
        page = page[4 + levels_length :]
    values = page_values(header[DATA_ENCODING], page, sum(definition_levels), dictionary)
    return with_nulls(values, definition_levels)


def data_page_v2(header, page, optional, codec, uncompressed_size, dictionary):
    count = header[V2_NUM_VALUES]
    definition_length = header[V2_DEFINITION_LENGTH]
    repetition_length = header[V2_REPETITION_LENGTH]
    if repetition_length:
        raise ParquetError("repeated columns are not supported")
    definition_levels = hybrid_values(page[:definition_length], 1, count) if optional else [1] * count
    values_data = page[definition_length:]
    if header.get(V2_IS_COMPRESSED, True):
        values_data = decompressed(codec, values_data, uncompressed_size - definition_length)
    values = page_values(header[V2_ENCODING], values_data, count - header[V2_NUM_NULLS], dictionary)
    return with_nulls(values, definition_levels)


def column_chunk_values(data, metadata, optional):
    codec = metadata[META_CODEC]
    start = metadata.get(META_DICTIONARY_PAGE_OFFSET, metadata[META_DATA_PAGE_OFFSET])
    start = min(start, metadata[META_DATA_PAGE_OFFSET])
    end = start + metadata[META_TOTAL_COMPRESSED_SIZE]
    expected = metadata[META_NUM_VALUES]
    reader = CompactReader(data, start)
    dictionary = None
    values = []
    while reader.position < end and len(values) < expected:
        header = reader.struct()
        page = data[reader.position : reader.position + header[PAGE_COMPRESSED_SIZE]]
        reader.position += header[PAGE_COMPRESSED_SIZE]
        page_type = header[PAGE_TYPE]
        uncompressed_size = header[PAGE_UNCOMPRESSED_SIZE]
        if page_type == DICTIONARY_PAGE:
            dictionary_header = header[PAGE_DICTIONARY_HEADER]
            if dictionary_header[DICTIONARY_ENCODING] not in (PLAIN, PLAIN_DICTIONARY):
                raise ParquetError(f"dictionary encoding {dictionary_header[DICTIONARY_ENCODING]} is not supported")
            page = decompressed(codec, page, uncompressed_size)
            dictionary = plain_byte_arrays(page, dictionary_header[DICTIONARY_NUM_VALUES])
        elif page_type == DATA_PAGE:
            page = decompressed(codec, page, uncompressed_size)
            values += data_page_v1(header[PAGE_DATA_HEADER], page, optional, dictionary)
        elif page_type == DATA_PAGE_V2:
            values += data_page_v2(header[PAGE_DATA_HEADER_V2], page, optional, codec, uncompressed_size, dictionary)
        else:
            raise ParquetError(f"page type {page_type} is not supported")
    if len(values) != expected:
        raise ParquetError(f"a column chunk holds {len(values)} values, its metadata says {expected}")
    return values


def file_metadata(data):
    if len(data) < 2 * len(MAGIC) + FOOTER_LENGTH_BYTES or data[:4] != MAGIC or data[-4:] != MAGIC:
        raise ParquetError("not a Parquet file")
    footer_length = struct.unpack("<I", data[-8:-4])[0]
    footer_start = len(data) - 8 - footer_length
    if footer_start < len(MAGIC):
        raise ParquetError("the footer is longer than the file")
    return CompactReader(data, footer_start).struct()


def flat_columns(schema):
    root, *columns = schema
    if root.get(SCHEMA_NUM_CHILDREN) != len(columns) or any(SCHEMA_NUM_CHILDREN in column for column in columns):
        raise ParquetError("only flat schemas are supported")
    described = {}
    for column in columns:
        name = column[SCHEMA_NAME].decode("utf-8")
        repetition = column.get(SCHEMA_REPETITION, REQUIRED)
        if repetition not in (REQUIRED, OPTIONAL):
            raise ParquetError(f"column {name} is repeated")
        described[name] = (column.get(SCHEMA_TYPE), repetition == OPTIONAL)
    return described


def read_string_columns(path, names):
    with open(path, "rb") as stream:
        data = stream.read()
    metadata = file_metadata(data)
    columns = flat_columns(metadata[FILE_SCHEMA])
    missing = [name for name in names if name not in columns]
    if missing:
        raise ParquetError(f"the file has no column {', '.join(missing)}")
    for name in names:
        if columns[name][0] != BYTE_ARRAY:
            raise ParquetError(f"column {name} is not a byte array")
    values = {name: [] for name in names}
    for row_group in metadata[FILE_ROW_GROUPS]:
        for chunk in row_group[ROW_GROUP_COLUMNS]:
            chunk_metadata = chunk[CHUNK_META_DATA]
            name = b".".join(chunk_metadata[META_PATH]).decode("utf-8")
            if name in values:
                values[name] += column_chunk_values(data, chunk_metadata, columns[name][1])
    row_count = metadata[FILE_NUM_ROWS]
    rows = []
    for index in range(row_count):
        row = {}
        for name in names:
            if len(values[name]) != row_count:
                raise ParquetError(f"column {name} holds {len(values[name])} values in {row_count} rows")
            value = values[name][index]
            row[name] = None if value is None else value.decode("utf-8")
        rows.append(row)
    return rows
