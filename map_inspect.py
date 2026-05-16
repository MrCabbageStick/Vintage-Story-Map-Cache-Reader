#! .venv/bin/python3

import sqlite3

def read_varint(data: bytes, offset: int) -> tuple[int, int]:
    """Returns (value, new_offset)"""
    result = 0
    shift = 0
    while True:
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result, offset

def inspect_blob(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT position, data FROM mappiece LIMIT 3")

    for position, data in cursor.fetchall():
        print(f"\n=== position={position}, data length={len(data)} ===")
        print(f"Full hex: {data.hex()}")

        # Try parsing as repeated protobuf varints
        offset = 0
        entry = 0
        while offset < len(data) and entry < 10:
            tag, offset = read_varint(data, offset)
            field = tag >> 3
            wire  = tag & 0x7
            print(f"  field={field} wire={wire}", end="")
            if wire == 0:  # varint
                val, offset = read_varint(data, offset)
                # try zigzag decode too
                zz = (val >> 1) ^ -(val & 1)
                print(f"  raw={val}  zigzag={zz}")
            elif wire == 2:  # length-delimited
                length, offset = read_varint(data, offset)
                chunk = data[offset:offset+length]
                offset += length
                print(f"  length={length}  hex={chunk[:16].hex()}")
            else:
                print(f"  (unknown wire type, stopping)")
                break
            entry += 1

    conn.close()

inspect_blob("map.db")