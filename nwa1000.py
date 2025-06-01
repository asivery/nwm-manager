from commons import BitmapDescription, image_from_bitmap, bitmap_from_image, default_main
from dataclasses import dataclass
from os import makedirs
from yaml import dump

THUMBNAIL = BitmapDescription(18, 18, 2, 20, 18)
BITMAP = BitmapDescription(80, 80, 2)

@dataclass
class ConfigClass:
    NAME = "NW-A1000"
    frames: list[int]
    bitmaps: list[str]
    thumbnail: str

def _validate_config(conf_file) -> bool:
    try:
        if type(conf_file['frames']) is not list: raise BaseException()
        if type(conf_file['frames'][0]) is not int: raise BaseException()
        if type(conf_file['bitmaps']) is not list: raise BaseException()
        if type(conf_file['bitmaps'][0]) is not str: raise BaseException()
        if type(conf_file['thumbnail']) is not str: raise BaseException()
        return True
    except BaseException:
        return False

def _encode(config: ConfigClass, output_file: str) -> None:
    with open(output_file, 'wb') as out:
        def short(i: int):
            out.write(i.to_bytes(2, 'big'))
        short(0xD301)
        short(len(config.frames))
        short(len(config.bitmaps))
        short(1) # Has thumbnail
        short(0x10)
        out.write(6 * b'\0')
        out.write(bitmap_from_image(config.thumbnail, THUMBNAIL))
        out.write(6 * b'\0')
        for frame in config.frames:
            out.write(bytes([frame, 0x10]))
            assert frame < len(config.bitmaps)
        l = out.tell() & 0xf
        if l:
            out.write((16 - l) * b'\0')
        for bitmap in config.bitmaps:
            out.write(bitmap_from_image(bitmap, BITMAP))
        l = out.tell() & 0xf
        if l:
            out.write((16 - l) * b'\0')

def _decode(input_file: str, output_dir: str) -> None:
    makedirs(f'{output_dir}/bitmaps', exist_ok=True)
    with open(input_file, 'rb') as inp:
        def short():
            return int.from_bytes(inp.read(2), 'big')
        if short() != 0xD301: raise BaseException("Not a valid NW-A1000 screensaver file!")
        frame_count = short()
        bitmap_count = short()
        if short() != 0x01: raise BaseException("No thumbnail!")
        if short() != 0x10: raise BaseException("Invalid offset to data section!")
        inp.read(6)
        thumb_file = f'thumbnail.png'
        image_from_bitmap(inp.read(90), THUMBNAIL).save(f'{output_dir}/{thumb_file}')
        inp.read(6)
        frames = []
        for _ in range(frame_count):
            fr = short()
            if (fr & 0xff) != 0x10: raise BaseException("Format error!")
            fr >>= 8
            frames.append(fr)
        if frame_count*2 & 0x0f:
            inp.read(16 - (frame_count*2 & 0xf))
        bitmaps = []
        for bmp in range(bitmap_count):
            bitmaps.append(f'bitmaps/{bmp:02d}.png')
            image_from_bitmap(inp.read(0x640), BITMAP).save(f'{output_dir}/bitmaps/{bmp:02d}.png')
        with open(f"{output_dir}/config.yaml", 'w') as e:
            dump({
                'thumbnail': thumb_file,
                'bitmaps': bitmaps,
                'frames': frames
            }, e)


if __name__ == "__main__": default_main(ConfigClass, _validate_config, _encode, _decode)

