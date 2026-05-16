#! .venv/bin/python3

import sqlite3
from math import gcd
from functools import reduce
from PIL import Image

def read_varint(data: bytes, offset: int):
    result, shift = 0, 0
    while True:
        byte = data[offset]; offset += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80): break
        shift += 7
    return result, offset

def unpack_position(pos: int):
    pos = pos & 0xFFFFFFFFFFFFFFFF
    x = pos & 0x3FFFFFF
    z = (pos >> 26) & 0x3FFFFFF
    y = (pos >> 52) & 0xFFF
    return x, y, z

def read_map_cache(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT position, data FROM mappiece WHERE (position >> 52) & 0xFFF = 0")
    chunks = {}
    for position, data in cursor.fetchall():
        cx, cy, cz = unpack_position(position)
        pixels = []
        offset = 0
        while offset < len(data):
            _tag, offset = read_varint(data, offset)
            raw, offset  = read_varint(data, offset)
            argb = raw & 0xFFFFFFFF
            b = (argb >> 16) & 0xFF
            g = (argb >> 8)  & 0xFF
            r =  argb        & 0xFF
            pixels.append((r, g, b))
        chunks[(cx, cz)] = pixels
    conn.close()
    return chunks

def render_map(chunks: dict, output_path: str = "map.png"):
    if not chunks:
        print("No chunks found."); return

    coords = list(chunks.keys())
    all_cx = sorted(set(c[0] for c in coords))
    all_cz = sorted(set(c[1] for c in coords))

    def find_step(vals):
        diffs = [vals[i+1] - vals[i] for i in range(len(vals)-1)]
        return reduce(gcd, diffs) if diffs else 1

    step_x = find_step(all_cx)
    step_z = find_step(all_cz)
    print(f"Detected grid step: x={step_x}, z={step_z}")

    min_cx, max_cx = all_cx[0], all_cx[-1]
    min_cz, max_cz = all_cz[0], all_cz[-1]

    width  = ((max_cx - min_cx) // step_x + 1) * 32
    height = ((max_cz - min_cz) // step_z + 1) * 32
    print(f"Image size: {width} x {height} px  ({len(chunks)} chunks)")

    img    = Image.new("RGB", (width, height), color=(0, 0, 0))
    pixels = img.load()

    for (cx, cz), colors in chunks.items():
        ox = ((cx - min_cx) // step_x) * 32
        oz = ((cz - min_cz) // step_z) * 32
        for i, rgb in enumerate(colors):
            lx = i % 32
            lz = i // 32
            pixels[ox + lx, oz + lz] = rgb

    img.save(output_path)
    print(f"Saved to {output_path}")

chunks = read_map_cache("map.db")
render_map(chunks)

