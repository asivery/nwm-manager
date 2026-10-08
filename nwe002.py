from commons import BitmapDescription, image_from_bitmap, bitmap_from_image, default_main
from dataclasses import dataclass
from os import makedirs
from yaml import dump

BITMAP = BitmapDescription(16, 108, 1)

@dataclass
class ConfigClass:
    NAME = "NW-E002"
    frames: list[int]
    bitmaps: list[str]
    name: str

def _validate_config(conf_file) -> bool:
    try:
        if type(conf_file['frames']) is not list: raise BaseException()
        if type(conf_file['frames'][0]) is not int: raise BaseException()
        if type(conf_file['bitmaps']) is not list: raise BaseException()
        if type(conf_file['bitmaps'][0]) is not str: raise BaseException()
        if type(conf_file['name']) is not str: raise BaseException()
        return True
    except BaseException:
        return False

def _encode(config: ConfigClass, output_file: str) -> None:
    with open(output_file, 'wb') as out:
        def short(i: int):
            out.write(i.to_bytes(2, 'big'))
        short(0xEC02)
        short(len(config.frames))
        short(len(config.bitmaps))
        name = config.name.encode('ascii')
        short(8 + 2 + len(name))
        short(len(name))
        out.write(name)
        for frame in config.frames:
            out.write(bytes([frame, 0x10]))
            assert frame < len(config.bitmaps)
        for bitmap in config.bitmaps:
            out.write(bitmap_from_image(bitmap, BITMAP))

def _decode(input_file: str, output_dir: str) -> None:
    makedirs(f'{output_dir}/bitmaps', exist_ok=True)
    with open(input_file, 'rb') as inp:
        def short():
            return int.from_bytes(inp.read(2), 'big')
        if short() != 0xEC02: raise BaseException("Not a valid NW-E002 screensaver file!")
        frame_count = short()
        bitmap_count = short()
        short() # data offset
        name_l = short()
        name = inp.read(name_l).decode('ascii')
        frames = []
        for _ in range(frame_count):
            fr = short()
            if (fr & 0xff) != 0x10: raise BaseException("Format error!")
            fr >>= 8
            frames.append(fr)
        bitmaps = []
        for bmp in range(bitmap_count):
            bitmaps.append(f'bitmaps/{bmp:02d}.png')
            image_from_bitmap(inp.read(216), BITMAP).save(f'{output_dir}/bitmaps/{bmp:02d}.png')
        with open(f"{output_dir}/config.yaml", 'w') as e:
            dump({
                'name': name,
                'bitmaps': bitmaps,
                'frames': frames
            }, e)

if __name__ == "__main__": default_main(ConfigClass, _validate_config, _encode, _decode)
