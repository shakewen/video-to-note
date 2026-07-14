import struct
import zlib
from pathlib import Path
from typing import Any


class PNGValidationError(ValueError):
    pass


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def inspect_png(path: Path, blank_threshold: int = 250) -> dict[str, Any]:
    if not path.exists():
        raise PNGValidationError(f"PNG file does not exist: {path}")
    try:
        from PIL import Image
    except ImportError:
        Image = None

    if Image is not None:
        try:
            with Image.open(path) as image:
                if image.format != "PNG":
                    raise PNGValidationError("not a PNG file")
                if image.mode != "RGBA":
                    raise PNGValidationError("only 8-bit RGBA PNG files are supported")
                width, height = image.size
                extrema = image.getextrema()
        except (OSError, ValueError) as error:
            raise PNGValidationError(f"cannot decode PNG: {error}") from error
        is_blank = all(channel_min >= blank_threshold for channel_min, _ in extrema[:3])
        return {"width": width, "height": height, "is_blank": is_blank, "pixel_count": width * height}

    width, height, color_type, bit_depth, idat_parts = _read_png_chunks(path)
    is_blank = _inspect_compressed_rgba_scanlines(
        width, height, color_type, bit_depth, idat_parts, blank_threshold
    )
    pixel_count = width * height
    return {"width": width, "height": height, "is_blank": is_blank, "pixel_count": pixel_count}


def plan_crop_slices(total_height: int, viewport_width: int, slice_height: int = 1800, overlap: int = 100) -> list[dict[str, int]]:
    if total_height <= 0:
        raise ValueError("total_height must be greater than 0")
    if viewport_width <= 0:
        raise ValueError("viewport_width must be greater than 0")
    if slice_height <= overlap:
        raise ValueError("slice_height must be greater than overlap")

    slices = []
    step = slice_height - overlap
    y = 0
    index = 1
    while True:
        if y + slice_height >= total_height:
            y = max(0, total_height - slice_height)
            slices.append({"index": index, "x": 0, "y": y, "width": viewport_width, "height": min(slice_height, total_height)})
            break
        slices.append({"index": index, "x": 0, "y": y, "width": viewport_width, "height": slice_height})
        y += step
        index += 1
    return slices


def _read_png(path: Path) -> tuple[int, int, int, int, bytes]:
    width, height, color_type, bit_depth, idat_parts = _read_png_chunks(path)
    try:
        decompressed = zlib.decompress(b"".join(idat_parts))
    except zlib.error as error:
        raise PNGValidationError(f"cannot decompress PNG: {error}") from error
    return width, height, color_type, bit_depth, decompressed


def _read_png_chunks(path: Path) -> tuple[int, int, int, int, list[bytes]]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise PNGValidationError("not a PNG file")

    offset = len(PNG_SIGNATURE)
    width = height = color_type = bit_depth = None
    idat_parts = []

    while offset < len(data):
        if offset + 8 > len(data):
            raise PNGValidationError("truncated PNG chunk")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        name = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        offset += 12 + length

        if name == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", chunk_data)
        elif name == b"IDAT":
            idat_parts.append(chunk_data)
        elif name == b"IEND":
            break

    if width is None or height is None or color_type is None or bit_depth is None:
        raise PNGValidationError("PNG missing IHDR")
    if not idat_parts:
        raise PNGValidationError("PNG missing IDAT")

    return width, height, color_type, bit_depth, idat_parts


