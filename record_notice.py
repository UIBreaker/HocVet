"""Thông báo nổi không lấy tiêu điểm, hoạt động khi cửa sổ chính đang ẩn."""
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk

from ui_theme import VINTAGE_BG, VINTAGE_TEXT_HEAD, VINTAGE_TEXT_BODY, BTN_RED_TOP, FONT_BODY


class RecordNotice:
    def __init__(self, root):
        self.root = root
        self.window = None
        self.timer = None

    def show(self, title, message, number=None, duration=None, progress=None):
        if self.timer:
            self.root.after_cancel(self.timer)
            self.timer = None
        if self.window is None or not self.window.winfo_exists():
            win = self.window = tk.Toplevel(self.root)
            win.withdraw()
            win.overrideredirect(True)
            win.attributes('-topmost', True)
            win.configure(bg='#b9b0a1', padx=2, pady=2)
            panel = tk.Frame(win, bg=VINTAGE_BG, padx=18, pady=14)
            panel.pack(fill='both', expand=True)
            self.number = tk.Label(panel, bg=VINTAGE_BG, fg=BTN_RED_TOP,
                                   font=('Bahnschrift', 28, 'bold'), width=2)
            self.number.pack(side='left', padx=(0, 12))
            content = tk.Frame(panel, bg=VINTAGE_BG)
            content.pack(side='left', fill='both', expand=True)
            self.title = tk.Label(content, bg=VINTAGE_BG, fg=VINTAGE_TEXT_HEAD,
                                  font=('Segoe UI', 11, 'bold'), anchor='w', wraplength=290, justify='left')
            self.title.pack(fill='x')
            self.message = tk.Label(content, bg=VINTAGE_BG, fg=VINTAGE_TEXT_BODY,
                                    font=FONT_BODY, wraplength=290, justify='left', anchor='w')
            self.message.pack(fill='x', pady=(4, 0))
            self.progress = ttk.Progressbar(content, maximum=100, length=280)
        self.title.configure(text=title)
        self.message.configure(text=message)
        self.number.configure(text=str(number) if number is not None else '●')
        if progress is None:
            self.progress.pack_forget()
        else:
            self.progress.configure(value=max(0, min(100, progress)))
            self.progress.pack(fill='x', pady=(8, 0))
        win = self.window
        win.update_idletasks()
        user32 = ctypes.windll.user32
        user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetAncestor.restype = wintypes.HWND
        hwnd = user32.GetAncestor(win.winfo_id(), 2)
        # Không làm mất con trỏ đang nhập trong phần mềm đích.
        get_style = user32.GetWindowLongPtrW
        set_style = user32.SetWindowLongPtrW
        get_style.argtypes = [wintypes.HWND, ctypes.c_int]
        get_style.restype = ctypes.c_ssize_t
        set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        set_style(hwnd, -20, get_style(hwnd, -20) | 0x08000000 | 0x80)
        work = wintypes.RECT()
        user32.SystemParametersInfoW(48, 0, ctypes.byref(work), 0)
        width, height = win.winfo_reqwidth(), win.winfo_reqheight()
        x, y = max(work.left, work.right-width-24), max(work.top, work.bottom-height-24)
        win.geometry(f'{width}x{height}+{x}+{y}')
        win.deiconify()
        user32.SetWindowPos(ctypes.c_void_p(hwnd), ctypes.c_void_p(-1), x, y, width, height, 0x0050)
        if duration:
            self.timer = self.root.after(duration, self.close)

    def close(self):
        if self.timer:
            self.root.after_cancel(self.timer)
            self.timer = None
        if self.window and self.window.winfo_exists():
            self.window.destroy()
        self.window = None
