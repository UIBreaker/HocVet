"""
Học Vẹt - Core Engine
Tác giả: Nhật Nam (GitHub: @UIBreaker)
Chịu trách nhiệm:
- Ghi và phát lại chuột/bàn phím (DPI Awareness, Emergency Stop).
- Hỗ trợ đa kịch bản (Multi-Script Profiles) với tổ hợp phím riêng cho từng kịch bản.
- Bộ lắng nghe phím tắt toàn cục động (Dynamic GlobalHotKeys).
- Quản lý thư viện kịch bản, sao chép chia sẻ kịch bản qua Clipboard / JSON.
"""

import ctypes
import json
import os
import sys
import time
import threading
import uuid
import winsound
import math
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable

from pynput import mouse, keyboard
from app_info import APP_VERSION
from clipboard_text import set_clipboard_text
from conditions import foreground_window, title_matches, window_at, window_title
from shortcuts import SHORTCUT_ACTIONS, normalize_hotkey, validate_shortcuts, parse_hotkey, key_identity, hotkey_identities


_playback_input = threading.local()


def _check_send_result(result, _function, args):
    if getattr(_playback_input, 'active', False) and result != args[0]:
        raise OSError('Windows chưa xác nhận gửi đủ sự kiện đầu vào.')
    return result


# Pynput bỏ qua số sự kiện SendInput đã gửi, kể cả khi Windows trả về 0.
ctypes.windll.user32.SendInput.errcheck = _check_send_result


def condition_check(action):
    from conditions import condition_check as _cc
    return _cc(action)


def decode_reference(encoded):
    from conditions import decode_reference as _dr
    return _dr(encoded)


