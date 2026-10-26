"""Thông báo nổi không lấy tiêu điểm, hoạt động khi cửa sổ chính đang ẩn."""
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk

from ui_theme import VINTAGE_BG, VINTAGE_TEXT_HEAD, VINTAGE_TEXT_BODY, VINTAGE_CARD_BG, BTN_RED_TOP, FONT_BODY


class RecordNotice:
    def __init__(self, root):
        self.root = root
        self.window = None
        self.timer = None
        self.pinned = False
        self.position = None
        self.page = 0
        self.busy = False
        self.profiles = []
        self.launcher = None
        self.on_run = self.on_stop = self.on_open = None

    def pin(self, profiles, on_run, on_stop, on_open, activation='mouse'):
        self.pinned = True
        self.activation = activation
        self.profiles = list(profiles)
        self.on_run, self.on_stop, self.on_open = on_run, on_stop, on_open
        self.show('HỌC VẸT · BẢNG ĐIỀU KHIỂN', 'Chọn kịch bản bên dưới để chạy.' if activation=='mouse'
            else 'Dùng phím đã gán để Học / Chạy / Dừng. Các nút kích hoạt bằng chuột đang khóa.', progress=0)

    def update_profiles(self, profiles):
        self.profiles = list(profiles)
        if self.pinned and self.launcher:
            self._render_profiles()

    def set_busy(self, busy):
        if self.busy != busy:
            self.busy = busy
            if self.pinned and self.launcher: self._render_profiles()

    def _render_profiles(self):
        for child in self.launcher.winfo_children(): child.destroy()
        per_page = 3
        pages = max(1, (len(self.profiles)+per_page-1)//per_page)
        self.page = min(self.page, pages-1)
        ttk.Separator(self.launcher).pack(fill='x', pady=(8, 6))
        ttk.Label(self.launcher, text='KỊCH BẢN · DÙNG CHUỘT' if self.activation=='mouse' else 'KỊCH BẢN · CHỈ DÙNG PHÍM',
            font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.run_buttons = []
        for index in range(per_page):
            slot = tk.Frame(self.launcher, bg=VINTAGE_CARD_BG, padx=10, pady=6)
            slot.pack(fill='x', pady=(5, 0))
            offset = self.page*per_page+index
            profile = self.profiles[offset] if offset < len(self.profiles) else None
            text = tk.Frame(slot, bg=VINTAGE_CARD_BG)
            text.pack(side='left', fill='x', expand=True)
            label = profile.name if profile else '—'
            tk.Label(text, text=label, anchor='w', justify='left', wraplength=235,
                height=2, font=('Segoe UI', 10, 'bold'), bg=VINTAGE_CARD_BG, fg=VINTAGE_TEXT_HEAD).pack(fill='x')
            meta = f'{len(profile.actions):,} bước · {"Dùng chuột" if self.activation=="mouse" else profile.hotkey or "Chưa gán phím"}' if profile else ' '
            tk.Label(text, text=meta, anchor='w', font=FONT_BODY, bg=VINTAGE_CARD_BG, fg=VINTAGE_TEXT_BODY).pack(fill='x')
            button = ttk.Button(slot, text='▶ Chạy', style='Primary.TButton', takefocus=False,
                command=lambda p=profile: self.on_run(p.id) if p else None)
            button.pack(side='right', padx=(8, 0))
            button.configure(state='disabled' if self.activation!='mouse' or self.busy or not profile or not profile.actions or not profile.enabled else 'normal')
            self.run_buttons.append(button)
        navigation = ttk.Frame(self.launcher)
        navigation.pack(fill='x', pady=6)
        ttk.Button(navigation, text='‹ Trước', takefocus=False, command=lambda:self._page(-1),
            state='normal' if self.page and not self.busy else 'disabled').pack(side='left')
        ttk.Label(navigation, text=f'{self.page+1}/{pages} · {len(self.profiles)} kịch bản').pack(side='left', expand=True)
        ttk.Button(navigation, text='Sau ›', takefocus=False, command=lambda:self._page(1),
            state='normal' if self.page+1 < pages and not self.busy else 'disabled').pack(side='right')
        footer = ttk.Frame(self.launcher)
        footer.pack(fill='x')
        ttk.Button(footer, text='Mở ứng dụng', takefocus=False, command=lambda:self.on_open(),
            state='disabled' if self.busy else 'normal').pack(side='left')
        self.stop_button = ttk.Button(footer, text='■ Dừng', style='Danger.TButton', takefocus=False,
            command=lambda:self.on_stop() if self.activation=='mouse' else None,
            state='normal' if self.busy and self.activation=='mouse' else 'disabled')
        self.stop_button.pack(side='right')

    def _page(self, delta):
        if self.busy: return
        self.page = max(0, self.page+delta)
        self._render_profiles()

    def _drag_start(self, event):
        if not self.busy: self._drag = (event.x_root-self.window.winfo_x(), event.y_root-self.window.winfo_y())

    def _drag_move(self, event):
        if self.busy or not hasattr(self, '_drag'): return
        work = self._work_area()
        x = max(work.left, min(work.right-self.window.winfo_width(), event.x_root-self._drag[0]))
        y = max(work.top, min(work.bottom-self.window.winfo_height(), event.y_root-self._drag[1]))
        self.position = (x,y)
        self.window.geometry(f'+{x}+{y}')

    @staticmethod
    def _work_area():
        work = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(work), 0)
        return work

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
            win.bind('<MouseWheel>', lambda event: self._page(-1 if event.delta > 0 else 1) if self.pinned else None)
            panel = tk.Frame(win, bg=VINTAGE_BG, padx=18, pady=14)
            panel.pack(fill='both', expand=True)
            self.panel = panel
            self.number = tk.Label(panel, bg=VINTAGE_BG, fg=BTN_RED_TOP,
                                   font=('Bahnschrift', 28, 'bold'), width=2)
            self.number.pack(side='left', padx=(0, 12))
            content = tk.Frame(panel, bg=VINTAGE_BG)
            self.content = content
            content.pack(side='left', fill='both', expand=True)
            self.title = tk.Label(content, bg=VINTAGE_BG, fg=VINTAGE_TEXT_HEAD,
                                  font=('Segoe UI', 11, 'bold'), anchor='w', wraplength=290, justify='left')
            self.title.pack(fill='x')
            self.title.bind('<Button-1>', self._drag_start)
            self.title.bind('<B1-Motion>', self._drag_move)
            self.message = tk.Label(content, bg=VINTAGE_BG, fg=VINTAGE_TEXT_BODY,
                                    font=FONT_BODY, wraplength=290, justify='left', anchor='w')
            self.message.pack(fill='x', pady=(4, 0))
            self.progress = ttk.Progressbar(content, maximum=100, length=280)
        self.title.configure(text=title)
        self.message.configure(text=message)
        self.number.configure(text=str(number) if number is not None else '●')
        if self.pinned and self.launcher is None:
            self.number.pack_forget()
            self.content.pack_forget()
            self.content.pack(fill='x')
            self.title.configure(height=2)
            self.message.configure(height=2)
            self.launcher = tk.Frame(self.panel, bg=VINTAGE_BG)
            self.launcher.pack(fill='x')
            self._render_profiles()
        if progress is None and not self.pinned:
            self.progress.pack_forget()
        else:
            self.progress.configure(value=max(0, min(100, progress or 0)))
            self.progress.pack(fill='x', pady=(8, 0))
        win = self.window
        win.update_idletasks()
        user32 = ctypes.windll.user32
        user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetAncestor.restype = wintypes.HWND
        hwnd = user32.GetAncestor(win.winfo_id(), 2)
        self.hwnd = hwnd
        # Không làm mất con trỏ đang nhập trong phần mềm đích.
        get_style = user32.GetWindowLongPtrW
        set_style = user32.SetWindowLongPtrW
        get_style.argtypes = [wintypes.HWND, ctypes.c_int]
        get_style.restype = ctypes.c_ssize_t
        set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        set_style(hwnd, -20, get_style(hwnd, -20) | 0x08000000 | 0x80)
        work = self._work_area()
        width, height = win.winfo_reqwidth(), win.winfo_reqheight()
        x, y = max(work.left, work.right-width-24), max(work.top, work.bottom-height-24)
        if self.position and self.pinned:
            x = max(work.left,min(work.right-width,self.position[0]))
            y = max(work.top,min(work.bottom-height,self.position[1]))
        win.geometry(f'{width}x{height}+{x}+{y}')
        win.deiconify()
        user32.SetWindowPos(ctypes.c_void_p(hwnd), ctypes.c_void_p(-1), x, y, width, height, 0x0050)
        if duration and not self.pinned:
            self.timer = self.root.after(duration, self.close)

    def close(self, force=False):
        if self.timer:
            self.root.after_cancel(self.timer)
            self.timer = None
        if self.pinned and not force: return
        if self.window and self.window.winfo_exists():
            self.window.destroy()
        self.window = None
        self.launcher = None
        if force: self.pinned = False
