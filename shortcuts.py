"""Danh sách lệnh và cú pháp phím tắt dùng chung cho cài đặt / bộ lắng nghe."""
from pynput import keyboard
import ctypes
from ctypes import wintypes


# id: (nhãn, phím mặc định, phạm vi). Các nút trong hộp thoại dùng phím theo ngữ cảnh.
SHORTCUT_ACTIONS = {
    'record': ('Bắt đầu / dừng học', 'F8', 'global'),
    'panic': ('Dừng khẩn cấp', 'ESC', 'global'),
    'play': ('Chạy kịch bản đang chọn', '', 'global'),
    'stop_record': ('Dừng học và lưu (kể cả chạy nền)', '', 'global'),
    'add_profile': ('Tạo kịch bản mới', '', 'global'),
    'edit_profile': ('Sửa tên / phím của kịch bản đang chọn', '', 'global'),
    'delete_profile': ('Xóa kịch bản đang chọn', '', 'global'),
    'copy_script': ('Sao chép mã kịch bản', '', 'global'),
    'paste_script': ('Dán kịch bản', '', 'global'),
    'import_file': ('Nhập file kịch bản', 'Ctrl+O', 'global'),
    'export_file': ('Xuất file kịch bản', 'Ctrl+S', 'global'),
    'edit_delay': ('Sửa độ trễ bước đang chọn', '', 'global'),
    'delete_action': ('Xóa bước đang chọn', '', 'global'),
    'clear_actions': ('Xóa hết bước', '', 'global'),
    'wait_window': ('Thêm chờ cửa sổ', '', 'global'),
    'wait_image': ('Thêm chờ ảnh / nút', '', 'global'),
    'edit_condition': ('Sửa điều kiện đang chọn', '', 'global'),
    'details': ('Mở / đóng phần chi tiết các bước', '', 'global'),
    'prev_page': ('Trang bước trước', '', 'global'),
    'next_page': ('Trang bước sau', '', 'global'),
    **{f'work_{name}': (label, '', 'global') for name, label in (
        ('open', 'Công việc: mở phiên'), ('learn', 'Công việc: học trong tab'),
        ('stop', 'Công việc: dừng'), ('run', 'Công việc: chạy'),
        ('save', 'Công việc: lưu'), ('load', 'Công việc: nhập'),
        ('export', 'Công việc: chia sẻ'), ('send', 'Công việc: gửi chữ'),
        ('windows', 'Công việc: làm mới cửa sổ'))},
    **{f'speed_{value}': (f'Tốc độ {value}x', '', 'global')
       for value in tuple(str(i)+'.0' for i in range(1,11))},
    'toggle_movement': ('Bật / tắt bỏ qua di chuột thừa', '', 'global'),
    'toggle_countdown': ('Bật / tắt đếm ngược', '', 'global'),
    'settings': ('Mở cài đặt', '', 'global'),
    'help': ('Mở hướng dẫn', 'F1', 'global'),
    'hide': ('Thu vào khay', '', 'global'),
    'show': ('Mở lại giao diện từ khay', '', 'global'),
    'data_folder': ('Mở thư mục kịch bản', '', 'global'),
    'exit': ('Thoát ứng dụng', '', 'global'),
    'dialog_save': ('Lưu cài đặt / lưu điều kiện', 'Ctrl+Enter', 'dialog'),
    'dialog_cancel': ('Hủy / đóng hộp thoại', 'ESC', 'dialog'),
    'capture': ('Chụp vùng ảnh trong hộp điều kiện', '', 'dialog'),
    'toggle_tray': ('Bật / tắt đóng cửa sổ vào khay (trong Cài đặt)', '', 'dialog'),
    'restore_shortcuts': ('Khôi phục phím mặc định (trong Cài đặt)', '', 'dialog'),
}


def normalize_hotkey(text):
    if not text:
        return ''
    aliases = {'control': 'ctrl', 'escape': 'esc', 'return': 'enter', 'del': 'delete',
               'win': 'cmd', 'windows': 'cmd', 'pgup': 'page_up', 'pgdn': 'page_down',
               'backspace': 'backspace', 'spacebar': 'space', 'capslock': 'caps_lock'}
    parts = [aliases.get(part.strip().lower(), part.strip().lower()) for part in text.split('+')]
    return '+'.join(f'<{part}>' if len(part) > 1 else part for part in parts)


