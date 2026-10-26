"""Phiên làm việc riêng: trình duyệt headless hoặc thông điệp tới một cửa sổ Windows.

Không gọi SendInput, SetCursorPos hoặc SetForegroundWindow.
"""
import ctypes
from ctypes import wintypes
import io
import math
import os
from pathlib import Path
import queue
import threading
import time
from urllib.parse import urlsplit

from PIL import Image


def validate_actions(actions):
    if not isinstance(actions, list) or len(actions) > 100000:
        raise ValueError('Danh sách công việc không hợp lệ.')
    for action in actions:
        if not isinstance(action, dict) or action.get('kind') not in ('click', 'text', 'key', 'scroll', 'wait'):
            raise ValueError('File này không phải kịch bản học trong tab Công việc.')
        delay = action.get('delay', 0)
        if not isinstance(delay, (int, float)) or not math.isfinite(delay) or not 0 <= delay <= 3600:
            raise ValueError('Độ trễ công việc không hợp lệ.')
        if action['kind'] in ('click', 'scroll'):
            if not all(isinstance(action.get(k), int) and 0 <= action[k] <= 16000 for k in ('x', 'y')):
                raise ValueError('Tọa độ trong tab không hợp lệ.')
        if action['kind'] == 'click' and action.get('button', 'left') not in ('left', 'right'):
            raise ValueError('Nút chuột không hợp lệ.')
        if action['kind'] == 'scroll' and (not isinstance(action.get('delta'), int) or abs(action['delta']) > 12000):
            raise ValueError('Bước cuộn không hợp lệ.')
        if action['kind'] == 'text' and (not isinstance(action.get('text'), str) or len(action['text']) > 100000):
            raise ValueError('Nội dung nhập không hợp lệ.')
        if action['kind'] == 'key' and action.get('key') not in ('Enter', 'Tab', 'Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End', 'Escape', 'Control+A'):
            raise ValueError('Phím này chưa được hỗ trợ trong tab.')


class BrowserWorkspace:
    def __init__(self, session_folder):
        self.session_folder = str(session_folder)
        self.runtime = self.context = None

    def open(self, target):
        url = str(target)
        if url != 'about:blank' and (urlsplit(url).scheme not in ('http', 'https') or not urlsplit(url).hostname):
            raise ValueError('Nhập địa chỉ http:// hoặc https:// hợp lệ.')
        from playwright.sync_api import sync_playwright
        self.runtime = sync_playwright().start()
        try:
            self.context = self.runtime.chromium.launch_persistent_context(
                self.session_folder, channel='msedge', headless=True,
                viewport={'width': 1280, 'height': 720}, accept_downloads=False)
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            self.size = (1280,720)
            self.page.set_default_timeout(3000)
            self.page.goto(url, wait_until='domcontentloaded', timeout=15000)
        except Exception:
            self.close()
            raise

    def execute(self, action):
        kind = action['kind']
        if kind == 'click':
            self.page.mouse.click(action['x'], action['y'], button=action.get('button', 'left'))
        elif kind == 'scroll':
            self.page.mouse.move(action['x'], action['y'])
            self.page.mouse.wheel(0, action['delta'])
        elif kind == 'text':
            self.page.keyboard.insert_text(action['text'])
        elif kind == 'key':
            self.page.keyboard.press(action['key'])

    def screenshot(self):
        return self.page.screenshot(type='png', timeout=3000)

    def close(self):
        try:
            if self.context:
                self.context.close()
        finally:
            if self.runtime:
                self.runtime.stop()
            self.context = self.runtime = None


def window_list():
    user = ctypes.windll.user32
    result = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    @callback_type
    def visit(hwnd, unused):
        process = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(process))
        length = user.GetWindowTextLengthW(hwnd)
        if user.IsWindowVisible(hwnd) and length and process.value != os.getpid():
            title = ctypes.create_unicode_buffer(length+1)
            user.GetWindowTextW(hwnd, title, len(title))
            result.append({'hwnd': int(hwnd), 'pid': process.value, 'title': title.value})
        return True
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.EnumWindows(visit, 0)
    return result


