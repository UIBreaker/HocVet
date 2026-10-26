"""Màu sắc và kiểu hiển thị chung của Học Vẹt."""
import math
import tkinter as tk
from tkinter import ttk

# ==========================================
# RETRO HARDWARE COLOR PALETTE (Braun / Dieter Rams)
# ==========================================
VINTAGE_BG = "#e7dfce"             # Nền kem cổ điển tổng thể
VINTAGE_CARD_BG = "#f5f1e5"        # Nền thẻ bề mặt mờ nhạt
VINTAGE_CARD_BORDER = "#c9c1b1"    # Viền thẻ nổi nhẹ
VINTAGE_INNER_GROOVE = "#ded8c9"   # Rãnh thụt / khe trượt
VINTAGE_TEXT_HEAD = "#3e3a35"      # Chữ tiêu đề tối màu
VINTAGE_TEXT_BODY = "#585249"      # Chữ thông tin chung
VINTAGE_TEXT_MUTED = "#8c8579"     # Chữ phụ / ghi chú

BTN_YELLOW_TOP = "#e8b056"
BTN_YELLOW_BOT = "#b88232"
BTN_YELLOW_TXT = "#433214"

BTN_GREEN_TOP = "#8eb77c"
BTN_GREEN_BOT = "#638c52"
BTN_GREEN_TXT = "#243a1c"

BTN_BLUE_TOP = "#96c5dc"
BTN_BLUE_BOT = "#699bb3"
BTN_BLUE_TXT = "#1c3848"

BTN_RED_TOP = "#d65c4f"
BTN_RED_BOT = "#a42a2a"
BTN_RED_TXT = "#ffffff"

BTN_BEIGE_TOP = "#e3ded4"
BTN_BEIGE_BOT = "#bcb5a7"
BTN_BEIGE_TXT = "#4d4841"

FONT_HEADER = ("Segoe UI", 12, "bold")
FONT_TITLE = ("Segoe UI", 9, "bold")
FONT_BODY = ("Segoe UI", 9)
FONT_BTN = ("Segoe UI", 9, "bold")


