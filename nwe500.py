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

@dataclass
class ConfigClass:
    NAME = "NW-E500"
    frames: list[int]
    bitmaps: list[str]
    name: str
    author: str
    u1: int
    u2: int

def _validate_config(conf_file) -> bool:
    try:
        if type(conf_file['frames']) is not list: raise BaseException()
        if type(conf_file['frames'][0]) is not int: raise BaseException()
        if type(conf_file['bitmaps']) is not list: raise BaseException()
        if type(conf_file['bitmaps'][0]) is not str: raise BaseException()
        if type(conf_file['name']) is not str: raise BaseException()
        if type(conf_file['author']) is not str: raise BaseException()
        if type(conf_file['u1']) is not int: raise BaseException()
        if type(conf_file['u2']) is not int: raise BaseException()
        return True
    except BaseException:
        return False

def _encode(config: ConfigClass, output_file: str) -> None:
    with open(output_file, 'wb') as out:
        def short(i: int):
            out.write(i.to_bytes(2, 'big'))
        short(0xEC01)
        short(len(config.frames))
        short(len(config.bitmaps))
        name, author = config.name.encode('ascii'), config.author.encode('ascii')
        short(8 + 2 + 2 + 2 + 2 + len(name) + len(author))
        short(len(name))
        out.write(name)
        short(len(author))
        out.write(author)
        short(config.u1)
        short(config.u2)
        for frame in config.frames:
            out.write(bytes([frame, 0x10]))
            assert frame < len(config.bitmaps)
        for bitmap in config.bitmaps:
            out.write(mangle_bitmap(bitmap_from_image(bitmap, UNMANGLED_BITMAP)))

def _decode(input_file: str, output_dir: str) -> None:
    makedirs(f'{output_dir}/bitmaps', exist_ok=True)
    with open(input_file, 'rb') as inp:
        def short():
            return int.from_bytes(inp.read(2), 'big')
        if short() != 0xEC01: raise BaseException("Not a valid NW-E500 screensaver file!")
        frame_count = short()
        bitmap_count = short()
        short() # data offset
        name_l = short()
        name = inp.read(name_l).decode('ascii')
        author_l = short()
        author = inp.read(author_l).decode('ascii')
        u1 = short()
        u2 = short()
        frames = []
        for _ in range(frame_count):
            fr = short()
            if (fr & 0xff) != 0x10: raise BaseException("Format error!")
            fr >>= 8
            frames.append(fr)
        bitmaps = []
        for bmp in range(bitmap_count):
            bitmaps.append(f'bitmaps/{bmp:02d}.png')
            image_from_bitmap(unmangle_bitmap(inp.read(720)), UNMANGLED_BITMAP).save(f'{output_dir}/bitmaps/{bmp:02d}.png')
        with open(f"{output_dir}/config.yaml", 'w') as e:
            dump({
                'name': name,
                'author': author,
                'u1': u1,
                'u2': u2,
                'bitmaps': bitmaps,
                'frames': frames
            }, e)

if __name__ == "__main__": default_main(ConfigClass, _validate_config, _encode, _decode)
