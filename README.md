# Vintage Story Map Cache to Image
Creates a PNG image from a map cache file.\
Works for VS version: `1.22.2`

🚨 WARNING: Highly vibecoded

## Setup
Create a virtual environment:
```
$ python3 -m venv .venv
```

Enter virtual environment
```
$ source .venv/bin/activate
```

Install dependencies
```
$ pip install -r requirements.txt
```



## Usage
1. Copy map file to this directory and rename it to `map.db`
2. Enter virtual env `$ source .venv/bin/activate`
3. Run program `$ python map_reader.py`
4. Output file will be named map.png

## Vintage Story Map Cache Format (`map.db`)

SQLite database with two tables: `mappiece` (terrain data) and `blockidmapping` (usually empty).

---

### `mappiece` table

| Column     | Type    | Description                          |
|------------|---------|--------------------------------------|
| `position` | INTEGER | Packed 64-bit chunk coordinate       |
| `data`     | BLOB    | 1024 ABGR pixel colors (protobuf)    |

---

### `position` encoding

A single 64-bit integer with three packed fields:

| Bits  | Field | Description                              |
|-------|-------|------------------------------------------|
| 0–25  | X     | Chunk X coordinate                       |
| 26–51 | Z     | Chunk Z coordinate                       |
| 52–63 | Y     | Map layer (0 = surface)                  |

```python
x = pos & 0x3FFFFFF
z = (pos >> 26) & 0x3FFFFFF
y = (pos >> 52) & 0xFFF
```

> **Note:** Coordinates are in chunk units, but the grid step between adjacent stored
> chunks is not always 1. Use GCD of all coordinate differences to find the true step
> before computing pixel offsets.

---

### `data` encoding

A flat sequence of **1024 protobuf varint records**, one per pixel in the 32×32 map tile.
No compression. No nesting.

Each record is 11 bytes:
- 1 byte tag: `0x08` (protobuf field 1, wire type 0)
- 10 byte varint: a 64-bit integer whose lower 32 bits are an ABGR color

| Bits of lower 32 | Channel | Notes           |
|------------------|---------|-----------------|
| 31–24            | Alpha   | Always `0xFF`   |
| 23–16            | Blue    |                 |
| 15–8             | Green   |                 |
| 7–0              | Red     |                 |

```python
argb = raw & 0xFFFFFFFF
b = (argb >> 16) & 0xFF
g = (argb >> 8)  & 0xFF
r =  argb        & 0xFF
```

Pixels are stored in **row-major order** (X is the inner/fast axis):

```python
lx = i % 32   # column within chunk
lz = i // 32  # row within chunk
```

---

### Rendering

To render the full map to an image, detect the grid step via GCD of all coordinate
differences, then place each 32×32 tile at its normalized position:

```python
ox = ((cx - min_cx) // step_x) * 32
oz = ((cz - min_cz) // step_z) * 32
```