def apply_theme(root, scale):
    root.option_add('*Font', FONT_BODY)
    root.option_add('*Background', VINTAGE_BG)
    root.option_add('*Foreground', VINTAGE_TEXT_HEAD)
    root.option_add('*Entry.Background', '#fffdf8')
    root.option_add('*Entry.selectBackground', BTN_BLUE_TOP)
    root.option_add('*Text.selectBackground', BTN_BLUE_TOP)
    root.option_add('*Menu.activeBackground', BTN_BLUE_TOP)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', background=VINTAGE_CARD_BG, foreground=VINTAGE_TEXT_HEAD, font=FONT_BODY)
    style.configure('TFrame', background=VINTAGE_CARD_BG)
    style.configure('TNotebook',background=VINTAGE_BG,borderwidth=0)
    style.configure('TNotebook.Tab',font=FONT_BTN,padding=(12,8),background=BTN_BEIGE_TOP)
    style.map('TNotebook.Tab',background=[('selected',VINTAGE_CARD_BG)],foreground=[('selected',VINTAGE_TEXT_HEAD)])
    style.configure('Horizontal.TProgressbar',background=BTN_RED_TOP,troughcolor=VINTAGE_INNER_GROOVE)
    style.configure('TLabel', background=VINTAGE_CARD_BG, foreground=VINTAGE_TEXT_BODY)
    style.configure('TCheckbutton', background=VINTAGE_CARD_BG, foreground=VINTAGE_TEXT_BODY,
                    padding=round(4 * scale))
    style.map('TCheckbutton', background=[('active', VINTAGE_CARD_BG)])
    style.configure('TEntry', fieldbackground='#fffdf8', padding=round(5 * scale),
                    bordercolor=VINTAGE_CARD_BORDER, lightcolor=VINTAGE_CARD_BORDER)
    style.configure('TCombobox', fieldbackground='#fffdf8', background=BTN_BEIGE_TOP,
                    arrowcolor=VINTAGE_TEXT_HEAD, padding=round(4 * scale))
    style.map('TCombobox', fieldbackground=[('readonly', '#fffdf8')],
              selectbackground=[('readonly', BTN_BLUE_TOP)], selectforeground=[('readonly', BTN_BLUE_TXT)])
    style.configure('Profile.TCombobox', padding=(round(8*scale), round(6*scale)))
    for name, top, bottom, text in (
            ('TButton', BTN_BEIGE_TOP, BTN_BEIGE_BOT, BTN_BEIGE_TXT),
            ('Primary.TButton', BTN_GREEN_TOP, BTN_GREEN_BOT, BTN_GREEN_TXT),
            ('Info.TButton', BTN_BLUE_TOP, BTN_BLUE_BOT, BTN_BLUE_TXT),
            ('Danger.TButton', BTN_RED_TOP, BTN_RED_BOT, BTN_RED_TXT)):
        style.configure(name, background=top, foreground=text, bordercolor=bottom,
                        lightcolor=top, darkcolor=bottom, relief='raised', borderwidth=2,
                        font=FONT_BTN, padding=(round(10*scale), round(6*scale)), focusthickness=2)
        style.map(name, background=[('disabled', VINTAGE_INNER_GROOVE), ('pressed', bottom), ('active', top)],
                  foreground=[('disabled', VINTAGE_TEXT_MUTED)], relief=[('pressed', 'sunken')])
    style.configure('TSeparator', background=VINTAGE_CARD_BORDER)
    style.configure('TScrollbar', background=BTN_RED_TOP, troughcolor=VINTAGE_INNER_GROOVE,
                    arrowcolor=VINTAGE_TEXT_HEAD, bordercolor=VINTAGE_CARD_BORDER)
    style.configure('RetroHardware.Vertical.TScrollbar', background=BTN_RED_TOP,
                    troughcolor=VINTAGE_INNER_GROOVE, arrowcolor=VINTAGE_TEXT_HEAD)
    style.configure('RetroHardware.Treeview', background='#fffdf8', fieldbackground='#fffdf8',
                    foreground=VINTAGE_TEXT_HEAD, font=FONT_BODY, rowheight=round(28*scale), borderwidth=0)
    style.configure('RetroHardware.Treeview.Heading', background=VINTAGE_INNER_GROOVE,
                    foreground=VINTAGE_TEXT_HEAD, font=FONT_TITLE, relief='flat', padding=round(6*scale))
    style.map('RetroHardware.Treeview', background=[('selected', BTN_BLUE_TOP)],
              foreground=[('selected', BTN_BLUE_TXT)])


def create_dialog(parent, title, subtitle='', size=(640, 420), modal=True):
    from app_info import APP_NAME, APP_VERSION
    win = tk.Toplevel(parent)
    win.title(f'{title} — {APP_NAME}')
    win.configure(bg=VINTAGE_BG)
    win.transient(parent.winfo_toplevel())
    scale = parent.winfo_fpixels('1i') / 96
    width = min(round(size[0] * scale), parent.winfo_screenwidth() - 60)
    height = min(round(size[1] * scale), parent.winfo_screenheight() - 80)
    win.geometry(f'{width}x{height}')
    win.minsize(min(width, round(460*scale)), min(height, round(320*scale)))
    header = tk.Frame(win, bg=VINTAGE_BG, padx=16, pady=12)
    header.pack(fill=tk.X)
    tk.Label(header, text=f'{APP_NAME.upper()}  /  {APP_VERSION}', bg=VINTAGE_BG,
             fg=VINTAGE_TEXT_MUTED, font=FONT_TITLE).pack(anchor='w')
    tk.Label(header, text=title, bg=VINTAGE_BG, fg=VINTAGE_TEXT_HEAD,
             font=('Bahnschrift SemiCondensed', 19)).pack(anchor='w', pady=(4, 0))
    if subtitle:
        label = tk.Label(header, text=subtitle, bg=VINTAGE_BG, fg=VINTAGE_TEXT_BODY,
                         font=FONT_BODY, justify='left', anchor='w', wraplength=width-48)
        label.pack(fill=tk.X, pady=(6, 0))
        win.bind('<Configure>', lambda event: label.configure(wraplength=max(200, win.winfo_width()-48))
                 if event.widget is win else None, add='+')
    win.footer = ttk.Frame(win, padding=(16, 8, 16, 12))
    win.footer.pack(side=tk.BOTTOM, fill=tk.X)
    win.body = ttk.Frame(win, padding=16, relief='solid', borderwidth=1)
    win.body.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 4))
    if modal:
        win.grab_set()
    return win


