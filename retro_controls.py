"""Thanh trượt đỏ dạng rãnh nổi theo bảng điều khiển mẫu."""
import tkinter as tk
from ui_theme import VINTAGE_CARD_BG, VINTAGE_TEXT_MUTED, BTN_RED_TOP, BTN_RED_BOT


class RetroSlider(tk.Canvas):
    animations_enabled = True

    def __init__(self, parent, values, command, on_preview=None):
        height = round(50 + 8*parent.winfo_fpixels('1i')/96)
        super().__init__(parent, height=height, bg=VINTAGE_CARD_BG, highlightthickness=0,
                         takefocus=True, cursor='hand2')
        self.values = list(values)
        self.index = self.values.index(1.0) if 1.0 in self.values else 0
        self.position = float(self.index)
        self.command = command
        self.on_preview = on_preview
        self._anim_timer = None
        self.bind('<Configure>', lambda event: self._draw())
        self.bind('<Button-1>', self._drag)
        self.bind('<B1-Motion>', self._drag)
        self.bind('<ButtonRelease-1>', lambda event: self.command(self.values[self.index]))
        self.bind('<Left>', lambda event: self._step(-1))
        self.bind('<Right>', lambda event: self._step(1))
        self.bind('<FocusIn>', lambda event: self._draw())
        self.bind('<FocusOut>', lambda event: self._draw())
        self.bind('<Destroy>', lambda event: self._cancel_anim(), add='+')

    def _cancel_anim(self):
        if self._anim_timer:
            try:
                self.after_cancel(self._anim_timer)
            except Exception:
                pass
            self._anim_timer = None

    def _animate_to(self, target_pos):
        self._cancel_anim()
        start_pos = self.position
        diff = target_pos - start_pos
        steps = 4
        def glide(step=1):
            if not self.winfo_exists():
                return
            if step <= steps:
                t = step / steps
                ease = 1 - (1 - t) * (1 - t)
                self.position = start_pos + diff * ease
                self._draw()
                self._anim_timer = self.after(16, glide, step + 1)
            else:
                self.position = target_pos
                self._draw()
                self._anim_timer = None
        glide(1)

    def set(self, value, animate=False):
        self.index = min(range(len(self.values)), key=lambda i: abs(self.values[i]-value))
        target_pos = float(self.index)
        for index, (left, right) in enumerate(zip(self.values, self.values[1:])):
            if left <= value <= right and left != right:
                target_pos = index + (value-left)/(right-left)
                break
        if animate and self.animations_enabled and abs(self.position - target_pos) > 0.05:
            self._animate_to(target_pos)
        else:
            self._cancel_anim()
            self.position = target_pos
            self._draw()

    def _step(self, offset):
        self.index = max(0, min(len(self.values)-1, self.index+offset))
        target_pos = float(self.index)
        if self.animations_enabled:
            self._animate_to(target_pos)
        else:
            self._cancel_anim()
            self.position = target_pos
            self._draw()
        self.command(self.values[self.index])
        return 'break'

    def _drag(self, event):
        self._cancel_anim()
        self.focus_set()
        position = (event.x-24) / max(1, self.winfo_width()-48)
        self.index = max(0, min(len(self.values)-1, round(position*(len(self.values)-1))))
        self.position = float(self.index)
        self._draw()
        if self.on_preview:
            self.on_preview(self.values[self.index])

    def _draw(self):
        self.delete('all')
        right = max(50, self.winfo_width()-24)
        self.create_line(24, 20, right, 20, width=12, fill='#c3bbac', capstyle='round')
        self.create_line(24, 19, right, 19, width=8, fill='#fffdf7', capstyle='round')
        self.create_line(24, 17, right, 17, width=1, fill='#9e978a')
        for index, value in enumerate(self.values):
            tick_x = 24 + (right-24)*index/max(1, len(self.values)-1)
            selected = index == self.position
            self.create_line(tick_x, 31, tick_x, 35, fill=BTN_RED_BOT if selected else VINTAGE_TEXT_MUTED)
            self.create_text(tick_x, 46, text=f'{value:g}×', tags=('speed_tick_label',),
                             fill=BTN_RED_BOT if selected else '#585249',
                             font=('Segoe UI', 10, 'bold' if selected else 'normal'))
        x = 24 + (right-24)*self.position/max(1, len(self.values)-1)
        self.create_oval(x-9, 12, x+9, 30, fill='#bab1a3', outline='')
        self.create_oval(x-8, 9, x+8, 25, fill=BTN_RED_BOT, outline='#a74b41', tags=('speed_thumb',))
        self.create_oval(x-7, 9, x+7, 22, fill=BTN_RED_TOP, outline='')
        self.create_line(x-3, 12, x+3, 12, fill='#f5a39a', width=2)
        if self.focus_get() is self:
            self.create_rectangle(2, 2, max(10, self.winfo_width()-2), int(self.cget('height'))-3,
                                  outline=VINTAGE_TEXT_MUTED, dash=(2, 2))