# ==========================================
# 1. WINDOWS DPI AWARENESS
# ==========================================
def enable_dpi_awareness():
    """Đảm bảo tọa độ chuột (x, y) trên màn hình Windows không bị lệch tỷ lệ DPI scaling (125%, 150%)."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ==========================================
# 2. AUDIO FEEDBACK (WINDOWS NATIVE)
# ==========================================
def play_sound(sound_type: str):
    """Phát âm thanh thông báo không chặn luồng (non-blocking)."""
    def _beep():
        try:
            if sound_type == "start_record":
                winsound.Beep(1000, 150)
            elif sound_type == "stop_record":
                winsound.Beep(700, 150)
            elif sound_type == "start_play":
                winsound.Beep(1200, 100)
                winsound.Beep(1500, 100)
            elif sound_type == "stop_play":
                winsound.Beep(1200, 200)
            elif sound_type == "emergency_stop":
                winsound.Beep(500, 300)
        except Exception:
            pass
    threading.Thread(target=_beep, daemon=True).start()


# ==========================================
# 3. HELPER CHUYỂN ĐỔI PHÍM & CHUỘT
# ==========================================
def key_to_str(key: Any) -> str:
    """Chuyển đổi đối tượng pynput Key/KeyCode sang chuỗi lưu trữ JSON."""
    if isinstance(key, keyboard.Key):
        return f"Key.{key.name}"
    elif hasattr(key, "vk") and key.vk is not None:
        return f"vk_{key.vk}"
    elif hasattr(key, "char") and key.char is not None:
        return key.char
    return str(key)


def str_to_key(s: str) -> Any:
    """Khôi phục đối tượng phím từ chuỗi JSON."""
    if s.startswith("Key."):
        name = s.split(".", 1)[1]
        return getattr(keyboard.Key, name, None)
    elif s.startswith("vk_"):
        vk = int(s.split("_", 1)[1])
        return keyboard.KeyCode.from_vk(vk)
    return keyboard.KeyCode.from_char(s)


def button_to_str(button: mouse.Button) -> str:
    return button.name if hasattr(button, "name") else str(button)


def str_to_button(s: str) -> mouse.Button:
    return getattr(mouse.Button, s, mouse.Button.left)


# ==========================================
# 4. DATA MODEL CHO MỖI THAO TÁC & KỊCH BẢN
# ==========================================
@dataclass
class MacroAction:
    action_type: str       # 'mouse_click', 'mouse_move', 'mouse_scroll', 'key_press', 'key_release'
    delay: float           # Thời gian chờ so với thao tác trước (giây)
    x: Optional[int] = None
    y: Optional[int] = None
    button: Optional[str] = None     # 'left', 'right', 'middle'
    pressed: Optional[bool] = None   # True = nhấn xuống, False = nhả ra
    dx: Optional[int] = None
    dy: Optional[int] = None
    key: Optional[str] = None        # Tên phím (Key.enter, 'a', ...)
    window_title: Optional[str] = None
    image: Optional[str] = None      # PNG base64 nằm trong kịch bản để chia sẻ cùng file.
    timeout: float = 30.0
    tolerance: float = 0.02
    data_field: Optional[str] = None
    data_label: Optional[str] = None
    data_row: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        # Các trường là giá trị vô hướng; tránh deepcopy từng bước khi lưu kịch bản dài.
        return {k: v for k, v in vars(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MacroAction":
        return cls(
            action_type=data.get("action_type", ""),
            delay=float(data.get("delay", 0.0)),
            x=data.get("x"),
            y=data.get("y"),
            button=data.get("button"),
            pressed=data.get("pressed"),
            dx=data.get("dx"),
            dy=data.get("dy"),
            key=data.get("key"),
            window_title=data.get('window_title'),
            image=data.get('image'),
            timeout=float(data.get('timeout', 30)),
            tolerance=float(data.get('tolerance', 0.02)),
            data_field=data.get('data_field'),
            data_label=data.get('data_label'),
            data_row=data.get('data_row'),
        )


@dataclass
class ScriptProfile:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Kịch bản mới"
    hotkey: str = "F9"
    actions: List[MacroAction] = field(default_factory=list)
    speed: float = 1.0
    loop_count: int = 1
    loop_delay: float = 1.0
    enabled: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "hotkey": self.hotkey,
            "speed": self.speed,
            "loop_count": self.loop_count,
            "loop_delay": self.loop_delay,
            "enabled": self.enabled,
            "description": self.description,
            "total_actions": len(self.actions),
            "actions": [act.to_dict() for act in self.actions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScriptProfile":
        raw_actions = data.get("actions", [])
        actions = [MacroAction.from_dict(item) for item in raw_actions]
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Kịch bản mới"),
            hotkey=data.get("hotkey", "F9"),
            actions=actions,
            speed=float(data.get("speed", 1.0)),
            loop_count=int(data.get("loop_count", 1)),
            loop_delay=float(data.get("loop_delay", 1.0)),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
        )


# ==========================================
# 5. RECORDER: BỘ GHI NHỚ THAO TÁC
# ==========================================
class MacroRecorder:
    def __init__(self, record_movement: bool = False):
        self.record_movement = record_movement
        self.actions: List[MacroAction] = []
        self.is_recording = False
        self._last_time = 0.0
        self._lock = threading.Lock()

        # Listeners
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None

        # Phím điều khiển mặc định
        self.control_hotkeys = ['F8', 'ESC']
        self._control_combinations = [hotkey_identities(text) for text in self.control_hotkeys]
        self.ignore_mouse: Optional[Callable[[int, int], bool]] = None
        self.ignore_keyboard: Optional[Callable[[], bool]] = None
        self._pressed_keys = set()
        self._ignored_releases = set()
        self._own_modifiers = {}
        self._captured_modifiers = set()
        self.ignore_key_event = lambda msg,data:False

        # Callback khi có action mới
        self.on_action_recorded: Optional[Callable[[MacroAction, int], None]] = None

    def _get_delay(self) -> float:
        now = time.perf_counter()
        if self._last_time == 0.0:
            delay = 0.0
        else:
            delay = max(0.001, round(now - self._last_time, 4))
        self._last_time = now
        return delay

    def _add_action(self, action: MacroAction):
        with self._lock:
            if not self.is_recording:
                return
            self.actions.append(action)
            count = len(self.actions)

        if self.on_action_recorded:
            self.on_action_recorded(action, count)

    def _on_mouse_click(self, x: int, y: int, button: mouse.Button, pressed: bool):
        if not self.is_recording:
            return
        if self.ignore_mouse and self.ignore_mouse(x, y):
            return
        delay = self._get_delay()
        action = MacroAction(
            action_type="mouse_click",
            delay=delay,
            x=int(x),
            y=int(y),
            button=button_to_str(button),
            pressed=pressed,
        )
        self._add_action(action)

    def record_field(self, field_id, label, row):
        if self.is_recording:
            self._add_action(MacroAction('copy_field',self._get_delay(),data_field=field_id,data_label=label,data_row=row))

    def record_date_field(self,field_id,label,row):
        if self.is_recording:
            self._add_action(MacroAction('paste_date',self._get_delay(),data_field=field_id,data_label=label,data_row=row))

    def _on_mouse_scroll(self, x: int, y: int, dx: int, dy: int):
        if not self.is_recording:
            return
        if self.ignore_mouse and self.ignore_mouse(x, y):
            return
        delay = self._get_delay()
        action = MacroAction(
            action_type="mouse_scroll",
            delay=delay,
            x=int(x),
            y=int(y),
            dx=int(dx),
            dy=int(dy),
        )
        self._add_action(action)

    def _on_mouse_move(self, x: int, y: int):
        if not self.is_recording or not self.record_movement:
            return
        if self.ignore_mouse and self.ignore_mouse(x, y):
            return
        now = time.perf_counter()
        if now - self._last_time < 0.03:
            return
        delay = self._get_delay()
        action = MacroAction(
            action_type="mouse_move",
            delay=delay,
            x=int(x),
            y=int(y),
        )
        self._add_action(action)

    def _on_key_press(self, key: Any):
        if not self.is_recording or key is None:
            return
        identity = key_identity(key)
        self._pressed_keys.add(identity)
        matched = next((combo for combo in self._control_combinations if combo <= self._pressed_keys), None)
        if matched:
            self._ignored_releases.update(matched)
            for name in matched:
                self._own_modifiers.pop(name, None)
                self._captured_modifiers.discard(name)
            # Không lưu Ctrl/Alt/Shift vừa bấm để dừng ghi vào cuối kịch bản.
            with self._lock:
                while self.actions and self.actions[-1].action_type == 'key_press' and \
                        key_identity(str_to_key(self.actions[-1].key)) in matched & {'ctrl', 'alt', 'shift', 'cmd'}:
                    self.actions.pop()
            return
        if self.ignore_keyboard and self.ignore_keyboard():
            if identity not in self._captured_modifiers:
                self._ignored_releases.add(identity)
                if identity in {'ctrl', 'alt', 'shift', 'cmd'}:
                    self._own_modifiers[identity] = key
            return
        # Ctrl có thể được giữ từ ô dữ liệu sang cửa sổ cần dán.
        for name, held in list(self._own_modifiers.items()):
            self._own_modifiers.pop(name, None)
            if name in self._pressed_keys and name != identity:
                self._ignored_releases.discard(name)
                self._captured_modifiers.add(name)
                self._add_action(MacroAction('key_press', self._get_delay(), key=key_to_str(held)))
        self._ignored_releases.discard(identity)
        if identity in {'ctrl', 'alt', 'shift', 'cmd'}:
            self._captured_modifiers.add(identity)
        delay = self._get_delay()
        action = MacroAction(
            action_type="key_press",
            delay=delay,
            key=key_to_str(key),
        )
        self._add_action(action)

    def _on_key_release(self, key: Any):
        if not self.is_recording or key is None:
            return
        identity = key_identity(key)
        self._pressed_keys.discard(identity)
        self._own_modifiers.pop(identity, None)
        captured = identity in self._captured_modifiers
        self._captured_modifiers.discard(identity)
        if identity in self._ignored_releases:
            self._ignored_releases.discard(identity)
            return
        if not captured and self.ignore_keyboard and self.ignore_keyboard():
            return
        delay = self._get_delay()
        action = MacroAction(
            action_type="key_release",
            delay=delay,
            key=key_to_str(key),
        )
        self._add_action(action)

    @staticmethod
    def _filter_keyboard_event(msg, data):
        # Bộ gõ tự sinh Backspace/Unicode để thay dấu; chỉ ghi phím vật lý.
        return not (data.flags & 0x12)  # LLKHF_INJECTED | LLKHF_LOWER_IL_INJECTED

    def start(self):
        self._control_combinations = [hotkey_identities(text) for text in self.control_hotkeys if text]
        with self._lock:
            self.actions = []
            self._pressed_keys.clear()
            self._ignored_releases.clear()
            self._own_modifiers.clear()
            self._captured_modifiers.clear()
            self.is_recording = True
            self._last_time = time.perf_counter()

        play_sound("start_record")

        self._mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll,
            on_move=self._on_mouse_move,
        )
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
            win32_event_filter=lambda msg,data:self._filter_keyboard_event(msg,data) and not self.ignore_key_event(msg,data),
        )
        self._mouse_listener.daemon = True
        self._keyboard_listener.daemon = True
        self._mouse_listener.start()
        self._keyboard_listener.start()

    def stop(self) -> List[MacroAction]:
        with self._lock:
            self.is_recording = False

        if self._mouse_listener:
            try:
                self._mouse_listener.stop()
            except Exception:
                pass
            self._mouse_listener = None

        if self._keyboard_listener:
            try:
                self._keyboard_listener.stop()
            except Exception:
                pass
            self._keyboard_listener = None

        play_sound("stop_record")
        return list(self.actions)


# ==========================================
# 6. PLAYER: BỘ THỰC HIỆN THAO TÁC (REPLAY)
# ==========================================
class PlaybackBlocked(RuntimeError):
    def __init__(self, reason, message):
        super().__init__(message)
        self.reason = reason


class MacroPlayer:
    def __init__(self):
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        self.is_playing = False
        self._abort_event = threading.Event()
        self._resume_event = threading.Event()
        self._play_thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_step: Optional[Callable[[int, int, int, int], None]] = None
        self.on_finished: Optional[Callable[[bool, bool], None]] = None
        self.on_wait: Optional[Callable[[str], None]] = None
        self.on_paused = None
        self.on_resumed = None
        self.pause = None
        self.log_path = None
        self.script_name = ''
        self.last_error = ''
        self.protect_mouse = None
        self.protect_keyboard = None
        self.on_input_finished = None
        self.field_reader = None
        self.on_field_copied = None
        self.current_loop = 1
        self.data_start_row = None
        self._held_buttons = set()
        self._held_keys = set()
        self._guarded = False
        self._target_window = None
        self._step_window = None
        self._sent_to = None

    def is_running(self) -> bool:
        return self.is_playing

    def stop(self):
        """Dừng khẩn cấp ngay lập tức."""
        if not self.is_playing or self._abort_event.is_set():
            return
        self._abort_event.set()
        self._resume_event.set()
        play_sound("emergency_stop")

    def resume(self):
        if self.pause and not self._abort_event.is_set():
            self._resume_event.set()

    def _release_held_input(self):
        for held, controller in ((self._held_buttons, self.mouse_controller),
                                 (self._held_keys, self.keyboard_controller)):
            for key in tuple(held):
                try:
                    controller.release(key)
                except Exception:
                    pass
            held.clear()

    def _log_event(self, event, step, reason):
        if self.log_path is None:
            return
        entry = dict(time=datetime.now().astimezone().isoformat(timespec='milliseconds'),
                     script=self.script_name, step=step, event=event, reason=reason)
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open('a', encoding='utf-8') as log:
                log.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except OSError:
            print('Không thể ghi nhật ký phát lại Học Vẹt.', file=sys.stderr)

    def _pause_at(self, step, total, error, uncertain):
        self._resume_event.clear()
        if self._abort_event.is_set():
            return False
        detail = str(error)
        if uncertain:
            self._release_held_input()
            detail += ' Hãy kiểm tra kết quả trên cửa sổ đích. Tiếp tục sẽ kết thúc lượt chạy.'
        self.pause = (self.script_name, step, total, detail)
        self._log_event('paused', step, error.reason)
        if self.on_paused:
            self.on_paused(*self.pause)
        self._resume_event.wait()
        self.pause = None
        if self._abort_event.is_set():
            return False
        self._log_event('resume_requested', step, error.reason)
        if uncertain:
            self.last_error = detail
            return False
        return True

    def _check_target(self, action, point=None):
        if self._abort_event.is_set():
            raise InterruptedError
        if point is not None and self.protect_mouse and self.protect_mouse(*point):
            raise PlaybackBlocked('panel_at_point', 'Tọa độ chạm bảng Học Vẹt. Hãy kéo bảng ra khỏi vị trí thao tác.')
        foreground = foreground_window() if self._guarded else None
        if (self._guarded or point is None) and self.protect_keyboard and self.protect_keyboard():
            raise PlaybackBlocked('panel_has_focus', 'Học Vẹt đang nhận tiêu điểm. Hãy chọn cửa sổ đích.')
        if not self._guarded:
            return None
        if not foreground:
            raise PlaybackBlocked('no_foreground', 'Không có cửa sổ đích đang nhận tiêu điểm.')
        if action.window_title:
            expected = action.window_title
            if not title_matches(expected, window_title(foreground)):
                raise PlaybackBlocked('title_mismatch', f'Cửa sổ phía trước không khớp với “{expected}”.')
        expected_window = self._step_window or (None if action.window_title else self._target_window)
        if expected_window and foreground != expected_window:
            raise PlaybackBlocked('focus_changed', 'Cửa sổ đích đã mất tiêu điểm. Hãy chọn lại cửa sổ đích.')
        if point is not None and window_at(*point) != foreground:
            raise PlaybackBlocked('wrong_mouse_window', 'Tọa độ thao tác nằm trên cửa sổ khác. Hãy đưa cửa sổ đích ra trước.')
        if foreground_window() != foreground:
            raise PlaybackBlocked('focus_changed', 'Cửa sổ đích đã mất tiêu điểm. Hãy chọn lại cửa sổ đích.')
        self._target_window = foreground
        self._step_window = foreground
        return foreground

    def _send_input(self, action, method, value, *, point=None, held=None, pressed=None):
        target = self._check_target(action, point)
        if point is not None and self.mouse_controller.position != point:
            raise PlaybackBlocked('cursor_moved', 'Con trỏ đã rời tọa độ thao tác. Hãy thử tiếp tục.')
        if self._abort_event.is_set():
            raise InterruptedError
        self._sent_to = target
        if held is not None and pressed:
            held.add(value)
        method(value)
        if held is not None and not pressed:
            held.discard(value)

    def _wait_for_condition(self, action, retry):
        if not math.isfinite(action.timeout) or not 0 < action.timeout <= 3600:
            raise ValueError('Thời gian chờ phải từ 0 đến 3600 giây.')
        check = condition_check(action)
        window_wait = action.action_type == 'wait_window'
        label = f'cửa sổ “{action.window_title}”' if window_wait else f'ảnh / nút mẫu tại ({action.x}, {action.y})'
        if self.on_wait and not retry:
            self.on_wait(f'ĐANG CHỜ · {label} · Tối đa {action.timeout:g} giây')
        deadline = time.monotonic() + action.timeout
        while not self._abort_event.is_set():
            if window_wait:
                foreground = foreground_window()
                if foreground and check(foreground) and foreground_window() == foreground:
                    self._target_window = foreground
                    return
            elif check():
                return
            remaining = deadline - time.monotonic()
            if retry or remaining <= 0:
                detail = f'Vẫn chưa tìm thấy {label}.' if retry else f'Không tìm thấy {label} sau {action.timeout:g} giây.'
                raise PlaybackBlocked(f'{action.action_type}_timeout', detail)
            self._abort_event.wait(min(0.2, remaining))

    def play_async(
        self,
        actions: List[MacroAction],
        speed: float = 1.0,
        loop_count: int = 1,
        loop_delay: float = 1.0,
        *, script_name: str = '',
    ):
        if self.is_playing:
            return
        self.data_start_row=next((action.data_row for action in actions if action.action_type in ('copy_field','paste_date')),None)
        self._abort_event.clear()
        self.script_name = script_name
        self.last_error = ''
        self.is_playing = True
        self._play_thread = threading.Thread(
            target=self._run_playback,
            args=(actions, speed, loop_count, loop_delay),
            daemon=True,
        )
        self._play_thread.start()

    def _run_playback(
        self,
        actions: List[MacroAction],
        speed: float,
        loop_count: int,
        loop_delay: float,
    ):
        total_steps = len(actions)
        speed = max(1.0, min(10.0, speed))
        current_loop = 1
        idx = 1
        stop_reason = 'user_stop'
        completed = False
        self._guarded = True
        _playback_input.active = True

        play_sound("start_play")

        try:
            self._target_window = None if self.protect_keyboard and self.protect_keyboard() else foreground_window()
            while not self._abort_event.is_set():
                self.current_loop = current_loop
                for idx, action in enumerate(actions, start=1):
                    if self._abort_event.wait(max(0, action.delay / speed)):
                        return
                    if self.on_step:
                        self.on_step(idx, total_steps, current_loop, loop_count)
                    next_action = actions[idx] if idx < total_steps else (
                        actions[0] if not loop_count or current_loop < loop_count else None)
                    retry = False
                    while not self._abort_event.is_set():
                        self._sent_to = self._step_window = None
                        try:
                            self._run_step(action, next_action, retry)
                        except PlaybackBlocked as error:
                            uncertain = bool(self._sent_to or self._held_buttons or self._held_keys)
                            if not self._pause_at(idx, total_steps, error, uncertain):
                                stop_reason = f'user_stop_while_paused:{error.reason}' if self._abort_event.is_set() else 'uncertain_input'
                                return
                            retry = True
                        else:
                            if retry and not self._abort_event.is_set():
                                self._log_event('resumed', idx, 'condition_met')
                                if self.on_resumed:
                                    self.on_resumed()
                            break
                    if self._abort_event.is_set():
                        if action.action_type in ('wait_window', 'wait_image'):
                            stop_reason = f'user_stop_during_{action.action_type}'
                        return

                if loop_count > 0 and current_loop >= loop_count:
                    completed = True
                    break

                current_loop += 1
                if loop_delay > 0:
                    if self._abort_event.wait(loop_delay):
                        return

        except InterruptedError:
            if not self._abort_event.is_set():
                self.last_error = 'Không thể hoàn tất thao tác phát lại.'
                stop_reason = 'playback_error'
        except Exception as ex:
            self.last_error = str(ex)
            stop_reason = 'playback_error'
        finally:
            self._release_held_input()
            _playback_input.active = False
            if self.on_input_finished:
                try:
                    self.on_input_finished()
                except Exception as error:
                    self.last_error = str(error)
                    completed = False
                    stop_reason = 'input_cleanup_failed'
            if self._abort_event.is_set() or not completed:
                self._log_event('stopped', idx, stop_reason)
            success = completed and not self._abort_event.is_set()
            self._guarded = False
            self.pause = None
            self.field_reader = None
            self.is_playing = False
            if success:
                play_sound("stop_play")
            if self.on_finished:
                self.on_finished(success, not success)

    def _run_step(self, action, next_action, retry):
        if action.action_type in ('wait_window', 'wait_image'):
            self._wait_for_condition(action, retry)
            return
        try:
            self._execute_action(action)
            if self._sent_to and not self._abort_event.is_set():
                foreground = foreground_window()
                if foreground != self._sent_to and not (
                        foreground and next_action and next_action.window_title
                        and title_matches(next_action.window_title, window_title(foreground))):
                    raise PlaybackBlocked('focus_changed_after_send', 'Tiêu điểm đã đổi trong lúc gửi thao tác.')
        except PlaybackBlocked:
            raise
        except Exception as error:
            if self._sent_to and not self._abort_event.is_set():
                raise PlaybackBlocked('send_uncertain', 'Chưa xác nhận được kết quả thao tác đã gửi.') from error
            raise

    def _execute_action(self, action: MacroAction):
        act_type = action.action_type
        if act_type == 'paste_date':
            target = self._check_target(action)

        if act_type in ('copy_field','paste_date'):
            if not self.field_reader: raise RuntimeError('Chưa có bảng dữ liệu cho kịch bản HIS.')
            value=self.field_reader(action.data_field,action.data_row+self.current_loop-1)
            if act_type=='paste_date':
                from date_paste import paste_date
                for key in (keyboard.Key.ctrl_l,keyboard.Key.ctrl_r):
                    if key in self._held_keys:
                        self._send_key(action, self.keyboard_controller.release, key)
                def protect():
                    self._check_target(action)
                    return False
                paste_date(value,self.keyboard_controller,self._abort_event,protect,target=target,
                    send=lambda method, key: self._send_key(action, method, key),
                    navigation=getattr(self.field_reader,'date_navigation',{}).get(action.data_field,'tab'))
            else:set_clipboard_text(value,self._abort_event)
            if self.on_field_copied:
                self.on_field_copied(getattr(self.field_reader,'environment_id',None),
                    getattr(self.field_reader,'field_ids',{}).get(action.data_field,action.data_field),action.data_row+self.current_loop-1)
        elif act_type.startswith('mouse_'):
            controller = self.mouse_controller
            point = (action.x, action.y) if action.x is not None and action.y is not None else None
            if point is not None:
                target = self._check_target(action, point)
                if self._abort_event.is_set():
                    raise InterruptedError
                if act_type == 'mouse_move' or self._held_buttons:
                    self._sent_to = target
                controller.position = point
            if act_type in ('mouse_click', 'mouse_scroll'):
                position = controller.position
                if position is None:
                    raise PlaybackBlocked('cursor_unavailable', 'Không đọc được vị trí con trỏ chuột.')
                if point is not None and position != point:
                    raise PlaybackBlocked('cursor_moved', 'Con trỏ đã rời tọa độ thao tác. Hãy thử tiếp tục.')
            if act_type == 'mouse_click':
                button = str_to_button(action.button or 'left')
                method = controller.press if action.pressed else controller.release
                self._send_input(action, method, button, point=position,
                                 held=self._held_buttons, pressed=action.pressed)
            elif act_type == 'mouse_scroll':
                self._send_input(action, lambda delta: controller.scroll(*delta),
                                 (action.dx or 0, action.dy or 0), point=position)
        elif act_type in ('key_press', 'key_release') and action.key:
            key = str_to_key(action.key)
            if key is not None:
                controller = self.keyboard_controller
                self._send_key(action, controller.press if act_type == 'key_press' else controller.release, key)

    def _send_key(self, action, method, key):
        self._send_input(action, method, key, held=self._held_keys, pressed=method == self.keyboard_controller.press)


# ==========================================
# 7. SCRIPT LIBRARY & STORAGE
# ==========================================
class MacroStorage:
    MAX_SCRIPT_BYTES = 30 * 1024 * 1024

    @staticmethod
    def default_library_path():
        folder = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'HocVet'
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / 'scripts_library.json'
        if not target.exists() and not target.with_suffix('.json.bak').exists():
            app_folder = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
            candidates = [app_folder / 'scripts_library.json', Path.cwd() / 'scripts_library.json']
            if app_folder.name.lower() == 'dist':
                candidates.append(app_folder.parent / 'scripts_library.json')
            for legacy in dict.fromkeys(candidates):
                if legacy.is_file() and legacy.resolve() != target.resolve():
                    profiles, settings = MacroStorage.load_library(str(legacy))
                    MacroStorage.save_library(profiles, target, settings)
                    break
        return str(target)

    @staticmethod
    def _atomic_json(payload, file_path):
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                             prefix=target.name, suffix='.tmp', delete=False) as stream:
                temporary = stream.name
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            if target.exists():
                try:
                    json.loads(target.read_text(encoding='utf-8'))
                except (ValueError, UnicodeError):
                    pass  # Giữ bản dự phòng tốt nếu file chính hỏng.
                else:
                    shutil.copy2(target, str(target) + '.bak')
            os.replace(temporary, target)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def validate_profile(profile):
        allowed = {'mouse_click', 'mouse_move', 'mouse_scroll', 'key_press', 'key_release', 'copy_field', 'paste_date',
                   'wait_window', 'wait_image'}
        if not profile.name or len(profile.actions) > 100000:
            raise ValueError('Tên kịch bản trống hoặc quá nhiều bước.')
        if profile.hotkey:
            keyboard.HotKey.parse(normalize_hotkey(profile.hotkey))
        for value in (profile.speed, profile.loop_delay):
            if not math.isfinite(value) or value < 0:
                raise ValueError('Tốc độ hoặc thời gian nghỉ không hợp lệ.')
        if profile.speed < 0.1 or profile.loop_count < 0:
            raise ValueError('Tốc độ tối thiểu 0.1; số vòng không được âm.')
        for action in profile.actions:
            if action.action_type not in allowed or not math.isfinite(action.delay) or action.delay < 0:
                raise ValueError('Loại thao tác hoặc độ trễ không hợp lệ.')
            if action.action_type in ('copy_field','paste_date'):
                if not isinstance(action.data_field,str) or not 1<=len(action.data_field)<=80 or type(action.data_row) is not int or not 1<=action.data_row<=10000:
                    raise ValueError('Tham chiếu ô dữ liệu không hợp lệ.')
                if action.data_label is not None and (not isinstance(action.data_label,str) or len(action.data_label)>100):
                    raise ValueError('Tên trường dữ liệu không hợp lệ.')
            if action.action_type.startswith('key_'):
                if not isinstance(action.key, str) or not action.key or str_to_key(action.key) is None:
                    raise ValueError('Phím trong kịch bản không hợp lệ.')
            if action.action_type.startswith('mouse_'):
                if not all(isinstance(value, int) for value in (action.x, action.y)):
                    raise ValueError('Tọa độ chuột không hợp lệ.')
                if action.action_type == 'mouse_click' and (action.button not in ('left', 'right', 'middle') or not isinstance(action.pressed, bool)):
                    raise ValueError('Nút chuột không hợp lệ.')
                if action.action_type == 'mouse_scroll' and not all(isinstance(value, int) for value in (action.dx, action.dy)):
                    raise ValueError('Khoảng cuộn chuột không hợp lệ.')
            if action.action_type.startswith('wait_'):
                if not math.isfinite(action.timeout) or not 0 < action.timeout <= 3600:
                    raise ValueError('Thời hạn chờ phải lớn hơn 0 và tối đa 3600 giây.')
            if action.action_type == 'wait_window' and not (action.window_title or '').strip():
                raise ValueError('Thiếu tên cửa sổ cần chờ.')
            if action.action_type == 'wait_image':
                if not isinstance(action.x, int) or not isinstance(action.y, int):
                    raise ValueError('Thiếu tọa độ vùng ảnh cần chờ.')
                if not math.isfinite(action.tolerance) or not 0 <= action.tolerance <= 0.2:
                    raise ValueError('Sai số ảnh phải từ 0 đến 20%.')
                decode_reference(action.image)

    @staticmethod
    def export_profile(profile, file_path):
        MacroStorage.validate_profile(profile)
        text = MacroStorage.export_profile_to_string(profile).encode('utf-8')
        if len(text) > MacroStorage.MAX_SCRIPT_BYTES:
            raise ValueError('Kịch bản quá lớn (tối đa 30 MB).')
        if str(file_path).lower().endswith('.json'):
            MacroStorage._atomic_json(json.loads(text), file_path)
            return
        with zipfile.ZipFile(file_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('script.json', text)

    @staticmethod
    def import_profile(file_path):
        if zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path) as archive:
                info = archive.getinfo('script.json')
                if info.file_size > MacroStorage.MAX_SCRIPT_BYTES:
                    raise ValueError('Kịch bản quá lớn (tối đa 30 MB).')
                text = archive.read(info).decode('utf-8')
        else:
            if os.path.getsize(file_path) > MacroStorage.MAX_SCRIPT_BYTES:
                raise ValueError('Kịch bản quá lớn (tối đa 30 MB).')
            text = Path(file_path).read_text(encoding='utf-8-sig')
        profile = MacroStorage.import_profile_from_string(text)
        if profile is None:
            raise ValueError('File không phải kịch bản Học Vẹt hợp lệ.')
        return profile

    @staticmethod
    def save_to_file(actions: List[MacroAction], file_path: str, metadata: Optional[Dict[str, Any]] = None):
        payload = {
            "version": "1.0",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": metadata or {},
            "total_actions": len(actions),
            "actions": [act.to_dict() for act in actions],
        }
        MacroStorage._atomic_json(payload, file_path)

    @staticmethod
    def load_from_file(file_path: str) -> List[MacroAction]:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_actions = data.get("actions", [])
        return [MacroAction.from_dict(item) for item in raw_actions]

    @staticmethod
    def save_library(profiles: List[ScriptProfile], file_path: str, settings: Optional[Dict[str, Any]] = None):
        """Lưu toàn bộ thư viện nhiều kịch bản ra file JSON."""
        payload = {
            "version": APP_VERSION,
            "author": "Nhật Nam (@UIBreaker)",
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "settings": settings or {},
            "profiles": [p.to_dict() for p in profiles],
        }
        MacroStorage._atomic_json(payload, file_path)

    @staticmethod
    def load_library(file_path: str) -> tuple[List[ScriptProfile], Dict[str, Any]]:
        """Nạp thư viện nhiều kịch bản từ file JSON."""
        file_path = str(file_path)
        if not os.path.isfile(file_path) and not os.path.isfile(file_path + '.bak'):
            return [], {}
        def read(path):
            with open(path, 'r', encoding='utf-8') as stream:
                data = json.load(stream)
            if not isinstance(data, dict) or not isinstance(data.get('profiles'), list):
                raise ValueError('Thư viện kịch bản sai định dạng.')
            profiles = [ScriptProfile.from_dict(item) for item in data['profiles']]
            settings = data.get('settings', {})
            if not isinstance(settings, dict):
                raise ValueError('Cài đặt sai định dạng.')
            return profiles, settings
        try:
            return read(file_path)
        except (OSError, ValueError, TypeError, AttributeError):
            return read(file_path + '.bak')

    @staticmethod
    def export_profile_to_string(profile: ScriptProfile) -> str:
        """Đóng gói kịch bản thành chuỗi JSON gọn gàng để sao chép qua máy khác."""
        payload = {
            "smart_operation_macro": True,
            "version": APP_VERSION,
            "author": "Nhật Nam (@UIBreaker)",
            "profile": profile.to_dict(),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def import_profile_from_string(text: str) -> Optional[ScriptProfile]:
        """Khôi phục kịch bản từ chuỗi sao chép (Clipboard hoặc file)."""
        try:
            data = json.loads(text.strip())
            if isinstance(data, dict):
                if "profile" in data:
                    p = ScriptProfile.from_dict(data["profile"])
                    MacroStorage.validate_profile(p)
                    p.id = str(uuid.uuid4())[:8]  # Đổi ID mới tránh trùng lặp
                    return p
                elif "actions" in data:
                    p = ScriptProfile.from_dict(data)
                    metadata = data.get('metadata', {})
                    p.name = metadata.get('name', p.name)
                    p.hotkey = metadata.get('hotkey', p.hotkey)
                    p.speed = float(metadata.get('speed', p.speed))
                    MacroStorage.validate_profile(p)
                    p.id = str(uuid.uuid4())[:8]
                    return p
        except Exception:
            pass
        return None


# ==========================================
# 8. MACRO MANAGER: QUẢN LÝ ĐA KỊCH BẢN & PHÍM TẮT TOÀN CỤC
# ==========================================
class MacroManager:
    STATE_IDLE = "idle"
    STATE_COUNTDOWN = 'countdown'
    STATE_RECORDING = "recording"
    STATE_PLAYING = "playing"
    STATE_PAUSED = "paused"

    def __init__(self, library_path: Optional[str] = None):
        self.state = self.STATE_IDLE
        self.recorder = MacroRecorder(record_movement=False)
        self.player = MacroPlayer()

        self.library_path = library_path if library_path is not None else MacroStorage.default_library_path()
        self.player.log_path = Path(self.library_path).with_name('playback_events.jsonl')
        self.profiles: List[ScriptProfile] = []
        self.active_profile_id: Optional[str] = None

        # Cài đặt phím tắt hệ thống
        self.hotkey_record_str = "F8"
        self.hotkey_panic_str = "ESC"
        self.button_hotkeys = {name: default for name, (_, default, _) in SHORTCUT_ACTIONS.items()
                               if name not in ('record', 'panic')}
        self.on_command = None
        self.on_record_toggle = None
        self.on_record_stopped = None
        self.on_panic = None
        self.shortcuts_suspended = False
        self.external_busy = False
        self.prepare_field_data = None
        self.button_hotkey_scopes = {name: 'global' if name in ('show', 'stop_record') else 'app'
                                     for name in self.button_hotkeys if SHORTCUT_ACTIONS[name][2] != 'dialog'}

        # Cài đặt ứng dụng
        self.minimize_to_tray_on_close = True
        self.panel_size = None
        self.script_activation = 'mouse'
        self.animations_enabled = True

        # Global HotKeys Listener
        self._global_hotkeys: Optional[keyboard.GlobalHotKeys] = None
        self._lock = threading.Lock()

        # Callbacks cập nhật UI
        self.on_state_changed: Optional[Callable[[str], None]] = None
        self.on_action_recorded: Optional[Callable[[MacroAction, int], None]] = None
        self.on_step: Optional[Callable[[int, int, int, int], None]] = None
        self.on_play_finished: Optional[Callable[[bool, bool], None]] = None
        self.on_play_paused = None
        self.on_play_resumed = None
        self.on_profile_triggered: Optional[Callable[[ScriptProfile], None]] = None

        self.recorder.on_action_recorded = self._handle_action_recorded
        self.player.on_step = self._handle_step
        self.player.on_finished = self._handle_play_finished
        self.player.on_paused = self._handle_play_paused
        self.player.on_resumed = self._handle_play_resumed

        # Tải thư viện kịch bản đã lưu
        self.load_library()

    def get_active_profile(self) -> Optional[ScriptProfile]:
        if not self.profiles:
            return None
        if self.active_profile_id:
            for p in self.profiles:
                if p.id == self.active_profile_id:
                    return p
        return self.profiles[0]

    def set_active_profile(self, profile_id: str):
        self.active_profile_id = profile_id

    def delete_profile(self, profile_id: str) -> bool:
        """Xóa kịch bản khỏi thư viện (đảm bảo luôn giữ ít nhất 1 kịch bản)."""
        if len(self.profiles) <= 1:
            return False
        idx = next((i for i, p in enumerate(self.profiles) if p.id == profile_id), -1)
        if idx == -1:
            return False
        deleted = self.profiles.pop(idx)
        previous_active = self.active_profile_id
        if self.active_profile_id == profile_id:
            new_idx = min(idx, len(self.profiles) - 1)
            self.active_profile_id = self.profiles[new_idx].id
        try:
            self.save_library()
        except OSError:
            self.profiles.insert(idx, deleted)
            self.active_profile_id = previous_active
            raise
        self.reload_global_hotkeys()
        return True

    def load_library(self):
        loaded_profiles, settings = MacroStorage.load_library(self.library_path)
        if loaded_profiles:
            self.profiles = loaded_profiles
            self.active_profile_id = self.profiles[0].id
        else:
            # Tạo sẵn 1 kịch bản mẫu mặc định cho người dùng HIS
            sample_profile = ScriptProfile(
                id="default_kiso",
                name="Ký số & Kết thúc khám",
                hotkey="F9",
                actions=[
                    MacroAction("mouse_click", delay=0.5, x=420, y=310, button="left", pressed=True),
                    MacroAction("mouse_click", delay=0.05, x=420, y=310, button="left", pressed=False),
                    MacroAction("mouse_click", delay=0.8, x=860, y=620, button="left", pressed=True),
                    MacroAction("mouse_click", delay=0.05, x=860, y=620, button="left", pressed=False),
                    MacroAction("mouse_click", delay=1.5, x=980, y=720, button="left", pressed=True),
                    MacroAction("mouse_click", delay=0.05, x=980, y=720, button="left", pressed=False),
                ],
                speed=1.0,
                loop_count=1,
                loop_delay=1.0,
                description="Kịch bản tự động hóa ký số và hoàn tất khám bệnh",
            )
            self.profiles = [sample_profile]
            self.active_profile_id = sample_profile.id

        if settings:
            saved = settings.get('button_hotkeys', {})
            if isinstance(saved, dict):
                self.button_hotkeys.update({name: value for name, value in saved.items()
                    if name in self.button_hotkeys and isinstance(value, str)})
            scopes = settings.get('button_hotkey_scopes', {})
            if isinstance(scopes, dict):
                self.button_hotkey_scopes.update({name: value for name, value in scopes.items()
                    if name in self.button_hotkey_scopes and value in ('app', 'global')})
            self.hotkey_record_str = settings.get("hotkey_record", "F8")
            self.hotkey_panic_str = settings.get("hotkey_panic", "ESC")
            self.minimize_to_tray_on_close = settings.get("minimize_to_tray_on_close", True)
            self.animations_enabled = bool(settings.get("animations_enabled", True))
            activation = settings.get('script_activation', 'mouse')
            self.script_activation = activation if activation in ('mouse', 'hotkey') else 'mouse'
            size = settings.get('panel_size')
            if isinstance(size,list) and len(size)==2 and all(type(v) is int and 0 < v <= 20000 for v in size):
                self.panel_size = size
        # Phím dừng học phải hoạt động khi người dùng đang thao tác ở phần mềm khác.
        self.button_hotkey_scopes['stop_record'] = 'global'

    def save_library(self):
        settings = {
            "hotkey_record": self.hotkey_record_str,
            "hotkey_panic": self.hotkey_panic_str,
            "minimize_to_tray_on_close": self.minimize_to_tray_on_close,
            "script_activation": self.script_activation,
            "panel_size": self.panel_size,
            "button_hotkeys": self.button_hotkeys,
            "button_hotkey_scopes": self.button_hotkey_scopes,
            "animations_enabled": self.animations_enabled,
        }
        MacroStorage.save_library(self.profiles, self.library_path, settings=settings)

    def _set_state(self, new_state: str):
        with self._lock:
            self.state = new_state
        if self.on_state_changed:
            self.on_state_changed(new_state)

    # ------------------------------------------
    # QUẢN LÝ HOTKEYS TOÀN CỤC (GLOBAL HOTKEYS)
    # ------------------------------------------
    def start_global_hotkeys(self):
        """Khởi động bộ lắng nghe phím tắt toàn hệ thống cho tất cả kịch bản."""
        self.stop_global_hotkeys()
        if self.shortcuts_suspended or self.script_activation == 'mouse':
            return

        hotkey_map = {}

        # 1. Phím tắt Bắt đầu / Dừng học thao tác
        norm_rec = normalize_hotkey(self.hotkey_record_str)
        if norm_rec and self.script_activation == 'hotkey':
            hotkey_map[norm_rec] = self._on_hotkey_toggle_record

        # 2. Phím tắt Dừng khẩn cấp
        norm_panic = normalize_hotkey(self.hotkey_panic_str)
        if norm_panic:
            hotkey_map[norm_panic] = self._on_hotkey_panic

        # 3. Phím tắt riêng cho TỪNG kịch bản được kích hoạt (Enabled)
        for profile in self.profiles:
            if self.script_activation != 'hotkey' or not profile.enabled:
                continue
            norm_hk = normalize_hotkey(profile.hotkey)
            if norm_hk and norm_hk not in hotkey_map:
                # Đóng gói profile vào callback
                hotkey_map[norm_hk] = (lambda p=profile: self._on_hotkey_play_profile(p))

        for action, hotkey in self.button_hotkeys.items():
            if self.script_activation == 'mouse' and action in ('play', 'stop_record', 'work_run', 'work_learn'):
                continue
            if hotkey and (action == 'stop_record' or self.button_hotkey_scopes.get(action) == 'global'):
                hotkey_map.setdefault(normalize_hotkey(hotkey), lambda name=action: self._on_command_hotkey(name))

        try:
            self._global_hotkeys = keyboard.GlobalHotKeys(hotkey_map,
                win32_event_filter=MacroRecorder._filter_keyboard_event)
            self._global_hotkeys.daemon = True
            self._global_hotkeys.start()
        except Exception as ex:
            print(f"Lỗi khởi động GlobalHotKeys: {ex}", file=sys.stderr)

    def stop_global_hotkeys(self):
        if self._global_hotkeys:
            try:
                self._global_hotkeys.stop()
            except Exception:
                pass
            self._global_hotkeys = None

    def reload_global_hotkeys(self):
        """Cập nhật lại phím tắt khi người dùng thêm/sửa kịch bản hoặc đổi cài đặt."""
        self.start_global_hotkeys()

    def shortcut_values(self):
        return dict(self.button_hotkeys, record=self.hotkey_record_str, panic=self.hotkey_panic_str)

    def apply_shortcuts(self, values, scopes=None):
        scopes = self.button_hotkey_scopes if scopes is None else scopes
        validate_shortcuts(values, self.profiles, scopes)
        self.hotkey_record_str = values['record'].strip().upper()
        self.hotkey_panic_str = values['panic'].strip().upper()
        self.button_hotkeys = {name: values.get(name, '').strip() for name in self.button_hotkeys}
        self.button_hotkey_scopes = {name: scopes.get(name, 'app') for name in self.button_hotkey_scopes}
        self.button_hotkey_scopes['stop_record'] = 'global'

    def _on_command_hotkey(self, action):
        if self.script_activation == 'mouse':
            return
        if self.on_command and (self.state == self.STATE_IDLE or
                action == 'stop_record' and self.state in (self.STATE_RECORDING, self.STATE_COUNTDOWN)):
            self.on_command(action)

    def _on_hotkey_panic(self):
        if self.script_activation != 'hotkey': return
        if self.on_panic:
            self.on_panic()
        else:
            self.stop_playing()

    def _on_hotkey_toggle_record(self):
        if self.script_activation != 'hotkey':
            return
        if self.on_record_toggle:
            self.on_record_toggle()
            return
        if self.state == self.STATE_IDLE:
            self.start_recording()
        elif self.state == self.STATE_RECORDING:
            self.stop_recording()

    def _on_hotkey_play_profile(self, profile: ScriptProfile):
        if self.script_activation != 'hotkey':
            return
        if self.state == self.STATE_IDLE and not self.external_busy and profile.enabled and profile.actions:
            if self.on_profile_triggered:
                self.on_profile_triggered(profile)
            else:
                self.set_active_profile(profile.id)
                self.start_playing_profile(profile)

    # ------------------------------------------
    # GHI & PHÁT KỊCH BẢN
    # ------------------------------------------
    def start_recording(self, record_movement: bool = False):
        if self.external_busy or self.state not in (self.STATE_IDLE, self.STATE_COUNTDOWN):
            return
        self.recorder.record_movement = record_movement
        self.recorder.control_hotkeys = [self.hotkey_record_str, self.hotkey_panic_str,
                                         self.button_hotkeys.get('stop_record', '')]
        if self.script_activation == 'mouse':
            self.recorder.control_hotkeys = []
        self.recorder.start()
        self._set_state(self.STATE_RECORDING)

    def stop_recording(self) -> List[MacroAction]:
        if self.state != self.STATE_RECORDING:
            return []
        recorded = self.recorder.stop()
        # Tự động gán vào profile hiện tại hoặc trả về
        active = self.get_active_profile()
        if active:
            active.actions = recorded
            try:
                self.save_library()
            except OSError as error:
                self._set_state(self.STATE_IDLE)
                raise OSError(f'Đã dừng học nhưng chưa lưu được: {error}. Kịch bản vẫn trong ứng dụng; hãy xuất ra file hoặc thử lưu lại.') from error
        self._set_state(self.STATE_IDLE)
        if self.on_record_stopped:
            self.on_record_stopped(active, len(recorded))
        return recorded

    def start_playing_profile(self, profile: ScriptProfile):
        if self.external_busy or self.state != self.STATE_IDLE or not profile.actions:
            return
        loops=profile.loop_count
        reader=None
        if any(action.action_type in ('copy_field','paste_date') for action in profile.actions):
            if not self.prepare_field_data: raise ValueError('Cần cài Hỗ trợ ĐK KCB HIS và nạp bảng dữ liệu trước khi chạy.')
            loops,reader=self.prepare_field_data(profile.actions,loops)
        self.player.field_reader=reader
        self._set_state(self.STATE_PLAYING)
        self.player.play_async(
            profile.actions,
            speed=profile.speed,
            loop_count=loops,
            loop_delay=profile.loop_delay,
            script_name=profile.name,
        )

    def start_playing_active(self):
        active = self.get_active_profile()
        if active:
            self.start_playing_profile(active)

    def resume_playing(self):
        if self.state == self.STATE_PAUSED:
            self.player.resume()

    def stop_playing(self):
        if self.state in (self.STATE_PLAYING, self.STATE_PAUSED):
            self.player.stop()
        elif self.state == self.STATE_RECORDING:
            self.stop_recording()

    def _handle_action_recorded(self, action: MacroAction, count: int):
        if self.on_action_recorded:
            self.on_action_recorded(action, count)

    def _handle_step(self, step: int, total: int, cur_loop: int, total_loops: int):
        if self.on_step:
            self.on_step(step, total, cur_loop, total_loops)

    def _handle_play_paused(self, *pause):
        self._set_state(self.STATE_PAUSED)
        if self.on_play_paused:
            self.on_play_paused(*pause)

    def _handle_play_resumed(self):
        self._set_state(self.STATE_PLAYING)
        if self.on_play_resumed:
            self.on_play_resumed()

    def _handle_play_finished(self, success: bool, aborted: bool):
        self._set_state(self.STATE_IDLE)
        if self.on_play_finished:
            self.on_play_finished(success, aborted)
