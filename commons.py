from PIL import Image
from dataclasses import dataclass
from os import makedirs, chdir
from os.path import dirname
from argparse import ArgumentParser
from yaml import safe_load as yaml_load
@dataclass
class BitmapDescription:
    width: int
    height: int
    bits_per_pixel: int
    width_px_align: int = 0
    height_px_align: int = 0

    def make_valid(self) -> None:
        if self.width_px_align == 0:
            self.width_px_align = self.width
        if self.height_px_align == 0:
            self.height_px_align = self.height

class BitList:
    __slots__ = ('buffer', 'data', 'b_offset')
    def __init__(self, source_data=None) -> None:
        self.buffer = 0
        self.b_offset = 0
        self.data = [] if source_data is None else list(source_data)
    def push_bits(self, bits: int, count: int) -> None:
        remaining_to_flush = 8 - self.b_offset
        if count > remaining_to_flush:
            # Push to make the buffer whole - align it to zero.
            self.push_bits(bits & ((1 << remaining_to_flush) - 1), remaining_to_flush)
            bits >>= remaining_to_flush
            while count >= 8:
                self.data.append(bits & 0xFF)
                bits >>= 8
                count -= 8
            self.push_bits(bits, count)
        else:
            self.buffer <<= count
            self.buffer |= bits
            self.b_offset += count
        if self.b_offset == 8:
            self.data.append(self.buffer)
            self.buffer, self.b_offset = 0, 0
    def flush(self) -> None:
        if self.b_offset == 0: return
        remaining = 8 - self.b_offset
        self.push_bits(0, remaining)
    def pop_bits(self, count: int) -> int:
        if count == 0: return 0
        output = 0
        if count > self.b_offset:
            if self.b_offset != 0:
                output = self.buffer
                count -= self.b_offset
            self.b_offset = 0
            while count >= 8:
                output <<= 8
                output |= self.data.pop(0)
                count -= 8
            output <<= count
            self.buffer = self.data.pop(0)
            self.b_offset = 8 - count
            output |= (self.buffer >> (8 - count)) & ((1 << count) - 1)
        else:
            if self.b_offset == 0:
                self.b_offset = 8
                self.buffer = self.data.pop(0)
            self.b_offset -= count
            output = (self.buffer >> self.b_offset) & ((1 << count) - 1)
        return output

def rgb_to_luma(r, g, b) -> int:
    if r == g and g == b:
        return r
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def bitmap_from_image(img_src: str, bmpinfo: BitmapDescription) -> bytes:
    bmpinfo.make_valid()

    output = BitList()
    image = Image.open(img_src)
    if image.width != bmpinfo.width or image.height != bmpinfo.height:
        raise BaseException(f"Invalid resolution of file {img_src}! Expected {bmpinfo.width}x{bmpinfo.height}")

    thresholds = list(range(0, 255, 255 // (2 ** bmpinfo.bits_per_pixel)))
    for y in range(0, bmpinfo.height):
        for x in range(0, bmpinfo.width):
            pix = image.getpixel((x, y))[:3]
            luma = rgb_to_luma(*pix)
            for i in range(len(thresholds) - 1, -1, -1):
                if luma >= thresholds[i]:
                    output.push_bits(i, bmpinfo.bits_per_pixel)
                    break
        output.push_bits(0, (bmpinfo.width_px_align - bmpinfo.width) * bmpinfo.bits_per_pixel)
    output.push_bits(0, (bmpinfo.height_px_align - bmpinfo.height) * bmpinfo.bits_per_pixel * bmpinfo.width_px_align)

    output.flush()
    return bytes(output.data)

def image_from_bitmap(bitmap: bytes, bmpinfo: BitmapDescription) -> Image.Image:
    bmpinfo.make_valid()
    thresholds = list(range(0, 255, 255 // (2 ** bmpinfo.bits_per_pixel)))
    bl = BitList(bitmap)
    image = Image.new('RGB', (bmpinfo.width, bmpinfo.height), (0, 0, 0))
    for y in range(0, bmpinfo.height):
        for x in range(0, bmpinfo.width):
            t = thresholds[bl.pop_bits(bmpinfo.bits_per_pixel)]
            image.putpixel((x, y), (t, t, t))
        bl.pop_bits((bmpinfo.width_px_align - bmpinfo.width) * bmpinfo.bits_per_pixel)
    return image

def default_main(config_class, validator, encoder, decoder) -> None:
    parser = ArgumentParser(description=f"Encode or decode {config_class.NAME} screensaver files.")

    subparsers = parser.add_subparsers(dest="mode", required=True, help="Mode of operation")

    encode_parser = subparsers.add_parser('create', help='Create a screensaver')
    encode_parser.add_argument('input_file', help='Input file to encode')
    encode_parser.add_argument('-o', '--output_file', required=True, help='Output file NWM file')

    decode_parser = subparsers.add_parser('disassemble', help='Disassemble a screensaver to edit it')
    decode_parser.add_argument('input_file', help='Input NWM file to disassemble')
    decode_parser.add_argument('-o', '--output_dir', required=True, help='Output directory for decoded files')

    args = parser.parse_args()

    if args.mode == 'create':
        with open(args.input_file, 'r') as c:
            data = yaml_load(c)
            if not validator(data):
                print("Invalid config file!")
                return
            chdir(dirname(args.input_file))
            encoder(config_class(**data), args.output_file)
    elif args.mode == 'disassemble':
        makedirs(args.output_dir, exist_ok=True)
        decoder(args.input_file, args.output_dir)
