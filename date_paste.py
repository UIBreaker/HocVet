"""Dán ngày vào ba ô HIS liên tiếp theo thứ tự ngày, tháng, năm."""
import ctypes
import datetime
import re
import threading
import time

from pynput import keyboard
from clipboard_text import set_clipboard_text,get_clipboard_text


def date_parts(value):
    match=re.fullmatch(r'\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*',value)
    if not match:raise ValueError('Ngày phải có dạng dd/mm/yyyy, ví dụ 19/08/1987.')
    day,month,year=map(int,match.groups())
    try:datetime.date(year,month,day)
    except ValueError:raise ValueError(f'Ngày không hợp lệ: {value.strip()}.') from None
    return f'{day:02}',f'{month:02}',f'{year:04}'


def paste_date(value,controller,cancel,protect=None,target=None):
    parts=date_parts(value)
    user=ctypes.windll.user32
    if target is None:target=user.GetForegroundWindow()
    def check():
        if cancel.is_set():raise InterruptedError('Đã dừng dán ngày.')
        if user.GetForegroundWindow()!=target or protect and protect():
            raise RuntimeError('Cửa sổ nhận dữ liệu đã thay đổi. Hãy chọn lại ô ngày rồi thử lại.')
    def chord(char):
        controller.press(keyboard.Key.ctrl_l)
        try:
            key=keyboard.KeyCode.from_vk(ord(char.upper()))
            controller.press(key);controller.release(key)
        finally:controller.release(keyboard.Key.ctrl_l)
    try:
        # Ở 10×, cú bấm ô ngày có thể còn trong hàng đợi của cửa sổ đích.
        check()
        cancel.wait(.12)
        check()
        for index,part in enumerate(parts):
            check();set_clipboard_text(part,cancel);chord('a');chord('v')
            if cancel.wait(.12):check()
            check()
            if index<2:
                controller.press(keyboard.Key.tab);controller.release(keyboard.Key.tab)
                if cancel.wait(.08):check()
    finally:
        # Giữ nguyên ngày đầy đủ để có thể sao chép sang nơi khác sau thao tác.
        set_clipboard_text(value)


class DatePaste:
    """Chỉ chặn một Ctrl+V sau khi người dùng sao chép cột Ngày → 3 ô HIS."""
    def __init__(self,protect,on_error):
        self.protect=protect;self.on_error=on_error
        self.pending=None;self.listener=None;self.swallow_v=False;self.busy=False
        self.record_skip_release=False
        self.cancel=threading.Event()

    def arm(self,value,on_paste):
        date_parts(value)
        if self.busy:raise ValueError('Đang dán ngày, hãy chờ thao tác hoàn tất.')
        if not self.listener or not self.listener.is_alive():
            self.listener=keyboard.Listener(win32_event_filter=self._filter)
            self.listener.start();self.listener.wait()
        self.cancel.clear();self.pending=(value,on_paste,time.monotonic()+60)
        self.clipboard_sequence=ctypes.windll.user32.GetClipboardSequenceNumber()

    def clear(self):
        self.pending=None

    def _ctrl(self):
        return bool(ctypes.windll.user32.GetAsyncKeyState(0x11)&0x8000)

    def _ready(self):
        if not self.pending:return False
        if time.monotonic()>self.pending[2]:
            self.clear();return False
        sequence=ctypes.windll.user32.GetClipboardSequenceNumber()
        if sequence!=self.clipboard_sequence:
            # Clipboard manager có thể ghi lại cùng nội dung / thêm định dạng.
            text=get_clipboard_text()
            if text is not None and text!=self.pending[0]:
                self.clear();return False
            if text is not None:self.clipboard_sequence=sequence
        return True

    def ignore_recording(self,msg,data):
        if data.vkCode!=86:return False
        if msg in (0x101,0x105) and self.record_skip_release:
            self.record_skip_release=False;return True
        pending=self._ready()
        ignore=self.swallow_v or pending and self._ctrl() and not self.protect()
        if ignore:self.record_skip_release=True
        elif msg in (0x100,0x104):self.record_skip_release=False
        return bool(ignore)

    def _filter(self,msg,data):
        # Chỉ bỏ phím do chính lượt dán đang chạy tạo ra; Ctrl+V từ bộ gõ
        # hoặc công cụ bàn phím khác vẫn phải kích hoạt lượt dán đã chuẩn bị.
        if data.flags&0x12 and self.busy:return True
        if data.vkCode==86 and self.swallow_v:
            if msg in (0x101,0x105):self.swallow_v=False
            self.listener.suppress_event()
        if data.vkCode==86 and msg==0x100 and self._ready() and self._ctrl() and not self.protect():
            value,on_paste,_=self.pending
            self.pending=None;self.swallow_v=True;self.busy=True
            self.record_skip_release=True
            target=ctypes.windll.user32.GetForegroundWindow()
            on_paste()
            threading.Thread(target=self._paste,args=(value,target),daemon=True).start()
            self.listener.suppress_event()
        return True

    def _paste(self,value,target=None):
        try:
            # Chờ nhả Ctrl thật để Tab không trở thành Ctrl+Tab trong trình duyệt.
            deadline=time.monotonic()+5
            while self._ctrl():
                if self.cancel.wait(.01):return
                if time.monotonic()>deadline:raise RuntimeError('Hãy nhả Ctrl sau khi bấm Ctrl+V rồi sao chép lại ngày.')
            self.swallow_v=False
            paste_date(value,keyboard.Controller(),self.cancel,self.protect,target)
        except Exception as error:self.on_error(str(error))
        finally:self.swallow_v=False;self.busy=False

    def close(self):
        self.clear();self.cancel.set()
        if self.listener:self.listener.stop();self.listener=None
