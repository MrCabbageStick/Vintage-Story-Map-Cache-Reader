#! .venv/bin/python3

import sqlite3
import struct
from PIL import Image

def unpack_position(pos: int) -> tuple[int, int, int]:
    pos = pos & 0xFFFFFFFFFFFFFFFF
    x = pos & 0x3FFFFFF
    z = (pos >> 26) & 0x3FFFFFF
    y = (pos >> 52) & 0xFFF
    return x, y, z

def read_varint(data: bytes, offset: int) -> tuple[int, int]:
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

def read_map_chunk_colors(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT position, data FROM mappiece")

    chunks = {}
    for position, data in cursor.fetchall():
        cx, cy, cz = unpack_position(position)

        # Parse 1024 ARGB pixels
        pixels = []
        offset = 0
        while offset < len(data):
            tag, offset = read_varint(data, offset)
            raw, offset  = read_varint(data, offset)
            argb = struct.unpack('i', struct.pack('I', raw & 0xFFFFFFFF))[0]
            a = (argb >> 24) & 0xFF   # always 255
            b = (argb >> 16) & 0xFF  # was R
            g = (argb >> 8)  & 0xFF
            r =  argb        & 0xFF  # was B
            pixels.append((r, g, b))

        chunks[(cx, cz)] = pixels
        # print(f"Chunk ({cx}, {cz}): {len(pixels)} pixels, "
        #     f"sample RGB={pixels[0]}, {pixels[1]}, {pixels[2]}")

    conn.close()
    return chunks

def render_map(chunks: dict, output_path="map.png"):
    if not chunks:
        return

    coords = list(chunks.keys())
    min_cx = min(c[0] for c in coords)
    min_cz = min(c[1] for c in coords)
    max_cx = max(c[0] for c in coords)
    max_cz = max(c[1] for c in coords)

    width  = (max_cx - min_cx + 1) * 32
    height = (max_cz - min_cz + 1) * 32
    img = Image.new("RGB", (width, height))
    pixels = img.load()

    for (cx, cz), colors in chunks.items():
        px_origin_x = (cx - min_cx) * 32
        px_origin_z = (cz - min_cz) * 32
        for i, rgb in enumerate(colors):
            lx = i % 32
            lz = i // 32
            pixels[px_origin_x + lx, px_origin_z + lz] = rgb

    img.save(output_path)
    print(f"Saved {width}x{height} map to {output_path}")


chunks = read_map_chunk_colors("map.db")
render_map(chunks)


