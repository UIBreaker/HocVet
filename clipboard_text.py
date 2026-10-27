"""Clipboard Unicode dùng được từ luồng phát, không gọi Tk ngoài luồng giao diện."""
import ctypes
from ctypes import wintypes
import time


def set_clipboard_text(text, cancel_event=None):
    if not isinstance(text,str) or len(text)>1000000 or '\0' in text:
        raise ValueError('Nội dung clipboard không hợp lệ.')
    user=ctypes.WinDLL('user32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    user.CreateWindowExW.argtypes=[wintypes.DWORD,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD,
        ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.HWND,wintypes.HMENU,wintypes.HINSTANCE,ctypes.c_void_p]
    user.CreateWindowExW.restype=wintypes.HWND
    user.DestroyWindow.argtypes=[wintypes.HWND]
    user.OpenClipboard.argtypes=[wintypes.HWND]
    user.SetClipboardData.argtypes=[wintypes.UINT,wintypes.HANDLE]
    user.SetClipboardData.restype=wintypes.HANDLE
    kernel.GlobalAlloc.argtypes=[wintypes.UINT,ctypes.c_size_t]
    kernel.GlobalAlloc.restype=wintypes.HGLOBAL
    kernel.GlobalLock.argtypes=[wintypes.HGLOBAL]
    kernel.GlobalLock.restype=ctypes.c_void_p
    kernel.GlobalUnlock.argtypes=[wintypes.HGLOBAL]
    kernel.GlobalFree.argtypes=[wintypes.HGLOBAL]
    owner=user.CreateWindowExW(0,'STATIC','HocVet Clipboard',0,0,0,0,0,None,None,None,None)
    if not owner: raise ctypes.WinError(ctypes.get_last_error())
    opened=False;handle=None
    try:
        deadline=time.monotonic()+2
        while not user.OpenClipboard(owner):
            if time.monotonic()>=deadline: raise RuntimeError('Clipboard đang bận. Hãy dừng sao chép ở ứng dụng khác rồi thử lại.')
            if cancel_event:
                if cancel_event.wait(.02): raise InterruptedError('Đã dừng sao chép dữ liệu.')
            else: time.sleep(.02)
        opened=True
        if cancel_event and cancel_event.is_set(): raise InterruptedError('Đã dừng sao chép dữ liệu.')
        data=(text+'\0').encode('utf-16-le')
        handle=kernel.GlobalAlloc(2,len(data))
        if not handle: raise ctypes.WinError(ctypes.get_last_error())
        pointer=kernel.GlobalLock(handle)
        if not pointer: raise ctypes.WinError(ctypes.get_last_error())
        try: ctypes.memmove(pointer,data,len(data))
        finally: kernel.GlobalUnlock(handle)
        if not user.EmptyClipboard() or not user.SetClipboardData(13,handle):
            raise ctypes.WinError(ctypes.get_last_error())
        handle=None  # Windows giữ bộ nhớ sau SetClipboardData thành công.
    finally:
        if opened: user.CloseClipboard()
        if handle: kernel.GlobalFree(handle)
        user.DestroyWindow(owner)
