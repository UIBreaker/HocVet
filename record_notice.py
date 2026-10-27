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
        self.on_repeat = self.on_resize = None
        self.size = None
        self.per_page = 3
        self._layout_timer = None
        self._row_height = self._chrome_height = None
        self._resizing = False
        self.environment_enabled = False
        self.on_environment = None

    def pin(self, profiles, on_run, on_stop, on_open, activation='mouse', *, on_repeat=None, size=None, on_resize=None):
        self.pinned = True
        self.activation = activation
        self.profiles = list(profiles)
        self.on_run, self.on_stop, self.on_open = on_run, on_stop, on_open
        self.on_repeat,self.on_resize = on_repeat,on_resize
        if size is not None: self.size = tuple(size)
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

    def set_environment_enabled(self, enabled):
        if self.environment_enabled != enabled:
            self.environment_enabled=enabled
            if self.pinned and self.launcher:self._render_profiles()

    def _render_profiles(self):
        for child in self.launcher.winfo_children(): child.destroy()
        per_page = self.per_page
        pages = max(1, (len(self.profiles)+per_page-1)//per_page)
        self.page = min(self.page, pages-1)
        ttk.Separator(self.launcher).pack(fill='x', pady=(8, 6))
        ttk.Label(self.launcher, text='KỊCH BẢN · DÙNG CHUỘT' if self.activation=='mouse' else 'KỊCH BẢN · CHỈ DÙNG PHÍM',
            font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.run_buttons = []
        self.repeat_buttons = []
        self.slots = []
        self.name_labels = []
        rows = tk.Frame(self.launcher,bg=VINTAGE_BG)
        rows.pack(fill='both',expand=True)
        for index in range(per_page):
            slot = tk.Frame(rows, bg=VINTAGE_CARD_BG, padx=10, pady=6)
            slot.pack(fill='both',expand=True,pady=(5,0))
            slot.bind('<Configure>',self._queue_layout)
            self.slots.append(slot)
            slot.columnconfigure(0,weight=1)
            offset = self.page*per_page+index
            profile = self.profiles[offset] if offset < len(self.profiles) else None
            label = profile.name if profile else '—'
            name = tk.Label(slot, text=label, anchor='w', justify='left', wraplength=235,
                height=2, font=('Segoe UI', 10, 'bold'), bg=VINTAGE_CARD_BG, fg=VINTAGE_TEXT_HEAD)
            name.grid(row=0,column=0,sticky='ew')
            self.name_labels.append(name)
            meta = f'{len(profile.actions):,} bước · {"Dùng chuột" if self.activation=="mouse" else profile.hotkey or "Chưa gán phím"}' if profile else ' '
            tk.Label(slot, text=meta, anchor='w', font=FONT_BODY, bg=VINTAGE_CARD_BG, fg=VINTAGE_TEXT_BODY).grid(row=1,column=0,sticky='w')
            button = ttk.Button(slot, text='▶ Chạy', style='Primary.TButton', takefocus=False,
                command=lambda p=profile: self.on_run(p.id) if p else None)
            button.grid(row=0,column=1,rowspan=2,padx=(8,0))
            button.configure(state='disabled' if self.activation!='mouse' or self.busy or not profile or not profile.actions or not profile.enabled else 'normal')
            self.run_buttons.append(button)
            repeats = tk.Frame(slot,bg=VINTAGE_CARD_BG)
            repeats.grid(row=2,column=0,columnspan=2,sticky='w',pady=(5,0))
            tk.Label(repeats,text='Lặp',font=FONT_BODY,bg=VINTAGE_CARD_BG,fg=VINTAGE_TEXT_BODY).pack(side='left',padx=(0,8))
            count = profile.loop_count if profile else 1
            for caption, value in (('−',max(0,count-1)), ('Liên tục' if count==0 else f'{count} lần',None), ('+',count+1)):
                edit = ttk.Button(repeats,text=caption,width=9 if value is None else 3,takefocus=False,
                    command=lambda p=profile,v=value:self.on_repeat(p.id,v) if p and self.on_repeat else None)
                edit.pack(side='left',padx=(0,4))
                edit.configure(state='disabled' if self.busy or not profile or not self.on_repeat else 'normal')
                self.repeat_buttons.append(edit)
        navigation = ttk.Frame(self.launcher)
        navigation.pack(fill='x', pady=6)
        ttk.Button(navigation, text='‹ Trước', width=6, takefocus=False, command=lambda:self._page(-1),
            state='normal' if self.page and not self.busy else 'disabled').pack(side='left')
        ttk.Label(navigation, text=f'{self.page+1}/{pages} · {len(self.profiles)} kịch bản').pack(side='left', expand=True)
        ttk.Button(navigation, text='Sau ›', width=6, takefocus=False, command=lambda:self._page(1),
            state='normal' if self.page+1 < pages and not self.busy else 'disabled').pack(side='right')
        footer = ttk.Frame(self.launcher)
        footer.pack(fill='x')
        ttk.Button(footer, text='Môi trường' if self.environment_enabled else 'Mở ứng dụng', takefocus=False,
            command=lambda:self.on_environment() if self.environment_enabled and self.on_environment else self.on_open(),
            state='normal' if self.environment_enabled or not self.busy else 'disabled').pack(side='left')
        self.stop_button = ttk.Button(footer, text='■ Dừng', style='Danger.TButton', takefocus=False,
            command=lambda:self.on_stop() if self.activation=='mouse' else None,
            state='normal' if self.busy and self.activation=='mouse' else 'disabled')
        self.stop_button.pack(side='right')
        if self.size and self._layout_timer is None:
            self._layout_timer = self.root.after_idle(self._fit_layout)

    def _page(self, delta):
        if self.busy: return
        self.page = max(0, self.page+delta)
        self._render_profiles()

    def _queue_layout(self, event):
        if (event.widget is self.window or event.widget in getattr(self,'slots',[])) and self.pinned and self._layout_timer is None:
            self._layout_timer = self.root.after_idle(self._fit_layout)

    def _fit_layout(self):
        if self._layout_timer:
            self.root.after_cancel(self._layout_timer)
        self._layout_timer = None
        if not self.window or not self.pinned or not self.launcher or not self.window.winfo_ismapped(): return
        if self._row_height is None:
            self._row_height = max(slot.winfo_reqheight()+5 for slot in self.slots)
            self._chrome_height = self.window.winfo_reqheight()-self.per_page*self._row_height
        count = max(1,(self.window.winfo_height()-self._chrome_height)//self._row_height)
        if count != self.per_page and not self.busy:
            first = self.page*self.per_page
            self.per_page = count
            self.page = first//count
            self._render_profiles()
            return
        if self.size:
            self.title.configure(wraplength=max(100,self.window.winfo_width()-40))
            self.message.configure(wraplength=max(100,self.window.winfo_width()-40))
            for slot,label,button in zip(self.slots,self.name_labels,self.run_buttons):
                label.configure(wraplength=max(80,slot.winfo_width()-button.winfo_reqwidth()-32))

    def resize(self, width, height, save=True):
        if self.busy or not self.pinned or not self.window: return
        self.window.update_idletasks()
        if self._row_height is None: self._fit_layout()
        work = self._work_area()
        scale = self.root.winfo_fpixels('1i')/96
        width = min(work.right-work.left,max(round(320*scale),int(width)))
        height = min(work.bottom-work.top,max(self._chrome_height+self._row_height,int(height)))
        x,y = self.position or (self.window.winfo_x(),self.window.winfo_y())
        x,y = max(work.left,min(work.right-width,x)),max(work.top,min(work.bottom-height,y))
        self.size,self.position = (width,height),(x,y)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
        if save and self.on_resize: self.on_resize(width,height)

    def _resize_start(self, event, edge):
        if self.busy or not self.pinned: return
        win=self.window
        self._resizing=True
        self._resize_origin=(edge,event.x_root,event.y_root,win.winfo_x(),win.winfo_y(),win.winfo_width(),win.winfo_height())

    def _resize_move(self, event):
        if self.busy or not self._resizing: return
        edge,px,py,x,y,w,h=self._resize_origin
        dx,dy=event.x_root-px,event.y_root-py
        self.resize(w+(dx if 'e' in edge else -dx if 'w' in edge else 0),
                    h+(dy if 's' in edge else -dy if 'n' in edge else 0),save=False)
        nw,nh=self.size
        work=self._work_area()
        self.position=(max(work.left,min(work.right-nw,x+w-nw if 'w' in edge else x)),
                       max(work.top,min(work.bottom-nh,y+h-nh if 'n' in edge else y)))
        self.window.geometry(f'+{self.position[0]}+{self.position[1]}')

    def _resize_end(self, event):
        if not self._resizing: return
        self._resizing=False
        if self.on_resize and self.size: self.on_resize(*self.size)

    def _add_resize_handles(self):
        for edge, options in (
                ('n',dict(relx=0,rely=0,relwidth=1,height=6)),('s',dict(relx=0,rely=1,anchor='sw',relwidth=1,height=6)),
                ('w',dict(relx=0,rely=0,relheight=1,width=6)),('e',dict(relx=1,rely=0,anchor='ne',relheight=1,width=6)),
                ('nw',dict(relx=0,rely=0)),('ne',dict(relx=1,rely=0,anchor='ne')),
                ('sw',dict(relx=0,rely=1,anchor='sw')),('se',dict(relx=1,rely=1,anchor='se'))):
            cursor='size_nw_se' if edge in ('nw','se') else 'size_ne_sw' if len(edge)==2 else 'sb_h_double_arrow' if edge in ('w','e') else 'sb_v_double_arrow'
            grip=tk.Frame(self.window,bg='#b9b0a1',cursor=cursor,width=9,height=9)
            grip.place(**options)
            grip.bind('<Button-1>',lambda event,e=edge:self._resize_start(event,e))
            grip.bind('<B1-Motion>',self._resize_move)
            grip.bind('<ButtonRelease-1>',self._resize_end)

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
            win.bind('<Configure>',self._queue_layout)
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
            self.launcher.pack(fill='both',expand=True)
            self._render_profiles()
            self._add_resize_handles()
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
        if self.size and self.pinned:
            scale=self.root.winfo_fpixels('1i')/96
            width=min(work.right-work.left,max(round(320*scale),self.size[0]))
            minimum=(self._chrome_height+self._row_height) if self._row_height is not None else 340
            height=min(work.bottom-work.top,max(minimum,self.size[1]))
        x, y = max(work.left, work.right-width-24), max(work.top, work.bottom-height-24)
        if self.position and self.pinned:
            x = max(work.left,min(work.right-width,self.position[0]))
            y = max(work.top,min(work.bottom-height,self.position[1]))
        win.geometry(f'{width}x{height}+{x}+{y}')
        win.deiconify()
        user32.SetWindowPos(ctypes.c_void_p(hwnd), ctypes.c_void_p(-1), x, y, width, height, 0x0050)
        if self.pinned and not self.busy:
            win.update_idletasks()
            self._fit_layout()
        if duration and not self.pinned:
            self.timer = self.root.after(duration, self.close)

    def close(self, force=False):
        if self.timer:
            self.root.after_cancel(self.timer)
            self.timer = None
        if self.pinned and not force: return
        if self._layout_timer:
            self.root.after_cancel(self._layout_timer)
            self._layout_timer = None
        if self.window and self.window.winfo_exists():
            self.window.destroy()
        self.window = None
        self.launcher = None
        self._row_height = self._chrome_height = None
        if force: self.pinned = False
