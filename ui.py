"""
Học Vẹt - Giao diện điều khiển thao tác trên Windows
Tác giả: Nhật Nam (GitHub: @UIBreaker)

Các chức năng chính:
- Thêm tính năng Xóa kịch bản (Delete Profile) linh hoạt từ thanh điều khiển hoặc trực tiếp trên từng thẻ kịch bản với xác nhận an toàn.
- Bố cục danh sách kịch bản (Script Deck) đẹp mắt, trực quan, dễ quản lý.
- Thông báo Windows Toast thời gian thực cho mọi sự kiện:
  + Bắt đầu học thao tác
  + Dừng học & lưu thao tác
  + Dừng khẩn cấp (Panic Stop)
  + Xóa sạch các bước / Xóa kịch bản
  + Bắt đầu chạy kịch bản
  + Hoàn thành kịch bản
- Tính năng Sao chép & Dán kịch bản (Copy/Paste Script qua Clipboard) để chia sẻ siêu tốc giữa các máy tính.
- Chạy ngầm dưới Khay hệ thống Windows (System Tray), phím tắt hoạt động 100% khi ẩn.
- Tùy biến tổ hợp phím trong Cài đặt.
- Biểu tượng ứng dụng: Chú vẹt xanh gõ phím cơ cổ điển.
"""

import os
import sys
import time
import threading
import queue
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageDraw
from screen_capture import capture_region
from record_notice import RecordNotice
from retro_controls import RetroSlider
from shortcuts import SHORTCUT_ACTIONS, parse_hotkey, tk_sequence, validate_shortcuts
import pystray

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core import (
    enable_dpi_awareness,
    MacroAction,
    ScriptProfile,
    MacroManager,
    MacroStorage,
    normalize_hotkey,
    play_sound,
)

from app_info import APP_NAME, APP_VERSION
from ui_theme import (
    VINTAGE_BG, VINTAGE_CARD_BG, VINTAGE_CARD_BORDER, VINTAGE_INNER_GROOVE,
    VINTAGE_TEXT_HEAD, VINTAGE_TEXT_BODY, VINTAGE_TEXT_MUTED,
    BTN_YELLOW_TOP, BTN_YELLOW_BOT, BTN_YELLOW_TXT, BTN_GREEN_TOP, BTN_GREEN_BOT, BTN_GREEN_TXT,
    BTN_BLUE_TOP, BTN_BLUE_BOT, BTN_BLUE_TXT, BTN_RED_TOP, BTN_RED_BOT, BTN_RED_TXT,
    BTN_BEIGE_TOP, BTN_BEIGE_BOT, BTN_BEIGE_TXT, FONT_HEADER, FONT_TITLE, FONT_BODY, FONT_BTN,
    apply_theme, create_dialog, ThemedMessages, ThemedInputs,
)
messagebox = ThemedMessages
simpledialog = ThemedInputs


