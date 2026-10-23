"""Điều kiện chờ trên Windows, dùng tọa độ pixel vật lý."""
import base64
import ctypes
import io
from ctypes import wintypes

from PIL import Image, ImageChops, ImageGrab, ImageStat


def foreground_title():
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    handle = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(handle)
    text = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(handle, text, len(text))
    return text.value


def decode_reference(encoded):
    raw = base64.b64decode(encoded, validate=True)
    with Image.open(io.BytesIO(raw)) as image:
        if image.width * image.height > 2_000_000:
            raise ValueError('Ảnh mẫu quá lớn; hãy chọn riêng vùng nút cần chờ.')
        return image.convert('RGB')


def image_matches(reference, screenshot, tolerance):
    if reference.size != screenshot.size:
        return False
    channels = ImageChops.difference(reference, screenshot.convert('RGB')).split()
    difference = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    changed = difference.point(lambda value: 255 if value > 24 else 0)
    return ImageStat.Stat(changed).mean[0] / 255 <= tolerance


def condition_check(action):
    if action.action_type == 'wait_window':
        return lambda: action.window_title.casefold() in foreground_title().casefold()
    reference = decode_reference(action.image)
    bbox = (action.x, action.y, action.x + reference.width, action.y + reference.height)
    return lambda: image_matches(reference, ImageGrab.grab(bbox=bbox, all_screens=True), action.tolerance)
