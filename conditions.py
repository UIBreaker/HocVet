"""Điều kiện chờ trên Windows, dùng tọa độ pixel vật lý."""
import base64
import ctypes
import io
from ctypes import wintypes

from PIL import Image, ImageChops, ImageGrab, ImageStat


def foreground_window():
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    return user32.GetForegroundWindow()


def window_at(x, y):
    user32 = ctypes.windll.user32
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    return user32.GetAncestor(user32.WindowFromPoint(wintypes.POINT(x, y)), 2)


def window_title(handle):
    user32 = ctypes.windll.user32
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    length = user32.GetWindowTextLengthW(handle)
    text = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(handle, text, len(text))
    return text.value


def foreground_title():
    return window_title(foreground_window())


def title_matches(expected, actual):
    return expected.casefold() in actual.casefold()


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
        return lambda handle=None: title_matches(action.window_title, window_title(handle) if handle else foreground_title())
    reference = decode_reference(action.image)
    bbox = (action.x, action.y, action.x + reference.width, action.y + reference.height)
    return lambda: image_matches(reference, ImageGrab.grab(bbox=bbox, all_screens=True), action.tolerance)