def _run_modal(win, accept, cancel):
    root = win._root()
    app = getattr(root, '_hocvet_app', None)
    if app:
        app._register_shortcut_dialog(win, {'dialog_save': accept, 'dialog_cancel': cancel})
    else:
        win.bind('<Control-Return>', lambda event: accept())
        win.bind('<Escape>', lambda event: cancel())
    win.protocol('WM_DELETE_WINDOW', cancel)
    win.wait_window()


class ThemedMessages:
    @staticmethod
    def _show(title, message, parent=None, question=False, error=False):
        parent = parent or tk._default_root
        previous_grab = parent.grab_current()
        win = create_dialog(parent, title, 'Vui lòng xác nhận để tiếp tục.' if question else '', size=(600, 380))
        result = [False]
        # Vùng văn bản có cuộn để tên kịch bản dài / lỗi dài vẫn đọc được.
        text = tk.Text(win.body, wrap='word', font=FONT_BODY, bg=VINTAGE_CARD_BG,
                       fg=VINTAGE_TEXT_BODY, relief='flat', borderwidth=0, height=7, padx=4, pady=4)
        scroll = ttk.Scrollbar(win.body, command=text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.configure(yscrollcommand=scroll.set)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert('1.0', message)
        text.configure(state='disabled')
        def finish(value):
            result[0] = value
            win.destroy()
        accept = lambda: finish(True)
        cancel = lambda: finish(False)
        ttk.Button(win.footer, text='Xác nhận' if question else 'Đóng',
                   style='Danger.TButton' if question or error else 'Primary.TButton',
                   command=accept).pack(side=tk.RIGHT)
        if question:
            button = ttk.Button(win.footer, text='Hủy', command=cancel)
            button.pack(side=tk.RIGHT, padx=8)
            button.focus_set()
        _run_modal(win, accept, cancel)
        if previous_grab and previous_grab.winfo_exists():
            previous_grab.grab_set()
        return result[0]

    @staticmethod
    def showinfo(title, message, parent=None):
        return ThemedMessages._show(title, message, parent)

    showwarning = showinfo

    @staticmethod
    def showerror(title, message, parent=None):
        return ThemedMessages._show(title, message, parent, error=True)

    @staticmethod
    def askyesno(title, message, parent=None):
        return ThemedMessages._show(title, message, parent, question=True)


class ThemedInputs:
    @staticmethod
    def _ask(title, prompt, parent=None, initialvalue='', minvalue=None, maxvalue=None, numeric=False):
        parent = parent or tk._default_root
        previous_grab = parent.grab_current()
        win = create_dialog(parent, title, 'Nhập thông tin rồi chọn Lưu.', size=(620, 340))
        ttk.Label(win.body, text=prompt, wraplength=480, justify='left').pack(anchor='w', pady=(0, 12))
        value = tk.StringVar(value='' if initialvalue is None else str(initialvalue))
        entry = ttk.Entry(win.body, textvariable=value)
        entry.pack(fill=tk.X)
        entry.select_range(0, tk.END)
        result = [None]
        def accept():
            answer = value.get()
            if numeric:
                try:
                    answer = float(answer)
                    if not math.isfinite(answer):
                        raise ValueError()
                    if minvalue is not None and answer < minvalue or maxvalue is not None and answer > maxvalue:
                        raise ValueError()
                except ValueError:
                    ThemedMessages.showerror('Giá trị không hợp lệ',
                        f'Nhập một số từ {minvalue if minvalue is not None else "−∞"} đến {maxvalue if maxvalue is not None else "+∞"}.', parent=win)
                    entry.focus_set()
                    return
            result[0] = answer
            win.destroy()
        cancel = win.destroy
        ttk.Button(win.footer, text='Lưu', style='Primary.TButton', command=accept).pack(side=tk.RIGHT)
        ttk.Button(win.footer, text='Hủy', command=cancel).pack(side=tk.RIGHT, padx=8)
        win.bind('<Return>', lambda event: accept())
        entry.focus_set()
        _run_modal(win, accept, cancel)
        if previous_grab and previous_grab.winfo_exists():
            previous_grab.grab_set()
        return result[0]

    @staticmethod
    def askstring(title, prompt, **options):
        return ThemedInputs._ask(title, prompt, **options)

    @staticmethod
    def askfloat(title, prompt, **options):
        return ThemedInputs._ask(title, prompt, numeric=True, **options)