class WindowsWorkspace:
    """Tương thích các cửa sổ nhận WM_*; không giả lập chuột vật lý cho ứng dụng từ chối."""
    def __init__(self):
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.gdi = ctypes.WinDLL('gdi32', use_last_error=True)
        self.hwnd = self.pid = self.focus = None
        signatures = {
            'IsWindow': ([wintypes.HWND], wintypes.BOOL),
            'IsIconic': ([wintypes.HWND], wintypes.BOOL),
            'IsWindowEnabled': ([wintypes.HWND], wintypes.BOOL),
            'GetWindowThreadProcessId': ([wintypes.HWND, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD),
            'GetClientRect': ([wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            'ClientToScreen': ([wintypes.HWND, ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            'ScreenToClient': ([wintypes.HWND, ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            'ChildWindowFromPointEx': ([wintypes.HWND, wintypes.POINT, wintypes.UINT], wintypes.HWND),
            'GetAncestor': ([wintypes.HWND, wintypes.UINT], wintypes.HWND),
            'GetParent': ([wintypes.HWND], wintypes.HWND),
            'GetDlgCtrlID': ([wintypes.HWND], ctypes.c_int),
            'GetClassNameW': ([wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            'GetNextDlgTabItem': ([wintypes.HWND, wintypes.HWND, wintypes.BOOL], wintypes.HWND),
            'PostMessageW': ([wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM], wintypes.BOOL),
            'SendMessageTimeoutW': ([wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM, wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)], ctypes.c_ssize_t),
            'GetDC': ([wintypes.HWND], wintypes.HDC),
            'ReleaseDC': ([wintypes.HWND, wintypes.HDC], ctypes.c_int),
        }
        for name, (arguments, result) in signatures.items():
            fn = getattr(self.user, name); fn.argtypes = arguments; fn.restype = result
        for name, args, result in (
                ('CreateCompatibleDC', [wintypes.HDC], wintypes.HDC),
                ('CreateCompatibleBitmap', [wintypes.HDC, ctypes.c_int, ctypes.c_int], wintypes.HBITMAP),
                ('SelectObject', [wintypes.HDC, wintypes.HANDLE], wintypes.HANDLE),
                ('DeleteObject', [wintypes.HANDLE], wintypes.BOOL),
                ('DeleteDC', [wintypes.HDC], wintypes.BOOL),
                ('GetDIBits', [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT], ctypes.c_int)):
            fn = getattr(self.gdi, name); fn.argtypes = args; fn.restype = result

    def open(self, target):
        self.hwnd, self.pid = int(target['hwnd']), int(target['pid'])
        self.focus = self.hwnd
        self._check()

    def _check(self):
        process = wintypes.DWORD()
        if not self.user.IsWindow(self.hwnd):
            raise RuntimeError('Cửa sổ đã đóng. Công việc đã dừng.')
        self.user.GetWindowThreadProcessId(self.hwnd, ctypes.byref(process))
        if process.value != self.pid:
            raise RuntimeError('Cửa sổ đích đã đổi. Hãy chọn lại; không gửi sang cửa sổ khác.')
        if self.user.IsIconic(self.hwnd) or not self.user.IsWindowEnabled(self.hwnd):
            raise RuntimeError('Cửa sổ đang thu nhỏ hoặc có hộp thoại chặn. Hãy mở lại cửa sổ đích; có thể để cửa sổ khác che lên.')
        rect = wintypes.RECT()
        if not self.user.GetClientRect(self.hwnd, ctypes.byref(rect)):
            raise RuntimeError('Không đọc được kích thước cửa sổ.')
        self.size = (rect.right, rect.bottom)
        if not all(0 < value <= 4096 for value in self.size):
            raise RuntimeError('Kích thước cửa sổ chưa được hỗ trợ.')

    def _child(self, x, y):
        self._check()
        if not (0 <= x < self.size[0] and 0 <= y < self.size[1]):
            raise RuntimeError('Cửa sổ đã đổi kích thước; tọa độ bước không còn hợp lệ.')
        point = wintypes.POINT(x, y)
        self.user.ClientToScreen(self.hwnd, ctypes.byref(point))
        current = self.hwnd
        for _ in range(32):
            local = wintypes.POINT(point.x, point.y)
            self.user.ScreenToClient(current, ctypes.byref(local))
            child = self.user.ChildWindowFromPointEx(current, local, 7)
            if not child or child == current:
                return current, local
            if self.user.GetAncestor(child, 2) != self.hwnd:
                raise RuntimeError('Không gửi thao tác ra ngoài cửa sổ được chọn.')
            current = child
        raise RuntimeError('Cấu trúc cửa sổ quá sâu.')

    def _send(self, hwnd, message, value=0, position=0):
        if self.user.GetAncestor(hwnd, 2) != self.hwnd:
            raise RuntimeError('Ô nhập đích đã đóng hoặc đổi cửa sổ.')
        if not self.user.PostMessageW(hwnd, message, value, position):
            raise RuntimeError('Phần mềm không nhận thao tác nền (có thể khác quyền chạy). Không chuyển sang chuột thật.')

    def execute(self, action):
        self._check()
        kind = action['kind']
        if kind == 'click':
            hwnd, point = self._child(action['x'], action['y'])
            self.focus = hwnd
            name = ctypes.create_unicode_buffer(128)
            self.user.GetClassNameW(hwnd,name,len(name))
            control = name.value.casefold()
            if action.get('button','left') != 'left':
                raise RuntimeError('Menu chuột phải của Windows cần phiên riêng; chế độ này không kích hoạt desktop.')
            if control == 'edit' or control.startswith('windowsforms10.edit.') or 'richedit' in control:
                # WM_LBUTTONDOWN của Edit có thể lấy tiêu điểm. Chỉ chọn ô nhập lô-gic.
                result = ctypes.c_size_t()
                self.user.SendMessageTimeoutW(hwnd,0xB1,-1,-1,3,500,ctypes.byref(result))
            elif control == 'button' or control.startswith('windowsforms10.button.'):
                # Gửi BN_CLICKED tới cha, không kích hoạt nút bằng chuột vật lý.
                parent = self.user.GetParent(hwnd)
                identifier = self.user.GetDlgCtrlID(hwnd)
                self._send(parent,0x111,identifier & 0xffff,hwnd)
            else:
                raise RuntimeError(f'Điều khiển {name.value or "không rõ"} không hỗ trợ nhập nền an toàn. Dùng chế độ Web hoặc phiên Windows/VM riêng.')
        elif kind == 'text':
            name=ctypes.create_unicode_buffer(128)
            self.user.GetClassNameW(self.focus,name,len(name))
            control=name.value.casefold()
            if control!='edit' and not control.startswith('windowsforms10.edit.') and 'richedit' not in control:
                raise RuntimeError('Chọn một ô nhập chuẩn trong ảnh trước khi gửi chữ. Điều khiển tùy biến cần phiên Windows/VM riêng.')
            raw = action['text'].encode('utf-16-le')
            for index in range(0, len(raw), 2):
                if getattr(self,'cancel_event',None) and self.cancel_event.is_set():
                    raise InterruptedError('Đã dừng nhập. Hãy kiểm tra phần nội dung đã nhập vào cửa sổ.')
                self._send(self.focus, 0x102, int.from_bytes(raw[index:index+2], 'little'))
        elif kind == 'key':
            keys = {'Enter':13, 'Tab':9, 'Backspace':8, 'Delete':46, 'ArrowLeft':37,
                    'ArrowRight':39, 'ArrowUp':38, 'ArrowDown':40, 'Home':36, 'End':35, 'Escape':27}
            key = action['key']
            if key == 'Tab':
                next_control = self.user.GetNextDlgTabItem(self.hwnd,self.focus,False)
                if next_control and self.user.GetAncestor(next_control,2)==self.hwnd:self.focus=next_control
            elif key == 'Control+A':
                # EM_SETSEL chỉ dành cho ô nhập chuẩn; không thay trạng thái Ctrl toàn hệ thống.
                result = ctypes.c_size_t()
                self.user.SendMessageTimeoutW(self.focus, 0xB1, 0, -1, 3, 500, ctypes.byref(result))
            else:
                self._send(self.focus, 0x100, keys[key], 1)
                if key in ('Enter', 'Tab', 'Backspace'):
                    self._send(self.focus, 0x102, keys[key], 1)
                self._send(self.focus, 0x101, keys[key], 0xC0000001)
        elif kind == 'scroll':
            hwnd, point = self._child(action['x'], action['y'])
            self.user.ClientToScreen(hwnd, ctypes.byref(point))
            pos = (point.y & 0xffff) << 16 | (point.x & 0xffff)
            self._send(hwnd, 0x20A, ((-action['delta']) & 0xffff) << 16, pos)

    def screenshot(self):
        self._check()
        width, height = self.size
        dc = self.user.GetDC(self.hwnd)
        memory = self.gdi.CreateCompatibleDC(dc)
        bitmap = self.gdi.CreateCompatibleBitmap(dc, width, height)
        previous = self.gdi.SelectObject(memory, bitmap)
        try:
            result = ctypes.c_size_t()
            if not self.user.SendMessageTimeoutW(self.hwnd, 0x317, memory, 0x1C, 3, 700, ctypes.byref(result)):
                raise RuntimeError('Không đọc được ảnh cửa sổ nền. Phần mềm này có thể cần phiên Windows/VM riêng.')
            self.gdi.SelectObject(memory, previous)
            class Header(ctypes.Structure):
                _fields_ = [('size',wintypes.DWORD),('width',wintypes.LONG),('height',wintypes.LONG),
                    ('planes',wintypes.WORD),('bits',wintypes.WORD),('compression',wintypes.DWORD),
                    ('image',wintypes.DWORD),('x',wintypes.LONG),('y',wintypes.LONG),
                    ('used',wintypes.DWORD),('important',wintypes.DWORD)]
            header = Header(); header.size = ctypes.sizeof(Header)
            header.width, header.height, header.planes, header.bits = width, -height, 1, 32
            buffer = ctypes.create_string_buffer(width*height*4)
            if not self.gdi.GetDIBits(memory, bitmap, 0, height, buffer, ctypes.byref(header), 0):
                raise RuntimeError('Không lấy được ảnh xem trước của phần mềm.')
            image = Image.frombytes('RGB', (width,height), buffer.raw, 'raw', 'BGRX')
            if image.getextrema() == ((0,0),(0,0),(0,0)):
                raise RuntimeError('Phần mềm trả ảnh đen khi chạy nền. Không thể dùng chế độ này với cửa sổ đã chọn.')
            output = io.BytesIO(); image.save(output, format='PNG')
            return output.getvalue()
        finally:
            self.gdi.SelectObject(memory, previous)
            self.gdi.DeleteObject(bitmap); self.gdi.DeleteDC(memory); self.user.ReleaseDC(self.hwnd, dc)

    def close(self):
        self.hwnd = self.focus = None


class WorkspaceEngine:
    def __init__(self, session_folder, emit, factory=None):
        self.folder = Path(session_folder)
        self.emit = emit
        self.factory = factory or self._backend
        self.commands = queue.Queue(maxsize=200)
        self.stop_event = threading.Event()
        self.closed = threading.Event()
        self.ready = self.running = self.recording = False
        self.preview_visible = True
        self.actions = []
        self.mode = None
        self.cursor = (0,0)
        self._frame = None
        self._last_input = self._last_frame = 0
        self._epoch = 0
        self._control_lock = threading.Lock()
        self.backend = None
        self.thread = threading.Thread(target=self._worker, daemon=False, name='HocVet-workspace')
        self.thread.start()

    def _backend(self, mode):
        return BrowserWorkspace(self.folder) if mode == 'web' else WindowsWorkspace()

    def submit(self, command, payload=None):
        if self.closed.is_set():
            return
        self.commands.put_nowait((command,payload,self._epoch))

    def take_frame(self):
        frame, self._frame = self._frame, None
        return frame

    def stop(self):
        with self._control_lock:
            self._epoch += 1
            self.stop_event.set()
        while True:
            try:
                self.commands.put_nowait(('stop',None,self._epoch)); break
            except queue.Full:
                try: self.commands.get_nowait()
                except queue.Empty: pass

    def close(self):
        self.closed.set(); self.stop()

    def _snapshot(self):
        if self.ready and self.preview_visible and time.monotonic()-self._last_frame > .4:
            self._frame = self.backend.screenshot()
            self._last_frame = time.monotonic()

    def _worker(self):
        try:
            while not self.closed.is_set():
                try:
                    command,payload,epoch = self.commands.get(timeout=.15)
                except queue.Empty:
                    command = None; epoch = self._epoch
                try:
                    if command and command != 'stop' and epoch != self._epoch:
                        if command == 'run': self.emit('stopped',(0,len(payload[0])))
                        continue
                    if command == 'stop':
                        if self.recording:
                            self.recording = False
                            self.emit('learned', [dict(action) for action in self.actions])
                        if epoch == self._epoch: self.stop_event.clear()
                    elif command == 'open':
                        self.stop_event.clear()
                        self.ready = self.recording = False
                        if self.backend: self.backend.close()
                        mode,target = payload
                        self.backend = self.factory(mode)
                        self.backend.cancel_event = self.stop_event
                        self.backend.open(target)
                        if self.stop_event.is_set():
                            self.backend.close(); self.emit('stopped',(0,0)); continue
                        self.mode = mode; self.target = target; self.ready = True
                        self.emit('ready', mode)
                    elif command == 'record':
                        if not self.ready: raise RuntimeError('Mở phiên làm việc trước.')
                        if self.stop_event.is_set():
                            self.emit('stopped',(0,0)); continue
                        self.actions = []; self.recording = True; self._last_input = time.monotonic()
                        self.emit('recording', 0)
                    elif command == 'input' and not self.stop_event.is_set():
                        if not self.ready: raise RuntimeError('Phiên chưa sẵn sàng.')
                        validate_actions([payload])
                        self.backend.execute(payload)
                        if 'x' in payload: self.cursor = (payload['x'],payload['y'])
                        if self.recording:
                            action = dict(payload, delay=max(.001,time.monotonic()-self._last_input))
                            self._last_input = time.monotonic(); self.actions.append(action)
                            self.emit('recording', len(self.actions))
                    elif command == 'run':
                        self._run(*payload, cancel_epoch=epoch)
                    self._snapshot()
                except Exception as error:
                    self.recording = self.running = False
                    self.emit('error', str(error))
                    if command == 'open' or command is None:
                        self.ready = False
        finally:
            if self.backend: self.backend.close()

    def _run(self, actions, speed, expected_size=None, cancel_epoch=None):
        if not self.ready: raise RuntimeError('Mở lại phiên và chọn đúng cửa sổ trước khi chạy.')
        validate_actions(actions)
        if not actions: raise ValueError('Học thao tác trong tab trước khi chạy.')
        if not 1 <= speed <= 10: raise ValueError('Tốc độ phải từ 1× đến 10×.')
        if self.mode == 'window':
            self.backend._check()
            if expected_size and tuple(expected_size) != tuple(self.backend.size):
                raise RuntimeError('Giữ nguyên kích thước cửa sổ như khi học, hoặc học lại công việc.')
        with self._control_lock:
            if cancel_epoch is not None and cancel_epoch != self._epoch:
                self.emit('stopped',(0,len(actions))); return
            self.stop_event.clear(); self.recording = False; self.running = True
        last_report = 0
        try:
            for index, action in enumerate(actions, start=1):
                if self.stop_event.wait(action.get('delay',0)/speed):
                    self.emit('stopped', (index-1,len(actions))); return
                if action['kind'] != 'wait': self.backend.execute(action)
                if 'x' in action: self.cursor = (action['x'],action['y'])
                now = time.monotonic()
                if now-last_report >= .1 or index == len(actions):
                    self.emit('progress', (index,len(actions))); last_report = now
                self._snapshot()
            self.emit('done', (len(actions),self.mode))
        finally:
            self.running = False