def get_resource_path(relative_path: str) -> str:
    """Lấy đường dẫn tài nguyên chuẩn xác kể cả khi chạy từ mã nguồn hoặc file .exe đóng gói."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def create_tray_icon_image():
    """Tạo biểu tượng System Tray từ ảnh chú vẹt xanh gõ phím cơ với bo tròn mềm mại."""
    icon_path = get_resource_path("app_icon.png")
    if os.path.exists(icon_path):
        try:
            img = Image.open(icon_path).convert("RGBA")
            size = (64, 64)
            img = img.resize(size, Image.Resampling.LANCZOS)
            mask = Image.new("L", size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle([(0, 0), (63, 63)], radius=14, fill=255)
            output = Image.new("RGBA", size, (0, 0, 0, 0))
            output.paste(img, (0, 0), mask=mask)
            return output
        except Exception:
            pass

    # Fallback
    img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill="#ece7de", outline="#ded7cb", width=3)
    draw.ellipse([14, 14, 50, 50], fill="#d94f4f", outline="#a42a2a", width=2)
    return img


class Retro3DButton(tk.Canvas):
    """Nút bấm 3D bề mặt mờ (Matte) có độ nảy cơ học khi nhấp."""
    def __init__(
        self,
        parent,
        text="",
        command=None,
        width=130,
        height=38,
        top_color=BTN_YELLOW_TOP,
        bot_color=BTN_YELLOW_BOT,
        text_color=BTN_YELLOW_TXT,
        font=FONT_BTN,
        radius=8,
        **kwargs
    ):
        dpi_scale = parent.winfo_fpixels('1i') / 96
        width, height = round(width * dpi_scale), round(height * dpi_scale)
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg") if hasattr(parent, "cget") else VINTAGE_CARD_BG,
            highlightthickness=0,
            cursor="hand2",
            **kwargs
        )
        self.text = text
        self.command = command
        self.width = width
        self.height = height
        self.top_color = top_color
        self.bot_color = bot_color
        self.text_color = text_color
        self.font = font
        self.radius = radius
        self.pressed = False
        self.state = "normal"

        self.bind('<Configure>', self._resize)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.configure(takefocus=True)
        self.bind('<Return>', self._activate)
        self.bind('<space>', self._activate)
        self.bind('<FocusIn>', lambda event: self.configure(highlightthickness=2, highlightbackground=BTN_BLUE_TXT))
        self.bind('<FocusOut>', lambda event: self.configure(highlightthickness=0))
        self._draw()

    def _resize(self, event):
        if (self.width, self.height) != (event.width, event.height):
            self.width, self.height = event.width, event.height
            self._draw()

    def _activate(self, event=None):
        if self.state != 'disabled' and self.command:
            self.command()
        return 'break'

    def _draw_round_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1,
            x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2,
            x1, y2 - r, x1, y1 + r, x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _draw(self):
        self.delete("all")
        offset = 3 if self.pressed else 0
        w, h = self.width, self.height
        r = self.radius

        if self.state == "disabled":
            t_col = BTN_BEIGE_TOP
            b_col = BTN_BEIGE_BOT
            txt_col = VINTAGE_TEXT_MUTED
        else:
            t_col = self.top_color
            b_col = self.bot_color
            txt_col = self.text_color

        self._draw_round_rect(2, 2, w - 2, h - 2, r, fill=b_col, outline="")
        self._draw_round_rect(2, 2 + offset, w - 2, h - 6 + offset, r, fill=t_col, outline="")
        self.create_text(
            w // 2,
            (h // 2 - 2) + offset,
            text=self.text,
            fill=txt_col,
            font=self.font,
            width=max(20, w-16),
            justify='center',
        )

    def _on_press(self, event):
        if self.state == "disabled":
            return
        self.focus_set()
        self.pressed = True
        self._draw()

    def _on_release(self, event):
        if self.state == "disabled":
            return
        self.pressed = False
        self._draw()
        if self.command:
            self.command()

    def configure_state(self, state: str):
        self.state = state
        self.configure(takefocus=state != 'disabled')
        self.configure(cursor="hand2" if state != "disabled" else "arrow")
        self._draw()

    def set_text(self, new_text: str):
        self.text = new_text
        self._draw()


class HocVetApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} // Nhật Nam (@UIBreaker) [v{APP_VERSION}]")
        enable_dpi_awareness()
        self.dpi_scale = root.winfo_fpixels('1i') / 96
        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        self.root.geometry(f"{min(round(800*self.dpi_scale), screen_w - 60)}x{min(round(740*self.dpi_scale), screen_h - 80)}")
        self.root.minsize(min(640, screen_w - 60), min(420, screen_h - 80))
        self.root.configure(bg=VINTAGE_BG)

        # Cài đặt biểu tượng ứng dụng chú vẹt gõ phím cơ
        ico_path = get_resource_path("app_icon.ico")
        png_path = get_resource_path("app_icon.png")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(default=ico_path)
            except Exception:
                pass
        elif os.path.exists(png_path):
            try:
                self._app_icon_tk = tk.PhotoImage(file=png_path)
                self.root.iconphoto(True, self._app_icon_tk)
            except Exception:
                pass

        # Khởi tạo Core MacroManager
        self.manager = MacroManager()
        self._shortcut_dialogs = {}
        self._shortcut_bindings = []
        self._closing = False
        self._ui_events = queue.SimpleQueue()
        self._recorded_count = 0
        self._rendered_record_count = 0
        self._pending_progress = None
        self._last_progress_draw = 0.0
        self._preview_start = 0
        self._preview_profile = None
        self.record_notice = RecordNotice(root)
        self.root._hocvet_app = self
        self._shortcut_commands = {
            'play': self._cmd_start_playing, 'stop_record': self._cmd_stop_recording,
            'add_profile': self._cmd_add_profile, 'edit_profile': self._edit_active_profile,
            'delete_profile': self._cmd_delete_active_profile,
            'copy_script': self._cmd_copy_script, 'paste_script': self._cmd_paste_script,
            'import_file': self._cmd_load_file, 'export_file': self._cmd_save_file,
            'edit_delay': self._cmd_edit_delay, 'delete_action': self._cmd_delete_selected_action,
            'clear_actions': self._cmd_clear_actions,
            'wait_window': lambda: self._cmd_add_condition('wait_window'),
            'wait_image': lambda: self._cmd_add_condition('wait_image'),
            'edit_condition': self._cmd_edit_condition,
            'details': self._toggle_details,
            'prev_page': lambda: self._change_preview(-1),
            'next_page': lambda: self._change_preview(1),
            'settings': self._cmd_open_settings, 'help': self._cmd_help,
            'hide': self._hide_to_tray, 'show': self._show_from_tray,
            'data_folder': lambda: os.startfile(os.path.dirname(self.manager.library_path)),
            'exit': self._exit_app,
            'toggle_movement': lambda: self.ignore_movement_var.set(not self.ignore_movement_var.get()),
            'toggle_countdown': lambda: self.countdown_var.set(not self.countdown_var.get()),
        }
        for name in SHORTCUT_ACTIONS:
            if name.startswith('speed_'):
                self._shortcut_commands[name] = lambda value=name[6:]: self._set_speed(value + 'x')
        self.manager.on_command = lambda name: self._post(self._dispatch_shortcut, name)
        self.manager.on_record_toggle = lambda: self._post(self._toggle_recording)
        self.manager.on_panic = lambda: self._post(self._cmd_emergency_stop)
        self.manager.on_record_stopped = lambda profile, count: self._post(self._record_saved, profile, count)
        self.manager.recorder.ignore_mouse = self._is_own_window
        self.manager.recorder.ignore_keyboard = self._is_own_focus

        # Biến cấu hình giao diện
        self.speed_var = tk.StringVar(value="1.0x")
        self.loop_count_var = tk.StringVar(value="1")
        self.loop_delay_var = tk.StringVar(value="1.0")
        self.ignore_movement_var = tk.BooleanVar(value=True)
        self.countdown_var = tk.BooleanVar(value=True)

        self.countdown_timer = None
        self.tray_icon: Optional[pystray.Icon] = None

        # Kết nối Callbacks từ Core Manager
        self.manager.on_state_changed = self._on_manager_state_changed
        self.manager.on_action_recorded = self._on_action_recorded
        self.manager.on_step = self._on_player_step
        self.manager.on_play_finished = lambda success, aborted: self._post(self._on_player_finished, success, aborted)
        self.manager.on_profile_triggered = self._on_profile_triggered
        self.manager.player.on_wait = lambda text: self._post(self._show_wait, text)

        # Kích hoạt DPI Awareness
        enable_dpi_awareness()

        # Cài đặt Theme & Xây dựng Giao diện
        self._setup_retro_styles()
        self._build_ui()
        self._install_shortcuts()

        # Khởi động phím tắt toàn cục
        self.manager.start_global_hotkeys()

        # Khởi động Khay hệ thống (System Tray)
        self._setup_system_tray()

        # Bắt sự kiện đóng cửa sổ
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self._handle_state_ui(self.manager.state)
        self._pump_timer = self.root.after(40, self._process_ui_events)
        self.root.bind('<Destroy>', self._cleanup_ui, add='+')

    def _post(self, callback, *args):
        if not self._closing:
            self._ui_events.put((callback, args))

    def _process_ui_events(self):
        if self._closing:
            return
        if getattr(self, '_pump_timer', None):
            self.root.after_cancel(self._pump_timer)
        self._pump_timer = self.root.after(40, self._process_ui_events)
        for _ in range(50):
            try:
                callback, args = self._ui_events.get_nowait()
            except queue.Empty:
                break
            try:
                callback(*args)
            except Exception as error:
                self._set_hud(str(error), BTN_RED_BOT)
                self.record_notice.show('Không thể thực hiện', str(error), duration=5000)
        if self.manager.state == MacroManager.STATE_RECORDING and self._recorded_count != self._rendered_record_count:
            count = self._recorded_count
            self.lbl_stats.configure(text=f'Đang học · {count:,} thao tác · phím dừng: {self.manager.button_hotkeys.get("stop_record") or self.manager.hotkey_record_str}')
            self._rendered_record_count = count
        now = time.monotonic()
        if self._pending_progress and now-self._last_progress_draw >= .1:
            progress, self._pending_progress = self._pending_progress, None
            self._draw_player_step(*progress)
            self._last_progress_draw = now

    def _show_wait(self, text):
        self._pending_progress = None
        self._set_hud(text, BTN_BLUE_TXT)

    def _cleanup_ui(self, event):
        if event.widget is self.root:
            self._closing = True
            self.record_notice.close()
            for timer in (getattr(self, '_pump_timer', None), self.countdown_timer):
                if timer:
                    try:
                        self.root.after_cancel(timer)
                    except tk.TclError:
                        pass

    @staticmethod
    def _is_own_window(x, y):
        user32 = ctypes.windll.user32
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        user32.WindowFromPoint.restype = wintypes.HWND
        hwnd = user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
        process = wintypes.DWORD()
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process))
        return process.value == os.getpid()

    @staticmethod
    def _is_own_focus():
        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.restype = wintypes.HWND
        process = wintypes.DWORD()
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(process))
        return process.value == os.getpid()

    def _setup_retro_styles(self):
        apply_theme(self.root, self.dpi_scale)

    def _new_dialog(self, title, subtitle='', size=(700, 520), modal=True):
        return create_dialog(self.root, title, subtitle, size=size, modal=modal)

    def _create_section_card(self, parent, section_name: str) -> tk.Frame:
        container = tk.Frame(parent, bg=VINTAGE_BG)
        container.pack(fill=tk.X, padx=16, pady=3)

        lbl_sec = tk.Label(
            container,
            text=section_name,
            font=("Bahnschrift SemiCondensed", 20),
            bg=VINTAGE_BG,
            fg=VINTAGE_TEXT_HEAD,
        )
        lbl_sec.pack(anchor="w", padx=4, pady=(1, 2))

        card = tk.Frame(
            container,
            bg=VINTAGE_CARD_BG,
            highlightbackground=VINTAGE_CARD_BORDER,
            highlightthickness=2,
            padx=12,
            pady=8,
        )
        card.pack(fill=tk.BOTH, expand=True)
        tk.Frame(container, height=3, bg='#b8b0a0').pack(fill=tk.X, padx=(2, 0))
        return card

    def _build_ui(self):
        menu = tk.Menu(self.root)
        scripts = tk.Menu(menu, tearoff=False)
        for label, command in (('Tạo kịch bản', self._cmd_add_profile), ('Đổi tên / phím chạy', self._edit_active_profile),
                ('Nhập file', self._cmd_load_file), ('Chia sẻ file', self._cmd_save_file),
                ('Sao chép mã', self._cmd_copy_script), ('Dán mã kịch bản', self._cmd_paste_script),
                ('Xóa kịch bản đang chọn', self._cmd_delete_active_profile)):
            scripts.add_command(label=label, command=command)
        menu.add_cascade(label='Kịch bản', menu=scripts)
        menu.add_command(label='Cài đặt phím tắt', command=self._cmd_open_settings)
        menu.add_command(label='Hướng dẫn', command=self._cmd_help)
        menu.add_command(label='Thư mục dữ liệu', command=lambda: os.startfile(os.path.dirname(self.manager.library_path)))
        self.root.configure(menu=menu)
        self.status_banner = tk.Label(self.root, text='SẴN SÀNG', bg=VINTAGE_BG, fg=VINTAGE_TEXT_HEAD,
                                      font=('Segoe UI', 10, 'bold'), pady=8, wraplength=700)
        self.status_banner.pack(side=tk.BOTTOM, fill=tk.X)
        self.content_canvas = tk.Canvas(self.root, bg=VINTAGE_BG, highlightthickness=0)
        bar = ttk.Scrollbar(self.root, orient='vertical', command=self.content_canvas.yview)
        bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content_canvas.pack(fill=tk.BOTH, expand=True)
        self.content_canvas.configure(yscrollcommand=bar.set)
        self.content = tk.Frame(self.content_canvas, bg=VINTAGE_BG)
        self.content_window = self.content_canvas.create_window(0, 0, window=self.content, anchor='nw')
        def reflow(event=None):
            self.content_canvas.configure(scrollregion=self.content_canvas.bbox('all'))
            needed = self.content.winfo_reqheight() > self.content_canvas.winfo_height()+2
            if needed and not bar.winfo_manager():
                bar.pack(side=tk.RIGHT, fill=tk.Y, before=self.content_canvas)
            elif not needed and bar.winfo_manager():
                bar.pack_forget()
        self.content.bind('<Configure>', reflow)
        def resize(event):
            self.content_canvas.itemconfigure(self.content_window, width=event.width)
            self.status_banner.configure(wraplength=max(280, event.width-32))
            reflow()
        self.content_canvas.bind('<Configure>', resize)
        self.root.bind_all('<MouseWheel>', lambda event: self.content_canvas.yview_scroll(-int(event.delta/120), 'units')
                           if event.widget.winfo_toplevel() is self.root else None, add='+')
        header = tk.Frame(self.content, bg=VINTAGE_BG, padx=20, pady=12)
        header.pack(fill=tk.X)
        tk.Label(header, text='HỌC VẸT', bg=VINTAGE_BG, fg=VINTAGE_TEXT_HEAD,
                 font=('Bahnschrift SemiCondensed', 28, 'bold')).pack(side=tk.LEFT)
        tk.Label(header, text=f'v{APP_VERSION}', bg=VINTAGE_BG, fg=VINTAGE_TEXT_MUTED, font=FONT_BODY).pack(side=tk.LEFT, padx=10)
        Retro3DButton(header, text='Cài đặt', width=88, height=32, top_color=BTN_BEIGE_TOP,
                      bot_color=BTN_BEIGE_BOT, text_color=BTN_BEIGE_TXT, command=self._cmd_open_settings).pack(side=tk.RIGHT)
        Retro3DButton(header, text='Thu vào khay', width=105, height=32, top_color=BTN_BEIGE_TOP,
                      bot_color=BTN_BEIGE_BOT, text_color=BTN_BEIGE_TXT, command=self._hide_to_tray).pack(side=tk.RIGHT, padx=8)
        select = self._create_section_card(self.content, '01  CHỌN KỊCH BẢN')
        self.profile_choice = ttk.Combobox(select, state='readonly', font=FONT_BODY)
        self.profile_choice.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.profile_choice.bind('<<ComboboxSelected>>', lambda event: self._select_profile(self.manager.profiles[self.profile_choice.current()].id))
        Retro3DButton(select, text='+ Tạo mới', width=100, height=34, top_color=BTN_BEIGE_TOP,
                      bot_color=BTN_BEIGE_BOT, text_color=BTN_BEIGE_TXT, command=self._cmd_add_profile).pack(side=tk.RIGHT)
        controls = self._create_section_card(self.content, '02  ĐIỀU CHỈNH')
        track = tk.Frame(controls, bg=VINTAGE_CARD_BG)
        track.pack(fill=tk.X)
        tk.Label(track, text='TỐC ĐỘ', bg=VINTAGE_CARD_BG, fg=VINTAGE_TEXT_BODY, font=FONT_TITLE).pack(side=tk.LEFT)
        self.speed_readout = tk.Label(track, text='1.0×', font=('Bahnschrift', 16, 'bold'), fg=BTN_RED_BOT, bg=VINTAGE_CARD_BG)
        self.speed_readout.pack(side=tk.RIGHT)
        self.speed_buttons = {}
        self.speed_slider = RetroSlider(controls, [.5, .8, 1., 1.25, 1.5, 2.], lambda value: self._set_speed(f'{value:g}x'))
        self.speed_slider.pack(fill=tk.X, pady=(2, 6))
        options = tk.Frame(controls, bg=VINTAGE_CARD_BG)
        options.pack(fill=tk.X)
        tk.Label(options, text='Lặp lại', bg=VINTAGE_CARD_BG, font=FONT_BODY).pack(side=tk.LEFT)
        self.entry_loop = ttk.Spinbox(options, from_=0, to=9999, textvariable=self.loop_count_var, width=4)
        self.entry_loop.pack(side=tk.LEFT, padx=(6, 18))
        tk.Label(options, text='Nghỉ giữa vòng (giây)', bg=VINTAGE_CARD_BG, font=FONT_BODY).pack(side=tk.LEFT)
        self.entry_delay = ttk.Entry(options, textvariable=self.loop_delay_var, width=5)
        self.entry_delay.pack(side=tk.LEFT, padx=6)
        tk.Label(controls, text='Lặp lại: 1 = một lần · 0 = liên tục', bg=VINTAGE_CARD_BG,
                 fg=VINTAGE_TEXT_MUTED, font=FONT_BODY).pack(anchor='w', pady=(8, 0))
        action = self._create_section_card(self.content, '03  HỌC & CHẠY')
        row = tk.Frame(action, bg=VINTAGE_CARD_BG)
        row.pack(fill=tk.X, pady=(2, 10))
        for column in range(3): row.columnconfigure(column, weight=1, uniform='actions')
        self.btn_rec = Retro3DButton(row, text='HỌC · F8', width=165, height=48, command=self._cmd_start_recording)
        self.btn_play = Retro3DButton(row, text='CHẠY · F9', width=165, height=48,
            top_color=BTN_GREEN_TOP, bot_color=BTN_GREEN_BOT, text_color=BTN_GREEN_TXT, command=self._cmd_start_playing)
        self.btn_stop = Retro3DButton(row, text='DỪNG HỌC', width=165, height=48,
            top_color=BTN_BLUE_TOP, bot_color=BTN_BLUE_BOT, text_color=BTN_BLUE_TXT, command=self._cmd_stop_recording)
        for column, button in enumerate((self.btn_rec, self.btn_play, self.btn_stop)):
            button.grid(row=0, column=column, sticky='ew', padx=4)
        def arrange(event):
            narrow = event.width < round(620*self.dpi_scale)
            for column, button in enumerate((self.btn_rec, self.btn_play, self.btn_stop)):
                button.grid(row=column if narrow else 0, column=0 if narrow else column,
                            columnspan=3 if narrow else 1, sticky='ew', padx=4, pady=3)
        row.bind('<Configure>', arrange)
        self.btn_stop.configure_state('disabled')
        self.btn_panic = Retro3DButton(action, text='DỪNG KHẨN CẤP · ESC', width=230, height=34,
            top_color=BTN_RED_TOP, bot_color=BTN_RED_BOT, text_color=BTN_RED_TXT, command=self._cmd_emergency_stop)
        self.btn_panic.pack(side=tk.LEFT, padx=4)
        self.workflow_hint = tk.StringVar()
        tk.Label(action, textvariable=self.workflow_hint, bg=VINTAGE_CARD_BG,
                 fg=VINTAGE_TEXT_MUTED, font=FONT_BODY, wraplength=260, justify='left').pack(side=tk.LEFT, padx=12)
        file_row = tk.Frame(self.content, bg=VINTAGE_BG, padx=16, pady=12)
        file_row.pack(fill=tk.X)
        for label, command in (('Nhập kịch bản', self._cmd_load_file), ('Chia sẻ kịch bản', self._cmd_save_file),
                               ('Chi tiết / sửa bước', self._toggle_details)):
            ttk.Button(file_row, text=label, command=command).pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
        self.lbl_stats = tk.Label(self.content, bg=VINTAGE_BG, fg=VINTAGE_TEXT_BODY, font=FONT_BODY)
        self.lbl_stats.pack(anchor='w', padx=24, pady=(0, 8))
        self.details = tk.Frame(self.content, bg=VINTAGE_BG)
        detail_card = self._create_section_card(self.details, 'CÁC BƯỚC THAO TÁC')
        tools = tk.Frame(detail_card, bg=VINTAGE_CARD_BG)
        tools.pack(fill=tk.X, pady=(0, 8))
        for label, command in (('+ Chờ cửa sổ', lambda: self._cmd_add_condition('wait_window')),
                ('+ Chờ ảnh', lambda: self._cmd_add_condition('wait_image')), ('Sửa điều kiện', self._cmd_edit_condition)):
            ttk.Button(tools, text=label, command=command).pack(side=tk.LEFT, padx=(0, 4))
        self.tree = ttk.Treeview(detail_card, columns=('stt', 'delay', 'type', 'detail'), show='headings',
                                 selectmode='browse', height=6, style='RetroHardware.Treeview')
        for name, label, width in (('stt', '#', 44), ('delay', 'Chờ', 66), ('type', 'Thao tác', 130), ('detail', 'Chi tiết', 300)):
            self.tree.heading(name, text=label)
            self.tree.column(name, width=width, minwidth=40, stretch=name=='detail')
        tree_bar = ttk.Scrollbar(detail_card, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_bar.set)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        tree_bar.pack(side=tk.RIGHT, fill=tk.Y)
        edits = tk.Frame(self.details, bg=VINTAGE_BG, padx=20, pady=6)
        edits.pack(fill=tk.X)
        for label, command in (('Sửa độ trễ', self._cmd_edit_delay), ('Xóa bước', self._cmd_delete_selected_action), ('Xóa hết bước', self._cmd_clear_actions)):
            ttk.Button(edits, text=label, command=command).pack(side=tk.LEFT, padx=4)
        pages = tk.Frame(self.details, bg=VINTAGE_BG, padx=20, pady=6)
        pages.pack(fill=tk.X)
        self.prev_page = ttk.Button(pages, text='← Trang trước', command=lambda: self._change_preview(-1))
        self.prev_page.pack(side=tk.LEFT)
        self.preview_label = tk.Label(pages, bg=VINTAGE_BG, fg=VINTAGE_TEXT_MUTED, font=FONT_BODY)
        self.preview_label.pack(side=tk.LEFT, padx=12)
        self.next_page = ttk.Button(pages, text='Trang sau →', command=lambda: self._change_preview(1))
        self.next_page.pack(side=tk.RIGHT)
        self._refresh_profile_deck()

    def _toggle_details(self):
        if self.details.winfo_manager():
            self.details.pack_forget()
        else:
            self.details.pack(fill=tk.BOTH, expand=True)
            self._refresh_action_tree()

    def _change_preview(self, direction):
        self._preview_start = max(0, self._preview_start + direction*1000)
        self._refresh_action_tree()

    # ==========================================
    # THÔNG BÁO WINDOWS NATIVE (TOAST / SYSTEM NOTIFICATION)
    # ==========================================
    def notify_windows(self, title: str, message: str):
        """Gửi thông báo Windows Toast trực tiếp góc màn hình."""
        if self.tray_icon:
            try:
                self.tray_icon.notify(message, title)
            except Exception:
                pass

    # ==========================================
    # QUẢN LÝ KHAY HỆ THỐNG (SYSTEM TRAY)
    # ==========================================
    def _setup_system_tray(self):
        """Khởi tạo icon khay hệ thống Windows."""
        icon_img = create_tray_icon_image()

        def _action_open(icon, item):
            self._post(self._show_from_tray)

        def _action_panic(icon, item):
            self._post(self._cmd_emergency_stop)

        def _action_exit(icon, item):
            self._post(self._exit_app)

        tray_menu = pystray.Menu(
            pystray.MenuItem("📌 Mở giao diện chính", _action_open, default=True),
            pystray.MenuItem("🛑 Dừng khẩn cấp (ESC)", _action_panic),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Thoát ứng dụng", _action_exit),
        )

        self.tray_icon = pystray.Icon(
            "HocVet",
            icon_img,
            f"{APP_NAME} v{APP_VERSION} - Nhật Nam (@UIBreaker)",
            tray_menu,
        )

        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _hide_to_tray(self):
        """Ẩn cửa sổ xuống khay hệ thống."""
        self.root.withdraw()
        self.notify_windows(
            f"{APP_NAME} (v{APP_VERSION})",
            "Ứng dụng đã thu nhỏ xuống khay hệ thống! Phím tắt kích hoạt vẫn hoạt động bình thường trong nền."
        )

    def _show_from_tray(self):
        """Khôi phục cửa sổ từ khay hệ thống."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _on_window_close(self):
        """Khi người dùng bấm nút [X] ở góc cửa sổ."""
        if self.manager.minimize_to_tray_on_close:
            self._hide_to_tray()
        else:
            self._exit_app()

    def _exit_app(self):
        """Thoát hoàn toàn ứng dụng."""
        self._closing = True
        self.record_notice.close()
        self.manager.stop_global_hotkeys()
        self.manager.stop_playing()
        if self.countdown_timer:
            self.root.after_cancel(self.countdown_timer)
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.root.after(0, self.root.destroy)

    # ==========================================
    # CÀI ĐẶT TỔ HỢP PHÍM (HOTKEY SETTINGS)
    # ==========================================
    def _install_shortcuts(self):
        for sequence, binding in self._shortcut_bindings:
            self.root.unbind(sequence, binding)
        self._shortcut_bindings.clear()
        for name, text in self.manager.button_hotkeys.items():
            if text and self.manager.button_hotkey_scopes.get(name) == 'app':
                sequence = tk_sequence(text)
                def invoke(event, action=name, hotkey=text):
                    if event.widget.winfo_toplevel() != self.root:
                        return
                    # Phím chữ đơn không cướp ký tự đang nhập trong ô văn bản.
                    if '+' not in hotkey and len(hotkey) == 1 and isinstance(event.widget, (tk.Entry, tk.Text, ttk.Entry, ttk.Spinbox)):
                        return
                    self._dispatch_shortcut(action)
                    return 'break'
                sequences = [sequence]
                key = sequence[:-1].rsplit('-', 1)[-1].lstrip('<')
                if len(key) == 1 and key.isalpha():
                    sequences.append(sequence[:-2] + key.swapcase() + '>')
                for variant in sequences:
                    binding = self.root.bind(variant, invoke, add='+')
                    self._shortcut_bindings.append((variant, binding))

    def _dispatch_shortcut(self, name):
        if name == 'stop_record' and self.manager.state in (MacroManager.STATE_RECORDING, MacroManager.STATE_COUNTDOWN):
            self._cmd_stop_recording()
            return
        if self.root.grab_current() is not None or any(win.winfo_exists() for win in self._shortcut_dialogs):
            return
        if self.manager.state != MacroManager.STATE_IDLE and not (
                name == 'stop_record' and self.manager.state in (MacroManager.STATE_RECORDING, MacroManager.STATE_COUNTDOWN)):
            return
        command = self._shortcut_commands.get(name)
        if command:
            command()

    def _edit_active_profile(self):
        profile = self.manager.get_active_profile()
        if profile:
            self._cmd_quick_edit_profile(profile.id)

    def _register_shortcut_dialog(self, win, commands):
        self._shortcut_dialogs[win] = commands
        if self.manager.state == MacroManager.STATE_IDLE:
            self.manager.shortcuts_suspended = True
            self.manager.stop_global_hotkeys()
        for name, callback in commands.items():
            text = self.manager.button_hotkeys.get(name, '')
            if text:
                def invoke(event, command=callback):
                    command()
                    return 'break'
                win.bind(tk_sequence(text), invoke)
        def close(event):
            if event.widget is win:
                self._shortcut_dialogs.pop(win, None)
                if not self._shortcut_dialogs and not self._closing:
                    self.manager.shortcuts_suspended = False
                    self.manager.reload_global_hotkeys()
        win.bind('<Destroy>', close, add='+')

    def _cmd_open_settings(self):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        win = self._new_dialog('Cài đặt phím tắt',
            'Gán phím cho từng thao tác và chọn phạm vi sử dụng.', size=(860, 740))
        panel = win.body
        ttk.Label(panel, text='Gõ tên phím (F6, Ctrl+Shift+K) hoặc bấm Ghi phím rồi nhấn tổ hợp.', wraplength=650).pack(anchor='w')
        ttk.Label(panel, text='Học, Dừng học và Khẩn cấp dùng được cả khi chạy nền. Các lệnh khác có thể chọn phạm vi; để trống để bỏ gán (trừ Học và Khẩn cấp).', wraplength=650).pack(anchor='w', pady=(4, 8))
        holder = ttk.Frame(panel)
        holder.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(holder, bg=VINTAGE_CARD_BG, highlightthickness=0)
        bar = ttk.Scrollbar(holder, orient='vertical', command=canvas.yview)
        bar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        horizontal = ttk.Scrollbar(panel, orient='horizontal', command=canvas.xview)
        horizontal.pack(fill=tk.X)
        canvas.configure(yscrollcommand=bar.set, xscrollcommand=horizontal.set)
        rows = ttk.Frame(canvas, padding=(0, 0, 8, 0))
        item = canvas.create_window(0, 0, window=rows, anchor='nw')
        rows.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(item, width=max(round(710*self.dpi_scale), event.width)))
        win.bind('<MouseWheel>', lambda event: canvas.yview_scroll(-int(event.delta/120), 'units'))
        variables = {name: tk.StringVar(value=value) for name, value in self.manager.shortcut_values().items()}
        scopes = {name: tk.StringVar(value='Toàn cục' if value == 'global' else 'Trong ứng dụng')
                  for name, value in self.manager.button_hotkey_scopes.items()}
        self.shortcut_entries = {}
        entries = self.shortcut_entries
        capture_hint = ttk.Label(panel, text='Phím đang lưu chỉ được đổi sau khi bấm Lưu cài đặt.')
        capture_hint.pack(anchor='w', pady=6)
        armed = [None]
        def capture(entry, variable):
            if armed[0]:
                armed[0].unbind('<KeyPress>')
            armed[0] = entry
            capture_hint.configure(text='Đang ghi phím: bấm một phím chính, có thể giữ Ctrl / Alt / Shift / Win.')
            entry.focus_set()
            def pressed(event):
                modifiers = {'Control_L', 'Control_R', 'Shift_L', 'Shift_R', 'Alt_L', 'Alt_R', 'Meta_L', 'Meta_R', 'Super_L', 'Super_R'}
                if event.keysym in modifiers:
                    return 'break'
                names = {'Return': 'Enter', 'KP_Enter': 'Enter', 'Escape': 'ESC', 'Prior': 'Page_Up',
                         'Next': 'Page_Down', 'BackSpace': 'Backspace', 'space': 'Space',
                         'comma': ',', 'period': '.', 'minus': '-', 'slash': '/', 'backslash': chr(92)}
                key = names.get(event.keysym, event.keysym)
                parts = []
                if event.state & 4: parts.append('Ctrl')
                if event.state & (8 | 0x20000): parts.append('Alt')
                if event.state & 1: parts.append('Shift')
                if event.state & 0x40: parts.append('Win')
                parts.append(key.upper() if len(key) == 1 else key)
                text = '+'.join(parts)
                try:
                    parse_hotkey(text)
                    variable.set(text)
                    capture_hint.configure(text=f'Đã chọn {text}. Bấm Lưu cài đặt để áp dụng.')
                    entry.unbind('<KeyPress>')
                    armed[0] = None
                except ValueError:
                    capture_hint.configure(text='Không nhận diện được phím này. Bạn có thể gõ tên phím trực tiếp.')
                return 'break'
            entry.bind('<KeyPress>', pressed)
        for column, heading in enumerate(('Thao tác', 'Phạm vi', 'Phím / tổ hợp', '')):
            ttk.Label(rows, text=heading, font=('Segoe UI', 9, 'bold')).grid(row=0, column=column, sticky='w', pady=6)
        for index, (name, (label, default, scope)) in enumerate(SHORTCUT_ACTIONS.items(), start=1):
            ttk.Label(rows, text=label, wraplength=300).grid(row=index, column=0, sticky='w', pady=5)
            if name in scopes and name != 'stop_record':
                ttk.Combobox(rows, textvariable=scopes[name], values=('Trong ứng dụng', 'Toàn cục'),
                             state='readonly', width=15).grid(row=index, column=1, padx=8)
            else:
                ttk.Label(rows, text='Hộp thoại' if scope == 'dialog' else 'Toàn cục').grid(row=index, column=1, padx=8)
            entry = ttk.Entry(rows, textvariable=variables[name], width=20)
            entry.grid(row=index, column=2, padx=4, sticky='ew')
            entries[name] = entry
            ttk.Button(rows, text='Ghi phím', width=9, command=lambda e=entry, v=variables[name]: capture(e, v)).grid(row=index, column=3, padx=4)
        rows.columnconfigure(0, weight=1)
        tray_var = tk.BooleanVar(value=self.manager.minimize_to_tray_on_close)
        ttk.Checkbutton(panel, text='Thu nhỏ xuống khay khi bấm đóng [X]', variable=tray_var).pack(anchor='w')
        def save():
            values = {name: value.get().strip() for name, value in variables.items()}
            previous = (self.manager.hotkey_record_str, self.manager.hotkey_panic_str,
                        dict(self.manager.button_hotkeys), dict(self.manager.button_hotkey_scopes),
                        self.manager.minimize_to_tray_on_close)
            try:
                if self.manager.state != MacroManager.STATE_IDLE:
                    raise ValueError('Hãy dừng ghi / chạy trước khi lưu cài đặt.')
                for name, text in values.items():
                    if text and (SHORTCUT_ACTIONS[name][2] == 'dialog' or
                            name in scopes and scopes[name].get() == 'Trong ứng dụng'):
                        sequence = tk_sequence(text)
                        try:
                            binding = win.bind(sequence, lambda event: None, add='+')
                            win.unbind(sequence, binding)
                        except tk.TclError as error:
                            raise ValueError(f'{SHORTCUT_ACTIONS[name][0]}: phím này chưa được hỗ trợ trong cửa sổ ứng dụng.') from error
                self.manager.apply_shortcuts(values, {name: 'global' if value.get() == 'Toàn cục' else 'app' for name, value in scopes.items()})
                self.manager.minimize_to_tray_on_close = tray_var.get()
                self.manager.save_library()
            except (ValueError, OSError) as error:
                (self.manager.hotkey_record_str, self.manager.hotkey_panic_str,
                 self.manager.button_hotkeys, self.manager.button_hotkey_scopes,
                 self.manager.minimize_to_tray_on_close) = previous
                messagebox.showerror('Không thể lưu phím tắt', str(error), parent=win)
                return
            self._install_shortcuts()
            self.btn_rec.set_text(f'HỌC · {self.manager.hotkey_record_str}')
            self.btn_panic.set_text(f'DỪNG KHẨN CẤP · {self.manager.hotkey_panic_str}')
            win.destroy()
            self._load_active_profile_ui()
            self._handle_state_ui(self.manager.state)
            self.notify_windows('Đã lưu cài đặt', 'Phím tắt của các nút đã được áp dụng.')
        buttons = win.footer
        def reset():
            for name, (_, default, _) in SHORTCUT_ACTIONS.items():
                variables[name].set(default)
            for name, value in scopes.items():
                value.set('Toàn cục' if name in ('show', 'stop_record') else 'Trong ứng dụng')
        ttk.Button(buttons, text='Khôi phục phím mặc định', command=reset).pack(side=tk.LEFT)
        ttk.Button(buttons, text='Lưu cài đặt', style='Primary.TButton', command=save).pack(side=tk.RIGHT)
        ttk.Button(buttons, text='Hủy', command=win.destroy).pack(side=tk.RIGHT, padx=8)
        self._register_shortcut_dialog(win, {'dialog_save': save, 'dialog_cancel': win.destroy,
            'toggle_tray': lambda: tray_var.set(not tray_var.get()), 'restore_shortcuts': reset})

    # ==========================================
    # QUẢN LÝ BỘ THẺ KỊCH BẢN (SCRIPT DECK)
    # ==========================================
    def _refresh_profile_deck(self):
        active = self.manager.get_active_profile()
        self.profile_choice.configure(values=[f'{p.name}  ·  {p.hotkey or "chưa gán phím"}' for p in self.manager.profiles])
        if active:
            self.profile_choice.current(self.manager.profiles.index(active))
        self._load_active_profile_ui()

    def _select_profile(self, profile_id: str):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        self.manager.set_active_profile(profile_id)
        self._refresh_profile_deck()

    def _load_active_profile_ui(self):
        """Nạp dữ liệu của profile đang chọn lên bảng."""
        active = self.manager.get_active_profile()
        if not active:
            return
        if active.id != self._preview_profile:
            self._preview_start = 0
            self._preview_profile = active.id
        self.btn_play.set_text(f"CHẠY · {active.hotkey or 'nút chạy'}")
        self.btn_rec.set_text(f"HỌC · {self.manager.hotkey_record_str}")
        self.btn_stop.set_text(f"DỪNG · {self.manager.button_hotkeys.get('stop_record') or self.manager.hotkey_record_str}")
        self.btn_panic.set_text(f'DỪNG KHẨN CẤP · {self.manager.hotkey_panic_str}')
        self.workflow_hint.set(f'{self.manager.hotkey_record_str} → đợi 3 giây → thao tác → [{self.manager.button_hotkeys.get("stop_record") or self.manager.hotkey_record_str}] dừng')
        self.speed_var.set(f"{active.speed:g}x")
        self.speed_slider.set(active.speed)
        self.speed_readout.configure(text=f"{active.speed:g}×")
        self.loop_count_var.set(str(active.loop_count))
        self.loop_delay_var.set(str(active.loop_delay))
        self._refresh_action_tree()
        if self.manager.state == MacroManager.STATE_IDLE:
            self._set_hud(self._idle_status(), BTN_GREEN_TXT)

    def _idle_status(self):
        active = self.manager.get_active_profile()
        name = active.name if active else 'Chọn kịch bản'
        stop = self.manager.button_hotkeys.get('stop_record') or self.manager.hotkey_record_str
        return f'SẴN SÀNG · {name} · HỌC [{self.manager.hotkey_record_str}] · DỪNG HỌC [{stop}]'

    def _cmd_add_profile(self):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        """Thêm kịch bản mới."""
        name = simpledialog.askstring("TẠO KỊCH BẢN MỚI", "Nhập tên kịch bản mới:", parent=self.root)
        if not name or not name.strip():
            return
        hotkey = simpledialog.askstring("GÁN PHÍM TẮT", f"Nhập tổ hợp phím kích hoạt cho '{name}' (VD: F9, F10, Ctrl+F1):", initialvalue="F10", parent=self.root)
        if hotkey is None:
            return

        new_profile = ScriptProfile(
            name=name.strip(),
            hotkey=hotkey.strip().upper(),
            actions=[],
            speed=1.0,
            loop_count=1,
            loop_delay=1.0,
        )
        try:
            validate_shortcuts(self.manager.shortcut_values(), self.manager.profiles + [new_profile], self.manager.button_hotkey_scopes)
        except ValueError as error:
            messagebox.showerror('Không thể gán phím', str(error), parent=self.root)
            return
        self.manager.profiles.append(new_profile)
        self.manager.set_active_profile(new_profile.id)
        self.manager.save_library()
        self.manager.reload_global_hotkeys()
        self._refresh_profile_deck()
        self.notify_windows("Đã tạo kịch bản mới", f"Kịch bản '{name}' đã gán phím tắt [{hotkey.strip().upper()}].")

    def _cmd_quick_edit_profile(self, profile_id: str):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        for p in self.manager.profiles:
            if p.id == profile_id:
                new_name = simpledialog.askstring("ĐỔI TÊN KỊCH BẢN", "Tên kịch bản:", initialvalue=p.name, parent=self.root)
                if new_name is None:
                    return
                new_name = new_name.strip() if new_name.strip() else p.name
                new_hk = simpledialog.askstring("ĐỔI PHÍM TẮT", f"Phím tắt cho '{new_name}' (để trống để bỏ gán):", initialvalue=p.hotkey, parent=self.root)
                new_hk = p.hotkey if new_hk is None else new_hk.strip().upper()
                candidate = ScriptProfile(name=new_name, hotkey=new_hk)
                try:
                    validate_shortcuts(self.manager.shortcut_values(),
                        [candidate if item is p else item for item in self.manager.profiles], self.manager.button_hotkey_scopes)
                except ValueError as error:
                    messagebox.showerror('Không thể gán phím', str(error), parent=self.root)
                    return
                p.name, p.hotkey = new_name, new_hk

                self.manager.save_library()
                self.manager.reload_global_hotkeys()
                self._refresh_profile_deck()
                break

    def _cmd_delete_active_profile(self):
        """Xóa kịch bản hiện đang được chọn từ thanh điều khiển Deck."""
        active = self.manager.get_active_profile()
        if active:
            self._cmd_delete_profile(active.id)

    def _cmd_delete_profile(self, profile_id: str):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        """Xóa kịch bản với kiểm tra an toàn và thông báo Windows Toast."""
        if len(self.manager.profiles) <= 1:
            messagebox.showwarning(
                "Không thể xóa",
                "Không thể xóa kịch bản duy nhất còn lại!\nThư viện cần có ít nhất 1 kịch bản để hoạt động.",
                parent=self.root,
            )
            return

        target = next((p for p in self.manager.profiles if p.id == profile_id), None)
        if not target:
            return

        confirm = messagebox.askyesno(
            "Xác nhận xóa kịch bản",
            f"Bạn có chắc chắn muốn xóa kịch bản:\n\n"
            f"• Tên: '{target.name}'\n"
            f"• Phím tắt: [{target.hotkey}]\n"
            f"• Số bước: {len(target.actions)} thao tác\n\n"
            f"Thao tác này sẽ xóa vĩnh viễn kịch bản khỏi thư viện!",
            parent=self.root,
        )
        if not confirm:
            return

        deleted_name = target.name
        if self.manager.delete_profile(profile_id):
            self._refresh_profile_deck()
            self.notify_windows(
                "🗑️ Đã xóa kịch bản",
                f"Đã xóa kịch bản '{deleted_name}' khỏi thư viện.",
            )

    # ==========================================
    # SAO CHÉP & DÁN KỊCH BẢN QUA CLIPBOARD (GỬI QUA MÁY KHÁC)
    # ==========================================
    def _cmd_copy_script(self):
        """Sao chép mã kịch bản vào Clipboard để gửi qua máy tính khác."""
        active = self.manager.get_active_profile()
        if not active or not active.actions:
            messagebox.showwarning("Cảnh báo", "Kịch bản hiện tại chưa có thao tác nào để sao chép!")
            return

        exported_str = MacroStorage.export_profile_to_string(active)

        self.root.clipboard_clear()
        self.root.clipboard_append(exported_str)

        self.notify_windows(
            "📋 Đã sao chép kịch bản",
            f"Đã copy mã kịch bản '{active.name}' ({len(active.actions)} bước). Bạn có thể dán (Paste) gửi qua Zalo / email sang máy khác!"
        )
        messagebox.showinfo(
            "Đã sao chép thành công",
            f"Đã sao chép toàn bộ kịch bản '{active.name}' vào bộ nhớ tạm!\n\n"
            f"Bạn có thể dán (Ctrl+V) gửi nội dung này qua Zalo, Messenger hoặc email sang máy tính khác.\n"
            f"Ở máy tính kia, chỉ cần mở Học Vẹt và bấm nút '📥 DÁN KỊCH BẢN' là chạy được ngay!"
        )

    def _cmd_paste_script(self):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        """Nhập kịch bản từ Clipboard được sao chép từ máy tính khác."""
        try:
            clipboard_text = self.root.clipboard_get()
        except Exception:
            messagebox.showwarning("Lỗi", "Bộ nhớ tạm (Clipboard) đang trống!")
            return

        imported_profile = MacroStorage.import_profile_from_string(clipboard_text)
        if not imported_profile:
            messagebox.showerror(
                "Lỗi định dạng",
                "Nội dung trong bộ nhớ tạm không phải là mã kịch bản của Học Vẹt!\n\n"
                "Hãy sao chép lại mã kịch bản bằng nút '📋 SAO CHÉP MÃ' từ máy gốc."
            )
            return

        # Hỏi xác nhận thêm kịch bản
        msg = f"Tìm thấy kịch bản: '{imported_profile.name}'\n" \
              f"- Số thao tác: {len(imported_profile.actions)} bước\n" \
              f"- Phím tắt đề xuất: [{imported_profile.hotkey}]\n\n" \
              f"Bạn có muốn thêm kịch bản này vào thư viện của máy tính này không?"

        if messagebox.askyesno("Xác nhận nhập kịch bản", msg):
            self._accept_import(imported_profile)

    # ==========================================
    # LOGIC ĐIỀU KHIỂN & CẬP NHẬT TRẠNG THÁI
    # ==========================================
    def _set_speed(self, spd_text: str):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        self.speed_var.set(spd_text)
        self.speed_slider.set(self._parse_speed())
        self.speed_readout.configure(text=f'{self._parse_speed():g}×')
        active = self.manager.get_active_profile()
        if active:
            active.speed = self._parse_speed()
            self.manager.save_library()

        for k, btn in self.speed_buttons.items():
            is_active = (k == spd_text)
            btn.top_color = BTN_RED_TOP if is_active else BTN_BEIGE_TOP
            btn.bot_color = BTN_RED_BOT if is_active else BTN_BEIGE_BOT
            btn.text_color = BTN_RED_TXT if is_active else BTN_BEIGE_TXT
            btn._draw()

    def _parse_speed(self) -> float:
        raw = self.speed_var.get()
        try:
            return float(raw.replace("x", "").strip())
        except Exception:
            return 1.0

    def _parse_loop_count(self) -> int:
        try:
            return max(0, int(self.loop_count_var.get().strip()))
        except Exception:
            return 1

    def _parse_loop_delay(self) -> float:
        try:
            return max(0.0, float(self.loop_delay_var.get().strip()))
        except Exception:
            return 1.0

    def _toggle_recording(self):
        if self.manager.state in (MacroManager.STATE_RECORDING, MacroManager.STATE_COUNTDOWN):
            self._cmd_stop_recording()
        elif self.manager.state == MacroManager.STATE_IDLE and not self._shortcut_dialogs:
            self._cmd_start_recording(force_countdown=True)

    def _cmd_start_recording(self, force_countdown=False):
        if self.manager.state != MacroManager.STATE_IDLE or self.countdown_timer:
            return
        if force_countdown or self.countdown_var.get():
            self.manager._set_state(MacroManager.STATE_COUNTDOWN)
            self._start_countdown(3)
        else:
            self._do_start_record()

    def _start_countdown(self, seconds_left):
        self.countdown_timer = None
        if self._closing or self.manager.state != MacroManager.STATE_COUNTDOWN:
            return
        if seconds_left > 0:
            self._set_hud(f'Bắt đầu học sau {seconds_left} giây · nhấn phím dừng để hủy', BTN_RED_BOT)
            self.record_notice.show('Sắp bắt đầu học thao tác', 'Chuyển sang phần mềm cần thao tác. Phím dừng có thể hủy đếm ngược.', number=seconds_left)
            self.countdown_timer = self.root.after(1000, lambda: self._start_countdown(seconds_left-1))
        else:
            self._do_start_record()

    def _do_start_record(self):
        if self.manager.state not in (MacroManager.STATE_IDLE, MacroManager.STATE_COUNTDOWN):
            return
        self._recorded_count = self._rendered_record_count = 0
        self._clear_tree()
        self.lbl_stats.configure(text='Đang học · 0 thao tác')
        self.manager.start_recording(record_movement=not self.ignore_movement_var.get())
        active = self.manager.get_active_profile()
        stop = self.manager.button_hotkeys.get('stop_record') or self.manager.hotkey_record_str
        name = active.name if active else 'Kịch bản'
        self.record_notice.show('ĐANG HỌC THAO TÁC', f'{name} · Nhấn [{stop}] để dừng và lưu.', duration=3500)
        self.notify_windows('Bắt đầu học thao tác', f'{name} · Nhấn [{stop}] để dừng và lưu.')

    def _cancel_countdown(self):
        if self.countdown_timer:
            self.root.after_cancel(self.countdown_timer)
            self.countdown_timer = None
        if self.manager.state == MacroManager.STATE_COUNTDOWN:
            self.manager._set_state(MacroManager.STATE_IDLE)
            self.record_notice.show('Đã hủy đếm ngược', 'Chưa ghi hoặc thay đổi kịch bản nào.', duration=2500)
            return True
        return False

    def _cmd_stop_recording(self):
        if self._cancel_countdown():
            return
        if self.manager.state != MacroManager.STATE_RECORDING:
            return
        self.manager.stop_recording()

    def _record_saved(self, profile, count):
        name = profile.name if profile else 'Kịch bản'
        self._refresh_profile_deck()
        self.record_notice.show('ĐÃ DỪNG & LƯU THÀNH CÔNG', f'{name} · {count:,} thao tác. Nút / phím dừng không được ghi.', duration=4500)
        self.notify_windows('Đã dừng học và lưu', f'{name} · Đã lưu {count:,} thao tác.')

    def _cmd_start_playing(self):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        active = self.manager.get_active_profile()
        if not active or not active.actions:
            messagebox.showwarning("Chưa có thao tác", f"Nhấn [{self.manager.hotkey_record_str}] để học hoặc nhập file kịch bản.")
            return
        active.speed = self._parse_speed()
        active.loop_count = self._parse_loop_count()
        active.loop_delay = self._parse_loop_delay()
        self.manager.start_playing_profile(active)

        # THÔNG BÁO WINDOWS KHI BẮT ĐẦU CHẠY
        self.notify_windows(
            "▶ Bắt đầu chạy kịch bản",
            f"Đang tự động thực hiện '{active.name}' ({len(active.actions)} bước)... Nhấn [{self.manager.hotkey_panic_str}] để dừng khẩn cấp."
        )

    def _cmd_emergency_stop(self):
        if self._cancel_countdown():
            return
        self.manager.stop_playing()
        self.notify_windows('Đã dừng thao tác', 'Mọi thao tác tự động đã được dừng.')

    def _set_hud(self, text: str, fg: str):
        self.status_banner.configure(text=text, fg=fg)
        self.root.title(f"Học Vẹt — {text[:90]}")

    def _on_manager_state_changed(self, new_state: str):
        self._post(self._handle_state_ui, new_state)

    def _on_profile_triggered(self, profile: ScriptProfile):
        """Được gọi khi người dùng bấm phím tắt của một kịch bản từ bất kỳ đâu."""
        self._post(self._refresh_profile_deck)
        # THÔNG BÁO WINDOWS KHI CHẠY TỪ PHÍM TẮT TOÀN CỤC
        self.notify_windows(
            f"▶ Kích hoạt '{profile.name}'",
            f"Đang tự động thực hiện kịch bản [{profile.hotkey}]..."
        )

    def _handle_state_ui(self, state: str):
        active = self.manager.get_active_profile()
        p_name = active.name if active else "Mặc định"
        p_hk = active.hotkey if active else "F9"

        self.status_banner.configure(bg={MacroManager.STATE_IDLE: '#e2f4e5',
                                         MacroManager.STATE_RECORDING: '#ffe3e3',
                                         MacroManager.STATE_PLAYING: '#dfeeff',
                                         MacroManager.STATE_COUNTDOWN: '#f3e5bf'}[state])
        if state == MacroManager.STATE_IDLE:
            self._set_hud(
                self._idle_status(),
                fg=BTN_GREEN_TXT,
            )
            self.btn_rec.configure_state("normal")
            self.btn_stop.configure_state("disabled")
            self.btn_play.configure_state("normal")

        elif state == MacroManager.STATE_COUNTDOWN:
            self.btn_rec.configure_state('disabled')
            self.btn_play.configure_state('disabled')
            self.btn_stop.configure_state('normal')
        elif state == MacroManager.STATE_RECORDING:
            self._set_hud(
                f"ĐANG HỌC · {p_name} · Nhấn [{self.manager.button_hotkeys.get('stop_record') or self.manager.hotkey_record_str}] để dừng và lưu",
                fg=BTN_RED_BOT,
            )
            self.btn_rec.configure_state("disabled")
            self.btn_stop.configure_state("normal")
            self.btn_play.configure_state("disabled")

        elif state == MacroManager.STATE_PLAYING:
            self._set_hud(
                f"🔵 [CHẠY] ĐANG THỰC HIỆN KỊCH BẢN '{p_name}'... NHẤN [{self.manager.hotkey_panic_str}] ĐỂ DỪNG NGAY!",
                fg=BTN_BLUE_TXT,
            )
            self.btn_rec.configure_state("disabled")
            self.btn_stop.configure_state("disabled")
            self.btn_play.configure_state("disabled")

    def _on_action_recorded(self, action: MacroAction, count: int):
        self._recorded_count = count

    def _on_player_step(self, step: int, total: int, cur_loop: int, total_loops: int):
        self._pending_progress = (step, total, cur_loop, total_loops)

    def _draw_player_step(self, step, total, cur_loop, total_loops):
        active = self.manager.get_active_profile()
        p_name = active.name if active else ""
        loop_str = f"VÒNG {cur_loop}/{total_loops}" if total_loops > 0 else f"VÒNG {cur_loop} (VÔ HẠN)"
        txt = f"🔵 [CHẠY '{p_name}'] {loop_str} ── BƯỚC {step:02d}/{total:02d} │ NHẤN [{self.manager.hotkey_panic_str}] ĐỂ DỪNG"
        self._set_hud(txt, fg=BTN_BLUE_TXT)

    def _on_player_finished(self, success: bool, aborted: bool):
        self._pending_progress = None
        active = self.manager.get_active_profile()
        p_name = active.name if active else ""
        if self.manager.player.last_error:
            error = self.manager.player.last_error
            self.root.after(0, lambda: self._set_hud(f'LỖI: {error}', BTN_RED_BOT))
            self.root.after(0, lambda: messagebox.showerror('Kịch bản đã dừng', error, parent=self.root))
            return
        if aborted:
            msg = f"ĐÃ DỪNG KHẨN CẤP '{p_name}' THEO LỆNH ({self.manager.hotkey_panic_str})"
            self.root.after(0, lambda: self._set_hud(f"⚠️ {msg}", fg=BTN_YELLOW_TXT))
            self.notify_windows("🛑 Đã dừng khẩn cấp", f"Kịch bản '{p_name}' đã dừng theo lệnh người dùng.")
        else:
            msg = f"HOÀN TẤT KỊCH BẢN '{p_name}' THÀNH CÔNG!"
            self.root.after(0, lambda: self._set_hud(f"⭐ {msg}", fg=BTN_GREEN_TXT))
            # THÔNG BÁO WINDOWS KHI HOÀN TẤT CHẠY
            self.notify_windows("⭐ Hoàn thành xuất sắc", f"Đã thực hiện xong toàn bộ kịch bản '{p_name}'!")

    # ==========================================
    # QUẢN LÝ BẢNG KỊCH BẢN (TREEVIEW)
    # ==========================================
    def _format_action_display(self, action: MacroAction):
        act_type = action.action_type
        if act_type == "mouse_click":
            st = "Nhấn" if action.pressed else "Nhả"
            btn = (action.button or "left").upper()
            t_name = f"Chuột {btn} ({st})"
            detail = f"Tọa độ: X={action.x}, Y={action.y}"
        elif act_type == "mouse_move":
            t_name = "Di chuột"
            detail = f"Tọa độ: X={action.x}, Y={action.y}"
        elif act_type == "mouse_scroll":
            t_name = "Cuộn chuột"
            detail = f"Tại ({action.x}, {action.y}) | Cuộn: {action.dy}"
        elif act_type == 'wait_window':
            t_name = 'Chờ cửa sổ'
            detail = f'{action.window_title} | Tối đa {action.timeout:g}s (cửa sổ phía trước)'
        elif act_type == 'wait_image':
            t_name = 'Chờ ảnh / nút'
            detail = f'Vùng ({action.x}, {action.y}) | Tối đa {action.timeout:g}s | Sai số {action.tolerance:.0%}'
        elif act_type == "key_press":
            t_name = "Nhấn phím"
            detail = f"Phím: [{action.key}]"
        elif act_type == "key_release":
            t_name = "Nhả phím"
            detail = f"Phím: [{action.key}]"
        else:
            t_name = act_type.upper()
            detail = str(action.to_dict())

        delay_str = f"{action.delay:.3f}s"
        return t_name, detail, delay_str

    def _clear_tree(self):
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        self._update_stats()

    def _refresh_action_tree(self):
        self._clear_tree()
        active = self.manager.get_active_profile()
        if not active:
            return
        start = min(self._preview_start, max(0, (len(active.actions)-1)//1000*1000))
        self._preview_start = start
        end = min(start+1000, len(active.actions))
        self.preview_label.configure(text=f'{start+1 if active.actions else 0}–{end} / {len(active.actions):,} bước')
        self.prev_page.configure(state='normal' if start else 'disabled')
        self.next_page.configure(state='normal' if end < len(active.actions) else 'disabled')
        for index in range(start, end):
            t_name, detail, delay_str = self._format_action_display(active.actions[index])
            self.tree.insert('', tk.END, iid=str(index), values=(f'{index+1:02d}', delay_str, t_name, detail))
        self._update_stats()

    def _update_stats(self):
        active = self.manager.get_active_profile()
        actions = active.actions if active else []
        total = len(actions)
        total_time = sum(act.delay for act in actions)
        self.lbl_stats.configure(text=f"[ THAO TÁC: {total:03d} ]   [ TỔNG THỜI GIAN: {total_time:.2f}s ]")

    def _cmd_delete_selected_action(self):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        active = self.manager.get_active_profile()
        if not active:
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("THÔNG BÁO", "Hãy chọn một dòng trong bảng để xóa!")
            return
        idx = int(selected[0])
        if 0 <= idx < len(active.actions):
            del active.actions[idx]
            self.manager.save_library()
            self._refresh_action_tree()
            self._refresh_profile_deck()

    def _cmd_edit_delay(self):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        active = self.manager.get_active_profile()
        if not active:
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("THÔNG BÁO", "Hãy chọn một dòng trong bảng để sửa thời gian chờ!")
            return
        idx = int(selected[0])
        action = active.actions[idx]

        new_val = simpledialog.askfloat(
            "SỬA ĐỘ TRỄ",
            f"Nhập thời gian chờ trước bước #{idx + 1} (giây):",
            initialvalue=action.delay,
            minvalue=0.0,
            maxvalue=300.0,
        )
        if new_val is not None:
            action.delay = round(new_val, 4)
            self.manager.save_library()
            self._refresh_action_tree()

    def _cmd_clear_actions(self):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        active = self.manager.get_active_profile()
        if not active or not active.actions:
            return
        if messagebox.askyesno("XÁC NHẬN", f"Bạn có chắc muốn xóa tất cả thao tác của '{active.name}'?"):
            active.actions = []
            self.manager.save_library()
            self._refresh_action_tree()
            self._refresh_profile_deck()

            # THÔNG BÁO WINDOWS KHI XÓA SẠCH BƯỚC
            self.notify_windows(
                "🗑 Đã xóa sạch thao tác",
                f"Đã xóa toàn bộ các bước của kịch bản '{active.name}'."
            )

    def _cmd_save_file(self):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        active = self.manager.get_active_profile()
        if not active:
            return
        filename = ''.join(c for c in active.name if c not in '<>:"/\\|?*').strip() or 'kich_ban'
        path = filedialog.asksaveasfilename(parent=self.root, title='Xuất một kịch bản để chia sẻ',
                defaultextension='.hocvet', initialfile=filename + '.hocvet',
                filetypes=[('Kịch bản nén Học Vẹt', '*.hocvet'), ('JSON', '*.json')])
        if path:
            try:
                MacroStorage.export_profile(active, path)
                messagebox.showinfo('Đã xuất kịch bản', 'Gửi file này cho người khác. Trên máy nhận, chọn NHẬP FILE. Ảnh mẫu đã nằm trong file.', parent=self.root)
            except Exception as error:
                messagebox.showerror('Không thể xuất', str(error), parent=self.root)

    def _cmd_load_file(self):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        path = filedialog.askopenfilename(parent=self.root, title='Nhập kịch bản được chia sẻ',
                filetypes=[('Kịch bản Học Vẹt / JSON', '*.hocvet *.json'), ('Tất cả', '*.*')])
        if path:
            try:
                self._accept_import(MacroStorage.import_profile(path))
            except Exception as error:
                messagebox.showerror('Không thể nhập', str(error), parent=self.root)

    def _accept_import(self, profile):
        if self.manager.state != MacroManager.STATE_IDLE:
            messagebox.showinfo('Chưa thể nhập', 'Hãy dừng ghi / chạy rồi nhập lại file.', parent=self.root)
            return
        # Phím tắt trùng được bỏ gán; không để một file nhập thay kịch bản đang có.
        used = {normalize_hotkey(p.hotkey) for p in self.manager.profiles}
        used.update(normalize_hotkey(value) for name, value in self.manager.button_hotkeys.items()
                    if value and SHORTCUT_ACTIONS[name][2] != 'dialog')
        if normalize_hotkey(profile.hotkey) in used or normalize_hotkey(profile.hotkey) in {
                normalize_hotkey(self.manager.hotkey_record_str), normalize_hotkey(self.manager.hotkey_panic_str)}:
            profile.hotkey = ''
        try:
            validate_shortcuts(self.manager.shortcut_values(), self.manager.profiles + [profile], self.manager.button_hotkey_scopes)
        except ValueError:
            profile.hotkey = ''
        self.manager.profiles.append(profile)
        self.manager.set_active_profile(profile.id)
        self.manager.save_library()
        self.manager.reload_global_hotkeys()
        self._refresh_profile_deck()
        messagebox.showinfo('Đã nhập kịch bản', f"Đã thêm '{profile.name}' ({len(profile.actions)} bước).\nKiểm tra tọa độ, ảnh và gán lại phím tắt nếu cần trước khi chạy.", parent=self.root)

    def _cmd_help(self):
        win = self._new_dialog('Hướng dẫn sử dụng',
            'Học thao tác, chia sẻ kịch bản và chạy theo điều kiện.', size=(760, 620), modal=False)
        text = tk.Text(win.body, wrap='word', padx=16, pady=14, font=FONT_BODY,
                       bg=VINTAGE_CARD_BG, fg=VINTAGE_TEXT_BODY, relief='flat', borderwidth=0)
        bar = ttk.Scrollbar(win.body, command=text.yview)
        bar.pack(side=tk.RIGHT, fill=tk.Y)
        text.configure(yscrollcommand=bar.set)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert('1.0', f"""HỌC VẸT — HƯỚNG DẪN

1. Tạo / chọn kịch bản. Nhấn {self.manager.hotkey_record_str}, chờ thông báo đếm ngược 3–2–1 và ĐANG HỌC rồi thực hiện thao tác. Nhấn lại hoặc phím Dừng học đã gán để lưu; thông báo xác nhận xuất hiện cả khi chạy nền. Nhấn {self.manager.hotkey_panic_str} để dừng khẩn cấp.
2. Chọn CHẠY hoặc dùng phím tắt của kịch bản. Thanh trạng thái luôn hiện ở cuối cửa sổ: ĐANG GHI, ĐANG CHẠY, ĐANG CHỜ hoặc lỗi.
3. Mở Chi tiết / sửa bước rồi chọn một bước trong bảng, bấm + Chờ cửa sổ hoặc + Chờ ảnh / nút để chèn điều kiện TRƯỚC bước đó. Không chọn dòng sẽ thêm ở cuối. Sửa điều kiện để đổi thời hạn / ảnh. Hết hạn thì kịch bản dừng, không bấm tiếp.
4. Chờ cửa sổ: nhập một phần tên trên thanh tiêu đề. Chỉ tiếp tục khi cửa sổ đó ở phía trước.
5. Chờ ảnh: bấm Chụp vùng, chuyển sang ứng dụng đích rồi kéo chọn riêng nút / vùng ổn định. Esc để hủy. Ảnh được so sánh ở đúng vị trí đã chụp; tối đa 2% pixel được khác (bỏ qua chênh lệch màu nhỏ). Có thể điều chỉnh sai số khi sửa điều kiện. Giữ cùng vị trí cửa sổ, giao diện, độ phân giải và DPI khi chia sẻ kịch bản.
6. XUẤT FILE ({self.manager.button_hotkeys.get('export_file') or 'chưa gán'}) tạo một file .hocvet nén, gồm cài đặt, các bước và ảnh mẫu. Gửi file này; người nhận dùng NHẬP FILE ({self.manager.button_hotkeys.get('import_file') or 'chưa gán'}). Nhập sẽ thêm kịch bản mới, không ghi đè kịch bản đang có. Phím tắt trùng được bỏ gán để bạn đặt lại.
7. Dữ liệu tự lưu tại:
{self.manager.library_path}
Cập nhật / thay file ứng dụng không xóa thư viện. File .bak giữ lần lưu trước. Muốn chuyển máy, dùng Xuất file cho từng kịch bản hoặc sao lưu cả thư mục dữ liệu. Dữ liệu cũ cạnh ứng dụng được chuyển ở lần đầu chạy bản mới.
8. Tiếng Việt: giữ cùng bộ gõ Unicode, Telex/VNI và Caps Lock khi học / chạy. Kịch bản cũ bị lặp dấu cần học lại.
9. Dùng Tab để chọn nút, Enter / Space để kích hoạt; {self.manager.button_hotkeys.get('help') or 'Nút Hướng dẫn'} mở hướng dẫn. Vào Cài đặt để gán phím cho từng nút, chọn Trong ứng dụng / Toàn cục. Các phím Lưu, Hủy, Chụp ảnh chỉ dùng trong hộp thoại tương ứng. Cửa sổ nhỏ có thanh cuộn dọc và ngang.

Kịch bản có thể chứa thông tin đã gõ và ảnh chụp màn hình; kiểm tra nội dung trước khi chia sẻ.
""")
        text.configure(state='disabled')
        ttk.Button(win.footer, text='Đóng', command=win.destroy).pack(side=tk.RIGHT)
        self._register_shortcut_dialog(win, {'dialog_cancel': win.destroy})

    def _cmd_add_condition(self, kind, existing=None):
        if self.manager.state != MacroManager.STATE_IDLE:
            return
        active = self.manager.get_active_profile()
        if not active:
            return
        selected = self.tree.selection()
        index = int(selected[0]) if selected else len(active.actions)
        win = self._new_dialog(
            'Chờ cửa sổ phía trước' if kind == 'wait_window' else 'Chờ ảnh / nút xuất hiện',
            'Chèn trước bước đã chọn. Hết thời hạn sẽ dừng kịch bản.', size=(720, 450))
        box = win.body
        title = tk.StringVar(value=existing.window_title if existing else '')
        timeout = tk.StringVar(value=str(existing.timeout if existing else 30))
        tolerance = tk.StringVar(value=str(round(existing.tolerance * 100, 2) if existing else 2))
        reference = [existing.image, existing.x, existing.y] if existing else [None, None, None]
        if kind == 'wait_window':
            ttk.Label(box, text='Một phần tên cửa sổ:').pack(anchor='w', pady=(10, 0))
            ttk.Entry(box, textvariable=title, width=55).pack(fill=tk.X)
        else:
            ttk.Label(box, text='Ảnh phải ở cùng vị trí và DPI khi chạy. Chọn vùng nhỏ, tránh đồng hồ / con trỏ.').pack(anchor='w', pady=8)
            summary = ttk.Label(box, text='Đã có ảnh mẫu' if reference[0] else 'Chưa chọn ảnh mẫu')
            summary.pack(anchor='w')
            def capture():
                win.grab_release()
                win.withdraw()
                self.root.withdraw()
                def complete(result):
                    self.root.deiconify()
                    win.deiconify()
                    win.grab_set()
                    if result:
                        reference[:] = [result[2], result[0], result[1]]
                        summary.configure(text=f'Đã chụp ảnh tại ({result[0]}, {result[1]})')
                def start_capture():
                    try:
                        capture_region(self.root, complete)
                    except Exception as error:
                        complete(None)
                        messagebox.showerror('Không thể chụp', str(error), parent=win)
                self.root.after(3000, start_capture)
            ttk.Button(box, text='Chụp vùng ảnh / nút sau 3 giây', style='Info.TButton', command=capture).pack(anchor='w', pady=8)
            ttk.Label(box, text='Sai số pixel cho phép (0–20%):').pack(anchor='w')
            ttk.Entry(box, textvariable=tolerance).pack(fill=tk.X)
        ttk.Label(box, text='Thời hạn chờ (giây, tối đa 3600):').pack(anchor='w', pady=(10, 0))
        ttk.Entry(box, textvariable=timeout).pack(fill=tk.X)
        def save():
            try:
                if self.manager.state != MacroManager.STATE_IDLE:
                    raise ValueError('Hãy dừng ghi / chạy trước khi sửa kịch bản.')
                action = MacroAction(kind, delay=existing.delay if existing else 0,
                    window_title=title.get().strip() if kind == 'wait_window' else None,
                    image=reference[0], x=reference[1], y=reference[2],
                    timeout=float(timeout.get()), tolerance=float(tolerance.get())/100)
                MacroStorage.validate_profile(ScriptProfile(actions=[action]))
                if existing:
                    active.actions[index] = action
                else:
                    active.actions.insert(index, action)
                self.manager.save_library()
                self._refresh_action_tree()
                self._refresh_profile_deck()
                win.destroy()
            except Exception as error:
                messagebox.showerror('Không thể lưu điều kiện', str(error), parent=win)
        ttk.Button(win.footer, text='Lưu điều kiện', style='Primary.TButton', command=save).pack(side=tk.RIGHT, pady=(14, 0))
        ttk.Button(win.footer, text='Hủy', command=win.destroy).pack(side=tk.RIGHT, padx=8, pady=(14, 0))
        commands = {'dialog_save': save, 'dialog_cancel': win.destroy}
        if kind == 'wait_image':
            commands['capture'] = capture
        self._register_shortcut_dialog(win, commands)

    def _cmd_edit_condition(self):
        selected = self.tree.selection()
        active = self.manager.get_active_profile()
        if selected and active:
            action = active.actions[int(selected[0])]
            if action.action_type in ('wait_window', 'wait_image'):
                self._cmd_add_condition(action.action_type, action)
                return
        messagebox.showinfo('Sửa điều kiện', 'Chọn một bước chờ trong bảng trước.', parent=self.root)


def run_app():
    enable_dpi_awareness()
    root = tk.Tk()
    apply_theme(root, root.winfo_fpixels('1i') / 96)
    try:
        app = HocVetApp(root)
    except (OSError, ValueError, TypeError) as error:
        root.withdraw()
        messagebox.showerror('Không thể mở dữ liệu Học Vẹt',
            f'Không thể đọc thư viện hoặc bản dự phòng. Dữ liệu được giữ nguyên.\n\n{error}', parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    run_app()
