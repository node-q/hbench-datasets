import struct

STRING, LIST_OF_STRINGS = "string", "list"
BYTE_ARRAY = 6
OPTIONAL, REPEATED = 1, 2
UTF8, LIST = 0, 3
UNCOMPRESSED, SNAPPY = 0, 1
PLAIN, RLE, RLE_DICTIONARY = 0, 3, 8
DATA_PAGE, DICTIONARY_PAGE, DATA_PAGE_V2 = 0, 2, 3
I32, I64, BINARY, LIST_TYPE, STRUCT, TRUE, FALSE = 5, 6, 8, 9, 12, 1, 2


def varint(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def zigzag(value):
    return varint((value << 1) ^ (value >> 63))


def thrift_struct(fields):
    out = bytearray()
    last = 0
    for field_id, kind, value in fields:
        if value is None:
            continue
        compact_type = (TRUE if value else FALSE) if kind == "bool" else kind
        delta = field_id - last
        out += bytes([(delta << 4) | compact_type]) if 0 < delta <= 15 else bytes([compact_type]) + zigzag(field_id)
        last = field_id
        if kind in (I32, I64):
            out += zigzag(value)
        elif kind == BINARY:
            out += varint(len(value)) + value
        elif kind == STRUCT:
            out += value
        elif kind == LIST_TYPE:
            element_type, items = value
            out += bytes([(len(items) << 4) | element_type]) if len(items) < 15 else bytes([0xF0 | element_type]) + varint(len(items))
            for item in items:
                if element_type == I32:
                    out += zigzag(item)
                elif element_type == BINARY:
                    out += varint(len(item)) + item
                else:
                    out += item
    return bytes(out + b"\x00")


def snappy_literals(data):
    out = bytearray(varint(len(data)))
    for start in range(0, len(data), 60):
        chunk = data[start : start + 60]
        out += bytes([(len(chunk) - 1) << 2]) + chunk
    return bytes(out)


def rle_runs(values, width):
    out = bytearray()
    value_bytes = (width + 7) // 8
    index = 0
    while index < len(values):
        run = 1
        while index + run < len(values) and values[index + run] == values[index]:
            run += 1
        out += varint(run << 1) + values[index].to_bytes(value_bytes, "little")
        index += run
    return bytes(out)


def plain_strings(values):
    return b"".join(struct.pack("<I", len(value.encode())) + value.encode() for value in values)


def levels_v1(values, width):
    encoded = rle_runs(values, width)
    return struct.pack("<I", len(encoded)) + encoded


def string_column_levels(values):
    definitions = [1 if value is not None else 0 for value in values]
    return [], definitions, [value for value in values if value is not None], 1, 0


def list_column_levels(rows):
    repetitions, definitions, present = [], [], []
    for row in rows:
        if row is None:
            repetitions.append(0)
            definitions.append(0)
        elif not row:
            repetitions.append(0)
            definitions.append(1)
        else:
            for index, element in enumerate(row):
                repetitions.append(0 if index == 0 else 1)
                definitions.append(3 if element is not None else 2)
                if element is not None:
                    present.append(element)
    return repetitions, definitions, present, 3, 1


def column_pages(levels, codec, dictionary, page_version):
    repetitions, definitions, present, max_definition, max_repetition = levels
    compress = snappy_literals if codec == SNAPPY else (lambda data: data)
    pages = b""
    dictionary_page = None
    if dictionary:
        entries = sorted(set(present))
        dictionary_body = plain_strings(entries)
        dictionary_page = thrift_struct(
            [
                (1, I32, DICTIONARY_PAGE),
                (2, I32, len(dictionary_body)),
                (3, I32, len(compress(dictionary_body))),
                (7, STRUCT, thrift_struct([(1, I32, len(entries)), (2, I32, PLAIN)])),
            ]
        ) + compress(dictionary_body)
        width = max(1, (len(entries) - 1).bit_length())
        values = bytes([width]) + rle_runs([entries.index(value) for value in present], width)
        encoding = RLE_DICTIONARY
    else:
        values = plain_strings(present)
        encoding = PLAIN
    count = len(definitions)
    if page_version == 2:
        repetition_bytes = rle_runs(repetitions, 1) if max_repetition else b""
        definition_bytes = rle_runs(definitions, max_definition.bit_length())
        compressed_values = compress(values)
        header = thrift_struct(
            [
                (1, I32, DATA_PAGE_V2),
                (2, I32, len(repetition_bytes) + len(definition_bytes) + len(values)),
                (3, I32, len(repetition_bytes) + len(definition_bytes) + len(compressed_values)),
                (
                    8,
                    STRUCT,
                    thrift_struct(
                        [
                            (1, I32, count),
                            (2, I32, count - len(present)),
                            (3, I32, sum(1 for level in repetitions if level == 0) if max_repetition else count),
                            (4, I32, encoding),
                            (5, I32, len(definition_bytes)),
                            (6, I32, len(repetition_bytes)),
                            (7, "bool", codec != UNCOMPRESSED),
                        ]
                    ),
                ),
            ]
        )
        pages = header + repetition_bytes + definition_bytes + compressed_values
    else:
        body = (levels_v1(repetitions, 1) if max_repetition else b"") + levels_v1(definitions, max_definition.bit_length()) + values
        compressed = compress(body)
        header = thrift_struct(
            [
                (1, I32, DATA_PAGE),
                (2, I32, len(body)),
                (3, I32, len(compressed)),
                (5, STRUCT, thrift_struct([(1, I32, count), (2, I32, encoding), (3, I32, RLE), (4, I32, RLE)])),
            ]
        )
        pages = header + compressed
    return dictionary_page, pages, count


def write_parquet(path, columns, rows, codec=SNAPPY, dictionary=True, page_version=1):
    data = bytearray(b"PAR1")
    chunks = []
    for name, kind in columns:
        values = [row.get(name) for row in rows]
        levels = string_column_levels(values) if kind == STRING else list_column_levels(values)
        dictionary_page, pages, count = column_pages(levels, codec, dictionary and kind == STRING, page_version)
        dictionary_offset = None
        if dictionary_page:
            dictionary_offset = len(data)
            data += dictionary_page
        data_offset = len(data)
        data += pages
        path_in_schema = [name.encode()] if kind == STRING else [name.encode(), b"list", b"element"]
        metadata = thrift_struct(
            [
                (1, I32, BYTE_ARRAY),
                (2, LIST_TYPE, (I32, [PLAIN, RLE] + ([RLE_DICTIONARY] if dictionary_page else []))),
                (3, LIST_TYPE, (BINARY, path_in_schema)),
                (4, I32, codec),
                (5, I64, count),
                (6, I64, len(data) - (dictionary_offset or data_offset)),
                (7, I64, len(data) - (dictionary_offset or data_offset)),
                (9, I64, data_offset),
                (11, I64, dictionary_offset),
            ]
        )
        chunks.append(thrift_struct([(2, I64, dictionary_offset or data_offset), (3, STRUCT, metadata)]))
    schema = [thrift_struct([(4, BINARY, b"schema"), (5, I32, len(columns))])]
    for name, kind in columns:
        if kind == STRING:
            schema.append(thrift_struct([(1, I32, BYTE_ARRAY), (3, I32, OPTIONAL), (4, BINARY, name.encode()), (6, I32, UTF8)]))
        else:
            schema += [
                thrift_struct([(3, I32, OPTIONAL), (4, BINARY, name.encode()), (5, I32, 1), (6, I32, LIST)]),
                thrift_struct([(3, I32, REPEATED), (4, BINARY, b"list"), (5, I32, 1)]),
                thrift_struct([(1, I32, BYTE_ARRAY), (3, I32, OPTIONAL), (4, BINARY, b"element"), (6, I32, UTF8)]),
            ]
    row_group = thrift_struct([(1, LIST_TYPE, (STRUCT, chunks)), (2, I64, len(data)), (3, I64, len(rows))])
    footer = thrift_struct([(1, I32, 1), (2, LIST_TYPE, (STRUCT, schema)), (3, I64, len(rows)), (4, LIST_TYPE, (STRUCT, [row_group]))])
    data += footer + struct.pack("<I", len(footer)) + b"PAR1"
    with open(path, "wb") as stream:
        stream.write(data)
