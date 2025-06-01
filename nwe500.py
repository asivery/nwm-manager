from commons import BitmapDescription, image_from_bitmap, bitmap_from_image, default_main
from dataclasses import dataclass
from os import makedirs
from yaml import dump

def unmangle_bitmap(source: bytes) -> bytes:
    raw_data_fragments = [source[a:a + 240] for a in range(0, 720, 240)]
    translated_data = b''
    for row in range(120):
        translated_data = raw_data_fragments[2][2*row:2*row+2] + raw_data_fragments[1][2*row:2*row+2] + raw_data_fragments[0][2*row:2*row+2] + translated_data
    return translated_data

def mangle_bitmap(source: bytes) -> bytes:
    block_0, block_1, block_2 = b'', b'', b''
    for row in range(120):
        row_data = source[row*6:row*6+6]
        block_2 = row_data[0:2] + block_2
        block_1 = row_data[2:4] + block_1
        block_0 = row_data[4:6] + block_0
    return block_0 + block_1 + block_2

UNMANGLED_BITMAP = BitmapDescription(48, 120, 1)

ddata = []

image_from_bitmap(unmangle_bitmap(ddata[:720]), UNMANGLED_BITMAP).save(f"/ram/unm.png")
mangled = mangle_bitmap(bitmap_from_image('/ram/unm.png', UNMANGLED_BITMAP))

print(mangled == ddata[:720]) # OK