def parse_hotkey(text):
    if not text.strip():
        return frozenset()
    if any(not part.strip() for part in text.split('+')):
        raise ValueError('Thiếu tên phím; ví dụ đúng: F6 hoặc Ctrl+Shift+K.')
    keys = keyboard.HotKey.parse(normalize_hotkey(text))
    modifiers = {keyboard.Key.ctrl, keyboard.Key.alt, keyboard.Key.shift, keyboard.Key.cmd}
    if len([key for key in keys if key not in modifiers]) != 1:
        raise ValueError('Dùng một phím chính, có thể kèm Ctrl, Alt, Shift hoặc Win.')
    return frozenset(keys)


def key_identity(key):
    if isinstance(key, keyboard.Key):
        name = key.name
        for modifier in ('ctrl', 'alt', 'shift', 'cmd'):
            if name == modifier or name.startswith(modifier + '_'):
                return modifier
        return key.value.vk if key.value.vk is not None else name
    if getattr(key, 'vk', None) is not None:
        if 96 <= key.vk <= 105:
            return ord('0') + key.vk - 96
        return key.vk
    char = getattr(key, 'char', '') or ''
    if len(char) == 1 and char.isascii() and char.isalnum():
        return ord(char.upper())
    if len(char) == 1:
        scan = ctypes.windll.user32.VkKeyScanW
        scan.argtypes = [wintypes.WCHAR]
        scan.restype = ctypes.c_short
        value = scan(char)
        if value != -1:
            return value & 0xff
    return char


def hotkey_identities(text):
    return frozenset(key_identity(key) for key in parse_hotkey(text))


def validate_shortcuts(values, profiles, scopes=None):
    bindings = []
    for action, (label, _, scope) in SHORTCUT_ACTIONS.items():
        if scope != 'dialog' and action not in ('record', 'panic'):
            scope = (scopes or {}).get(action, 'app')
            if scope not in ('app', 'global'):
                raise ValueError(f'Phạm vi phím của {label} không hợp lệ.')
        text = values.get(action, '').strip()
        if action in ('record', 'panic') and not text:
            raise ValueError(f'Không được bỏ trống phím {label}.')
        try:
            keys = parse_hotkey(text)
        except ValueError as error:
            raise ValueError(f'{label}: phím "{text}" không hợp lệ. {error}') from error
        if keys:
            bindings.append((label, keys, scope))
    for profile in profiles:
        if profile.hotkey:
            bindings.append((f'Kịch bản "{profile.name}"', parse_hotkey(profile.hotkey), 'global'))
    for index, (label, keys, scope) in enumerate(bindings):
        for other_label, other_keys, other_scope in bindings[:index]:
            same_context = (scope == 'dialog') == (other_scope == 'dialog')
            if same_context and (keys <= other_keys or other_keys <= keys):
                raise ValueError(f'Phím của "{label}" trùng hoặc chồng tổ hợp với "{other_label}". Hãy đổi một trong hai.')


def tk_sequence(text):
    """Phím hộp thoại: cùng cú pháp với phím toàn cục, chuyển sang Tk."""
    parse_hotkey(text)
    names = {'ctrl': 'Control', 'alt': 'Alt', 'shift': 'Shift', 'cmd': 'Mod4',
             'esc': 'Escape', 'enter': 'Return', 'space': 'space', 'page_up': 'Prior',
             'page_down': 'Next', 'backspace': 'BackSpace', 'delete': 'Delete',
             'home': 'Home', 'end': 'End', 'up': 'Up', 'down': 'Down', 'left': 'Left',
             'right': 'Right', 'tab': 'Tab', 'insert': 'Insert', ',': 'comma', '.': 'period',
             '-': 'minus', '/': 'slash', '\\': 'backslash', ';': 'semicolon', "'": 'apostrophe',
             '[': 'bracketleft', ']': 'bracketright', '=': 'equal', '`': 'grave',
             '<': 'less', '>': 'greater', '!': 'exclam', '@': 'at', '#': 'numbersign'}
    names.update(caps_lock='Caps_Lock', num_lock='Num_Lock', scroll_lock='Scroll_Lock',
                 print_screen='Print', pause='Pause', menu='Menu')
    parts = [part[1:-1] if len(part) > 2 and part.startswith('<') else part
             for part in normalize_hotkey(text).split('+')]
    modifiers = [names[part] for part in parts if part in ('ctrl', 'alt', 'shift', 'cmd')]
    main = next(part for part in parts if part not in ('ctrl', 'alt', 'shift', 'cmd'))
    key = names.get(main, main.upper() if main.startswith('f') and main[1:].isdigit() else main)
    if 'shift' in parts and len(key) == 1:
        key = key.upper()
    return '<' + '-'.join(modifiers + [key]) + '>'
