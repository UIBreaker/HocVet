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
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable

from pynput import mouse, keyboard
from app_info import APP_VERSION
from conditions import condition_check, decode_reference
from shortcuts import SHORTCUT_ACTIONS, normalize_hotkey, validate_shortcuts, parse_hotkey, key_identity, hotkey_identities


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
            # Không lưu Ctrl/Alt/Shift vừa bấm để dừng ghi vào cuối kịch bản.
            with self._lock:
                while self.actions and self.actions[-1].action_type == 'key_press' and \
                        key_identity(str_to_key(self.actions[-1].key)) in matched & {'ctrl', 'alt', 'shift', 'cmd'}:
                    self.actions.pop()
            return
        if self.ignore_keyboard and self.ignore_keyboard():
            return
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
        if identity in self._ignored_releases:
            self._ignored_releases.discard(identity)
            return
        if self.ignore_keyboard and self.ignore_keyboard():
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
            win32_event_filter=self._filter_keyboard_event,
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
class MacroPlayer:
    def __init__(self):
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        self.is_playing = False
        self._abort_event = threading.Event()
        self._play_thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_step: Optional[Callable[[int, int, int, int], None]] = None
        self.on_finished: Optional[Callable[[bool, bool], None]] = None
        self.on_wait: Optional[Callable[[str], None]] = None
        self.last_error = ''

    def is_running(self) -> bool:
        return self.is_playing

    def stop(self):
        """Dừng khẩn cấp ngay lập tức."""
        if not self.is_playing:
            return
        self._abort_event.set()
        play_sound("emergency_stop")
        self._release_all_modifiers()

    def _release_all_modifiers(self):
        try:
            for btn in (mouse.Button.left, mouse.Button.right, mouse.Button.middle):
                self.mouse_controller.release(btn)
        except Exception:
            pass

        modifier_keys = [
            keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
            keyboard.Key.alt_l, keyboard.Key.alt_r,
            keyboard.Key.shift_l, keyboard.Key.shift_r,
        ]
        for k in modifier_keys:
            try:
                self.keyboard_controller.release(k)
            except Exception:
                pass

    def play_async(
        self,
        actions: List[MacroAction],
        speed: float = 1.0,
        loop_count: int = 1,
        loop_delay: float = 1.0,
    ):
        if self.is_playing:
            return
        self._abort_event.clear()
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
        aborted = False

        play_sound("start_play")

        try:
            while not self._abort_event.is_set():
                for idx, action in enumerate(actions, start=1):
                    if self._abort_event.is_set():
                        aborted = True
                        break

                    actual_delay = action.delay / speed
                    if actual_delay > 0:
                        if self._abort_event.wait(actual_delay):
                            aborted = True
                            break

                    if self.on_step:
                        self.on_step(idx, total_steps, current_loop, loop_count)
                    self._execute_action(action)
                    if self._abort_event.is_set():
                        aborted = True
                        break

                if aborted:
                    break

                if loop_count > 0 and current_loop >= loop_count:
                    break

                current_loop += 1
                if loop_delay > 0:
                    if self._abort_event.wait(loop_delay):
                        aborted = True
                        break

        except Exception as ex:
            self.last_error = str(ex)
            print(f"Lỗi khi thực hiện thao tác: {ex}", file=sys.stderr)
            aborted = True
        finally:
            self._release_all_modifiers()
            self.is_playing = False
            if not aborted:
                play_sound("stop_play")
            if self.on_finished:
                self.on_finished(not aborted, aborted)

    def _execute_action(self, action: MacroAction):
        act_type = action.action_type

        if act_type in ('wait_window', 'wait_image'):
            if not math.isfinite(action.timeout) or not 0 < action.timeout <= 3600:
                raise ValueError('Thời gian chờ phải từ 0 đến 3600 giây.')
            check = condition_check(action)
            label = action.window_title if act_type == 'wait_window' else f'ảnh tại ({action.x}, {action.y})'
            if self.on_wait:
                self.on_wait(f'ĐANG CHỜ: {label} (tối đa {action.timeout:g}s)')
            deadline = time.monotonic() + action.timeout
            while not self._abort_event.is_set():
                if check():
                    return
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f'Hết {action.timeout:g}s chờ {label}. Kịch bản đã dừng trước bước tiếp theo.')
                if self._abort_event.wait(min(0.2, remaining)):
                    return

        elif act_type == "mouse_click":
            if action.x is not None and action.y is not None:
                self.mouse_controller.position = (action.x, action.y)
            btn = str_to_button(action.button or "left")
            if action.pressed:
                self.mouse_controller.press(btn)
            else:
                self.mouse_controller.release(btn)

        elif act_type == "mouse_move":
            if action.x is not None and action.y is not None:
                self.mouse_controller.position = (action.x, action.y)

        elif act_type == "mouse_scroll":
            if action.x is not None and action.y is not None:
                self.mouse_controller.position = (action.x, action.y)
            dx = action.dx or 0
            dy = action.dy or 0
            self.mouse_controller.scroll(dx, dy)

        elif act_type == "key_press":
            if action.key:
                k = str_to_key(action.key)
                if k is not None:
                    self.keyboard_controller.press(k)

        elif act_type == "key_release":
            if action.key:
                k = str_to_key(action.key)
                if k is not None:
                    self.keyboard_controller.release(k)


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
        allowed = {'mouse_click', 'mouse_move', 'mouse_scroll', 'key_press', 'key_release',
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

    def __init__(self, library_path: Optional[str] = None):
        self.state = self.STATE_IDLE
        self.recorder = MacroRecorder(record_movement=False)
        self.player = MacroPlayer()

        self.library_path = library_path if library_path is not None else MacroStorage.default_library_path()
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
        self.button_hotkey_scopes = {name: 'global' if name in ('show', 'stop_record') else 'app'
                                     for name in self.button_hotkeys if SHORTCUT_ACTIONS[name][2] != 'dialog'}

        # Cài đặt ứng dụng
        self.minimize_to_tray_on_close = True

        # Global HotKeys Listener
        self._global_hotkeys: Optional[keyboard.GlobalHotKeys] = None
        self._lock = threading.Lock()

        # Callbacks cập nhật UI
        self.on_state_changed: Optional[Callable[[str], None]] = None
        self.on_action_recorded: Optional[Callable[[MacroAction, int], None]] = None
        self.on_step: Optional[Callable[[int, int, int, int], None]] = None
        self.on_play_finished: Optional[Callable[[bool, bool], None]] = None
        self.on_profile_triggered: Optional[Callable[[ScriptProfile], None]] = None

        self.recorder.on_action_recorded = self._handle_action_recorded
        self.player.on_step = self._handle_step
        self.player.on_finished = self._handle_play_finished

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
        self.profiles.pop(idx)
        if self.active_profile_id == profile_id:
            new_idx = min(idx, len(self.profiles) - 1)
            self.active_profile_id = self.profiles[new_idx].id
        self.save_library()
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
        # Phím dừng học phải hoạt động khi người dùng đang thao tác ở phần mềm khác.
        self.button_hotkey_scopes['stop_record'] = 'global'

    def save_library(self):
        settings = {
            "hotkey_record": self.hotkey_record_str,
            "hotkey_panic": self.hotkey_panic_str,
            "minimize_to_tray_on_close": self.minimize_to_tray_on_close,
            "button_hotkeys": self.button_hotkeys,
            "button_hotkey_scopes": self.button_hotkey_scopes,
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
        if self.shortcuts_suspended:
            return

        hotkey_map = {}

        # 1. Phím tắt Bắt đầu / Dừng học thao tác
        norm_rec = normalize_hotkey(self.hotkey_record_str)
        if norm_rec:
            hotkey_map[norm_rec] = self._on_hotkey_toggle_record

        # 2. Phím tắt Dừng khẩn cấp
        norm_panic = normalize_hotkey(self.hotkey_panic_str)
        if norm_panic:
            hotkey_map[norm_panic] = self._on_hotkey_panic

        # 3. Phím tắt riêng cho TỪNG kịch bản được kích hoạt (Enabled)
        for profile in self.profiles:
            if not profile.enabled:
                continue
            norm_hk = normalize_hotkey(profile.hotkey)
            if norm_hk and norm_hk not in hotkey_map:
                # Đóng gói profile vào callback
                hotkey_map[norm_hk] = (lambda p=profile: self._on_hotkey_play_profile(p))

        for action, hotkey in self.button_hotkeys.items():
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
        if self.on_command and (self.state == self.STATE_IDLE or
                action == 'stop_record' and self.state in (self.STATE_RECORDING, self.STATE_COUNTDOWN)):
            self.on_command(action)

    def _on_hotkey_panic(self):
        if self.on_panic:
            self.on_panic()
        else:
            self.stop_playing()

    def _on_hotkey_toggle_record(self):
        if self.on_record_toggle:
            self.on_record_toggle()
            return
        if self.state == self.STATE_IDLE:
            self.start_recording()
        elif self.state == self.STATE_RECORDING:
            self.stop_recording()

    def _on_hotkey_play_profile(self, profile: ScriptProfile):
        if self.state == self.STATE_IDLE and not self.external_busy and profile.enabled and profile.actions:
            self.set_active_profile(profile.id)
            if self.on_profile_triggered:
                self.on_profile_triggered(profile)
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
        self._set_state(self.STATE_PLAYING)
        self.player.play_async(
            profile.actions,
            speed=profile.speed,
            loop_count=profile.loop_count,
            loop_delay=profile.loop_delay,
        )

    def start_playing_active(self):
        active = self.get_active_profile()
        if active:
            self.start_playing_profile(active)

    def stop_playing(self):
        if self.state == self.STATE_PLAYING:
            self.player.stop()
        elif self.state == self.STATE_RECORDING:
            self.stop_recording()

    def _handle_action_recorded(self, action: MacroAction, count: int):
        if self.on_action_recorded:
            self.on_action_recorded(action, count)

    def _handle_step(self, step: int, total: int, cur_loop: int, total_loops: int):
        if self.on_step:
            self.on_step(step, total, cur_loop, total_loops)

    def _handle_play_finished(self, success: bool, aborted: bool):
        self._set_state(self.STATE_IDLE)
        if self.on_play_finished:
            self.on_play_finished(success, aborted)
