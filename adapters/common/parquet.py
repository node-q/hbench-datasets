"""Read the rows of a Parquet file with the Python standard library.

Supports what Hugging Face's dataset files use: top-level columns of booleans, integers, floats and
strings, and lists of them, in PLAIN or dictionary encoding, in version 1 or 2 data pages, uncompressed,
Snappy or gzip. read_rows returns one dict per row, keyed by top-level column name.
"""

import struct
import zlib

MAGIC = b"PAR1"
FOOTER_LENGTH_SIZE = 4

BOOLEAN, INT32, INT64, INT96, FLOAT, DOUBLE, BYTE_ARRAY, FIXED_LEN_BYTE_ARRAY = range(8)
REQUIRED, OPTIONAL, REPEATED = range(3)
UNCOMPRESSED, SNAPPY, GZIP = 0, 1, 2
PLAIN, PLAIN_DICTIONARY, RLE, RLE_DICTIONARY = 0, 2, 3, 8
DATA_PAGE, DICTIONARY_PAGE, DATA_PAGE_V2 = 0, 2, 3
UTF8_CONVERTED_TYPE = 0
LIST_CONVERTED_TYPE = 3
STRING_LOGICAL_TYPE_FIELD = 1
LIST_LOGICAL_TYPE_FIELD = 3

COMPACT_STOP = 0
COMPACT_TRUE, COMPACT_FALSE, COMPACT_BYTE, COMPACT_I16, COMPACT_I32, COMPACT_I64 = 1, 2, 3, 4, 5, 6
COMPACT_DOUBLE, COMPACT_BINARY, COMPACT_LIST, COMPACT_SET, COMPACT_MAP, COMPACT_STRUCT = 7, 8, 9, 10, 11, 12
COMPACT_LONG_LIST_SIZE = 15

PLAIN_FORMATS = {INT32: "<i", INT64: "<q", FLOAT: "<f", DOUBLE: "<d"}


class ParquetError(ValueError):
    pass