def _inspect_compressed_rgba_scanlines(
    width: int,
    height: int,
    color_type: int,
    bit_depth: int,
    idat_parts: list[bytes],
    blank_threshold: int,
) -> bool:
    if bit_depth != 8 or color_type != 6:
        raise PNGValidationError("only 8-bit RGBA PNG files are supported")

    bytes_per_pixel = 4
    row_length = width * bytes_per_pixel
    encoded_row_length = row_length + 1
    previous = bytearray(row_length)
    pending = bytearray()
    decompressor = zlib.decompressobj()
    rows_seen = 0
    is_blank = True

    def consume_rows() -> None:
        nonlocal previous, rows_seen, is_blank
        while len(pending) >= encoded_row_length and rows_seen < height:
            filter_type = pending[0]
            row = bytearray(pending[1:encoded_row_length])
            del pending[:encoded_row_length]
            recon = _apply_png_filter(filter_type, row, previous, bytes_per_pixel)
            previous = recon
            rows_seen += 1
            if is_blank:
                for pixel_offset in range(0, row_length, bytes_per_pixel):
                    if (
                        recon[pixel_offset] < blank_threshold
                        or recon[pixel_offset + 1] < blank_threshold
                        or recon[pixel_offset + 2] < blank_threshold
                    ):
                        is_blank = False
                        break

    try:
        for compressed in idat_parts:
            for offset in range(0, len(compressed), 16 * 1024):
                pending.extend(decompressor.decompress(compressed[offset : offset + 16 * 1024]))
                consume_rows()
        pending.extend(decompressor.flush())
        consume_rows()
    except zlib.error as error:
        raise PNGValidationError(f"cannot decompress PNG: {error}") from error

    if rows_seen != height or pending:
        raise PNGValidationError("truncated PNG scanline")
    return is_blank


def _decode_rgba_scanlines(width: int, height: int, color_type: int, bit_depth: int, data: bytes) -> list[tuple[int, int, int, int]]:
    if bit_depth != 8 or color_type != 6:
        raise PNGValidationError("only 8-bit RGBA PNG files are supported")

    bytes_per_pixel = 4
    row_length = width * bytes_per_pixel
    previous = bytearray(row_length)
    offset = 0
    pixels = []

    for _ in range(height):
        if offset >= len(data):
            raise PNGValidationError("truncated PNG scanline")
        filter_type = data[offset]
        offset += 1
        row = bytearray(data[offset : offset + row_length])
        offset += row_length
        if len(row) != row_length:
            raise PNGValidationError("truncated PNG row")
        recon = _apply_png_filter(filter_type, row, previous, bytes_per_pixel)
        previous = recon
        for pixel_offset in range(0, row_length, bytes_per_pixel):
            pixels.append(tuple(recon[pixel_offset : pixel_offset + bytes_per_pixel]))
    return pixels


def _inspect_rgba_scanlines(
    width: int,
    height: int,
    color_type: int,
    bit_depth: int,
    data: bytes,
    blank_threshold: int,
) -> tuple[bool, int]:
    if bit_depth != 8 or color_type != 6:
        raise PNGValidationError("only 8-bit RGBA PNG files are supported")

    bytes_per_pixel = 4
    row_length = width * bytes_per_pixel
    previous = bytearray(row_length)
    offset = 0
    is_blank = True

    for _ in range(height):
        if offset >= len(data):
            raise PNGValidationError("truncated PNG scanline")
        filter_type = data[offset]
        offset += 1
        row = bytearray(data[offset : offset + row_length])
        offset += row_length
        if len(row) != row_length:
            raise PNGValidationError("truncated PNG row")
        recon = _apply_png_filter(filter_type, row, previous, bytes_per_pixel)
        previous = recon
        if is_blank:
            for pixel_offset in range(0, row_length, bytes_per_pixel):
                if (
                    recon[pixel_offset] < blank_threshold
                    or recon[pixel_offset + 1] < blank_threshold
                    or recon[pixel_offset + 2] < blank_threshold
                ):
                    is_blank = False
                    break

    return is_blank, width * height


def _apply_png_filter(filter_type: int, row: bytearray, previous: bytearray, bytes_per_pixel: int) -> bytearray:
    result = bytearray(len(row))
    for index, value in enumerate(row):
        left = result[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        up = previous[index]
        upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        if filter_type == 0:
            predictor = 0
        elif filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = up
        elif filter_type == 3:
            predictor = (left + up) // 2
        elif filter_type == 4:
            predictor = _paeth(left, up, upper_left)
        else:
            raise PNGValidationError(f"unsupported PNG filter: {filter_type}")
        result[index] = (value + predictor) & 0xFF
    return result


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left
