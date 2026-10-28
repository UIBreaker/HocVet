"""Cho thao tác phát xuyên bảng; chỉ chuột thật được bấm Dừng trên bảng."""
import ctypes
from ctypes import wintypes
import threading

from pynput import mouse


class OverlayInput:
    _MARKER = 0x48564554
    _PAIRS = {0x201:0x202, 0x204:0x205, 0x207:0x208, 0x20B:0x20C}

    def __init__(self):
        self.active = False
        self.listener = None
        self.hwnd = None
        self._swallowed = set()
        self._drained = threading.Event()
        self.bounds = self.stop_bounds = (0,0,0,0)
        self.on_stop = lambda:None
        self.allow_stop = True
        self.close_bounds=self.drag_bounds=(0,0,0,0)
        self.on_hide=lambda:None
        self.on_drag_start=self.on_drag_move=lambda x,y:None
        self.on_drag_end=lambda:None
        self._dragging=False
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.user.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        self.user.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        self.user.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        self.user.SetLayeredWindowAttributes.argtypes = [wintypes.HWND,wintypes.DWORD,wintypes.BYTE,wintypes.DWORD]
        self.user.SetWindowPos.argtypes = [wintypes.HWND,wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.UINT]
        self.user.IsWindow.argtypes = [wintypes.HWND]
        self.user.mouse_event.argtypes = [wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,ctypes.c_size_t]

    @staticmethod
    def contains(bounds, x, y):
        left,top,right,bottom = bounds
        return left <= x < right and top <= y < bottom

    def _filter(self, message, data):
        if data.flags & 1:
            if data.dwExtraInfo == self._MARKER:
                self._drained.set()
                self.listener.suppress_event()
            return True
        if message==0x202 and self._dragging:self._dragging=False;self.on_drag_end()
        if self.active and self._dragging and message==0x200:
            self.on_drag_move(data.pt.x,data.pt.y)
            return True
        if message in self._swallowed:
            self._swallowed.discard(message)
            self.listener.suppress_event()
        if not self.active: return True
        x,y = data.pt.x,data.pt.y
        if not self.contains(self.bounds,x,y): return True
        if message in self._PAIRS:
            self._swallowed.add(self._PAIRS[message])
            if message==0x201:
                if self.contains(self.close_bounds,x,y):self.on_hide()
                elif self.contains(self.drag_bounds,x,y):self._dragging=True;self.on_drag_start(x,y)
                elif self.allow_stop and self.contains(self.stop_bounds,x,y):self.on_stop()
            self.listener.suppress_event()
        if message in (0x202,0x205,0x208,0x20C,0x20A,0x20E):
            self.listener.suppress_event()
        return True

    def activate(self, hwnd, bounds, stop_bounds, on_stop, allow_stop):
        if not self.listener:
            self.listener = mouse.Listener(win32_event_filter=self._filter)
            self.listener.start()
            self.listener.wait()
        if self.active: return
        self.hwnd = hwnd
        self.bounds,self.stop_bounds = bounds,stop_bounds
        self.on_stop,self.allow_stop = on_stop,allow_stop
        self._style = self.user.GetWindowLongPtrW(hwnd,-20)
        self.active = True
        try:
            ctypes.set_last_error(0)
            self.user.SetWindowLongPtrW(hwnd,-20,self._style | 0x80000 | 0x20)
            if ctypes.get_last_error(): raise ctypes.WinError(ctypes.get_last_error())
            if not self.user.SetLayeredWindowAttributes(hwnd,0,255,2): raise ctypes.WinError(ctypes.get_last_error())
            if not self.user.SetWindowPos(hwnd,None,0,0,0,0,0x37): raise ctypes.WinError(ctypes.get_last_error())
        except Exception:
            self.deactivate()
            raise

    def drain(self):
        if self.active:
            # Marker đi sau mọi thao tác phát, trước khi bật lại nút trên bảng.
            self._drained.clear()
            self.user.mouse_event(0x800,0,0,1,self._MARKER)
            if not self._drained.wait(2):
                raise RuntimeError('Chưa xác nhận xong hàng đợi chuột của Windows.')

    def deactivate(self):
        if self.hwnd and self.user.IsWindow(self.hwnd) and self.active:
            self.user.SetWindowLongPtrW(self.hwnd,-20,self._style)
            self.user.SetWindowPos(self.hwnd,None,0,0,0,0,0x37)
        self.active = False
        if self._dragging:self.on_drag_end()
        self._dragging=False

    def close(self):
        self.deactivate()
        if self.listener:
            self.listener.stop()
            self.listener.join(timeout=.5)
            if not self.listener.is_alive(): self.listener = None