class CompactReader:
    def __init__(self, data, position=0):
        self.data = data
        self.position = position

    def byte(self):
        if self.position >= len(self.data):
            raise ParquetError("Thrift data ends early")
        value = self.data[self.position]
        self.position += 1
        return value

    def varint(self):
        result = 0
        shift = 0
        while True:
            byte = self.byte()
            result |= (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                return result

    def zigzag(self):
        value = self.varint()
        return (value >> 1) ^ -(value & 1)

    def binary(self):
        length = self.varint()
        value = self.data[self.position : self.position + length]
        if len(value) != length:
            raise ParquetError("Thrift binary ends early")
        self.position += length
        return bytes(value)

    def collection(self):
        header = self.byte()
        size = header >> 4
        element_type = header & 0x0F
        if size == COMPACT_LONG_LIST_SIZE:
            size = self.varint()
        if element_type in (COMPACT_TRUE, COMPACT_FALSE):
            return [self.byte() == COMPACT_TRUE for _ in range(size)]
        return [self.value(element_type) for _ in range(size)]

    def mapping(self):
        size = self.varint()
        if size == 0:
            return {}
        types = self.byte()
        return {self.value(types >> 4): self.value(types & 0x0F) for _ in range(size)}

    def value(self, compact_type):
        if compact_type in (COMPACT_TRUE, COMPACT_FALSE):
            return compact_type == COMPACT_TRUE
        if compact_type == COMPACT_BYTE:
            return struct.unpack("<b", bytes([self.byte()]))[0]
        if compact_type in (COMPACT_I16, COMPACT_I32, COMPACT_I64):
            return self.zigzag()
        if compact_type == COMPACT_DOUBLE:
            value = struct.unpack_from("<d", self.data, self.position)[0]
            self.position += 8
            return value
        if compact_type == COMPACT_BINARY:
            return self.binary()
        if compact_type in (COMPACT_LIST, COMPACT_SET):
            return self.collection()
        if compact_type == COMPACT_MAP:
            return self.mapping()
        if compact_type == COMPACT_STRUCT:
            return self.structure()
        raise ParquetError(f"unknown Thrift compact type {compact_type}")

    def structure(self):
        fields = {}
        last_field_id = 0
        while True:
            header = self.byte()
            if header == COMPACT_STOP:
                return fields
            delta = header >> 4
            field_id = last_field_id + delta if delta else self.zigzag()
            last_field_id = field_id
            fields[field_id] = self.value(header & 0x0F)


def varint_at(data, position):
    reader = CompactReader(data, position)
    return reader.varint(), reader.position


def snappy_decompress(data):
    expected_length, position = varint_at(data, 0)
    output = bytearray()
    while position < len(data):
        tag = data[position]
        position += 1
        kind = tag & 0x03
        if kind == 0:
            length = tag >> 2
            if length >= 60:
                width = length - 59
                length = int.from_bytes(data[position : position + width], "little")
                position += width
            length += 1
            output += data[position : position + length]
            position += length
            continue
        if kind == 1:
            length = ((tag >> 2) & 0x07) + 4
            offset = ((tag >> 5) << 8) | data[position]
            position += 1
        elif kind == 2:
            length = (tag >> 2) + 1
            offset = int.from_bytes(data[position : position + 2], "little")
            position += 2
        else:
            length = (tag >> 2) + 1
            offset = int.from_bytes(data[position : position + 4], "little")
            position += 4
        if offset == 0 or offset > len(output):
            raise ParquetError("Snappy copy reaches before the start of the output")
        start = len(output) - offset
        if length <= offset:
            output += output[start : start + length]
        else:
            pattern = bytes(output[start:])
            output += (pattern * (length // offset + 1))[:length]
    if len(output) != expected_length:
        raise ParquetError(f"Snappy data decompressed to {len(output)} bytes, not {expected_length}")
    return bytes(output)


def decompress(data, codec):
    if codec == UNCOMPRESSED:
        return bytes(data)
    if codec == SNAPPY:
        return snappy_decompress(data)
    if codec == GZIP:
        return zlib.decompress(data, 16 + zlib.MAX_WBITS)
    raise ParquetError(f"compression codec {codec} is not supported")


def bit_width(maximum):
    return maximum.bit_length()


def rle_bit_packed_hybrid(data, width, count):
    values = []
    position = 0
    mask = (1 << width) - 1
    value_bytes = (width + 7) // 8
    while len(values) < count:
        if position >= len(data):
            raise ParquetError("RLE data ends early")
        header, position = varint_at(data, position)
        if header & 1:
            groups = header >> 1
            packed_length = groups * width
            packed = int.from_bytes(data[position : position + packed_length], "little")
            position += packed_length
            values += [(packed >> (index * width)) & mask for index in range(groups * 8)]
        else:
            value = int.from_bytes(data[position : position + value_bytes], "little")
            position += value_bytes
            values += [value] * (header >> 1)
    return values[:count]


def plain_values(data, physical_type, count, type_length=None):
    if physical_type == BYTE_ARRAY:
        values = []
        position = 0
        for _ in range(count):
            (length,) = struct.unpack_from("<I", data, position)
            position += 4
            values.append(bytes(data[position : position + length]))
            position += length
        return values
    if physical_type == BOOLEAN:
        packed = int.from_bytes(data[: (count + 7) // 8], "little")
        return [bool((packed >> index) & 1) for index in range(count)]
    if physical_type == FIXED_LEN_BYTE_ARRAY:
        return [bytes(data[index * type_length : (index + 1) * type_length]) for index in range(count)]
    if physical_type in PLAIN_FORMATS:
        value_format = PLAIN_FORMATS[physical_type]
        return list(struct.unpack_from(f"<{count}{value_format[1]}", data, 0))
    raise ParquetError(f"physical type {physical_type} is not supported")


class Column:
    def __init__(self, path, leaf, ancestors):
        self.path = path
        self.name = path[0]
        self.physical_type = leaf.get(1)
        self.type_length = leaf.get(2)
        chain = [*ancestors, leaf]
        self.max_definition = sum(1 for element in chain if element.get(3) in (OPTIONAL, REPEATED))
        self.max_repetition = sum(1 for element in chain if element.get(3) == REPEATED)
        self.is_string = leaf.get(6) == UTF8_CONVERTED_TYPE or STRING_LOGICAL_TYPE_FIELD in (leaf.get(10) or {})
        if self.max_repetition > 1:
            raise ParquetError(f"column {'.'.join(path)} is nested more than one list deep")
        self.list_definition = None
        if self.max_repetition == 1:
            if len(ancestors) != 2 or ancestors[1].get(3) != REPEATED:
                raise ParquetError(f"column {'.'.join(path)} is not a three-level list")
            self.list_definition = 1 if ancestors[0].get(3) == OPTIONAL else 0

    def converted(self, value):
        return value.decode("utf-8") if self.is_string else value


def schema_columns(schema):
    columns = []
    position = 1

    def walk(ancestors, names):
        nonlocal position
        element = schema[position]
        position += 1
        name = element[4].decode("utf-8")
        children = element.get(5)
        if children:
            for _ in range(children):
                walk([*ancestors, element], [*names, name])
        else:
            columns.append(Column([*names, name], element, ancestors))

    for _ in range(schema[0].get(5, 0)):
        walk([], [])
    return columns


def page_levels(data, maximum, length_prefixed):
    if maximum == 0:
        return None, data
    if length_prefixed:
        (length,) = struct.unpack_from("<I", data, 0)
        encoded, rest = data[4 : 4 + length], data[4 + length :]
    else:
        encoded, rest = data, b""
    return encoded, rest


def decoded_values(data, encoding, column, count, dictionary):
    if encoding == PLAIN:
        return plain_values(data, column.physical_type, count, column.type_length)
    if encoding in (PLAIN_DICTIONARY, RLE_DICTIONARY):
        if dictionary is None:
            raise ParquetError(f"column {'.'.join(column.path)} has a dictionary-encoded page but no dictionary")
        if count == 0:
            return []
        indices = rle_bit_packed_hybrid(data[1:], data[0], count)
        return [dictionary[index] for index in indices]
    raise ParquetError(f"encoding {encoding} is not supported")


def column_chunk_levels_and_values(data, metadata, column):
    codec = metadata[4]
    remaining = metadata[5]
    position = metadata.get(11) if metadata.get(11) is not None else metadata[9]
    position = min(position, metadata[9])
    dictionary = None
    repetitions, definitions, values = [], [], []
    while remaining > 0:
        reader = CompactReader(data, position)
        header = reader.structure()
        page_start = reader.position
        page = data[page_start : page_start + header[3]]
        position = page_start + header[3]
        page_type = header[1]
        if page_type == DICTIONARY_PAGE:
            dictionary_header = header[7]
            raw = plain_values(decompress(page, codec), column.physical_type, dictionary_header[1], column.type_length)
            dictionary = [column.converted(value) for value in raw]
            continue
        if page_type == DATA_PAGE:
            page_header = header[5]
            count, encoding = page_header[1], page_header[2]
            body = decompress(page, codec)
            repetition_bytes, body = page_levels(body, column.max_repetition, True)
            definition_bytes, body = page_levels(body, column.max_definition, True)
        elif page_type == DATA_PAGE_V2:
            page_header = header[8]
            count, encoding = page_header[1], page_header[4]
            definition_length, repetition_length = page_header[5], page_header[6]
            repetition_bytes = page[:repetition_length] if column.max_repetition else None
            definition_bytes = page[repetition_length : repetition_length + definition_length] if column.max_definition else None
            body = page[repetition_length + definition_length :]
            if page_header.get(7, True):
                body = decompress(body, codec)
        else:
            continue
        page_repetitions = (
            rle_bit_packed_hybrid(repetition_bytes, bit_width(column.max_repetition), count)
            if column.max_repetition
            else [0] * count
        )
        page_definitions = (
            rle_bit_packed_hybrid(definition_bytes, bit_width(column.max_definition), count)
            if column.max_definition
            else [column.max_definition] * count
        )
        present = sum(1 for level in page_definitions if level == column.max_definition)
        page_values = decoded_values(body, encoding, column, present, dictionary)
        if encoding == PLAIN:
            page_values = [column.converted(value) for value in page_values]
        repetitions += page_repetitions
        definitions += page_definitions
        values += page_values
        remaining -= count
    return repetitions, definitions, values


def assembled(column, repetitions, definitions, values):
    rows = []
    value_iterator = iter(values)
    if column.max_repetition == 0:
        for level in definitions:
            rows.append(next(value_iterator) if level == column.max_definition else None)
        return rows
    for repetition, level in zip(repetitions, definitions):
        if repetition == 0:
            if level < column.list_definition:
                rows.append(None)
                continue
            rows.append([])
        if level <= column.list_definition:
            continue
        rows[-1].append(next(value_iterator) if level == column.max_definition else None)
    return rows


def file_metadata(data):
    if data[:4] != MAGIC or data[-4:] != MAGIC:
        raise ParquetError("not a Parquet file")
    (footer_length,) = struct.unpack_from("<I", data, len(data) - 8)
    footer_start = len(data) - 8 - footer_length
    return CompactReader(data, footer_start).structure()


def read_rows(path):
    with open(path, "rb") as stream:
        data = stream.read()
    metadata = file_metadata(data)
    columns = schema_columns(metadata[2])
    names = [column.name for column in columns]
    if len(set(names)) != len(names):
        raise ParquetError("several leaf columns share a top-level name")
    rows = []
    for row_group in metadata.get(4, []):
        row_count = row_group[3]
        by_name = {}
        for chunk in row_group[1]:
            chunk_metadata = chunk[3]
            path = [part.decode("utf-8") for part in chunk_metadata[3]]
            column = next(column for column in columns if column.path == path)
            by_name[column.name] = assembled(column, *column_chunk_levels_and_values(data, chunk_metadata, column))
        for name, column_rows in by_name.items():
            if len(column_rows) != row_count:
                raise ParquetError(f"column {name} has {len(column_rows)} rows, its row group {row_count}")
        rows += [{name: by_name[name][index] for name in names} for index in range(row_count)]
    if len(rows) != metadata[3]:
        raise ParquetError(f"read {len(rows)} rows, the file declares {metadata[3]}")
    return rows
