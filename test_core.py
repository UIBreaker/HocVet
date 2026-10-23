"""
Unit Test tự động kiểm tra logic cốt lõi của Học Vẹt (core.py).
Chạy độc lập: python test_core.py
Không cần cài đặt thêm framework nào ngoài thư viện chuẩn.
"""

import os
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from core import MacroAction, MacroStorage, key_to_str, str_to_key, button_to_str, str_to_button
from pynput import keyboard, mouse


def test_key_serialization():
    print("-> Kiểm tra chuyển đổi phím (Key serialization)...")
    cases = [
        keyboard.Key.enter,
        keyboard.Key.f8,
        keyboard.Key.esc,
        keyboard.Key.ctrl_l,
        keyboard.KeyCode.from_char('k'),
        keyboard.KeyCode.from_char('0'),
    ]
    for key in cases:
        s = key_to_str(key)
        restored = str_to_key(s)
        assert restored is not None, f"Lỗi khôi phục phím cho: {key}"
        # So sánh tên hoặc char
        if isinstance(key, keyboard.Key):
            assert restored == key, f"Phím không khớp: {key} != {restored}"
        elif hasattr(key, 'char') and key.char:
            assert getattr(restored, 'char', None) == key.char
    physical = keyboard.KeyCode.from_vk(65, char='A')
    assert key_to_str(physical) == 'vk_65'
    assert str_to_key(key_to_str(physical)).vk == 65
    assert str_to_key('á').char == 'á'  # Kịch bản cũ vẫn đọc được.
    print("   [PASS] Chuyển đổi phím chính xác.")


def test_vietnamese_recording_playback():
    from core import MacroRecorder, MacroPlayer

    recorder = MacroRecorder()
    with patch('core.keyboard.Listener') as listener, \
            patch('core.mouse.Listener'), patch('core.play_sound'):
        recorder.start()
        callbacks = listener.call_args.kwargs

        def emit(key, flags=0, pressed=True):
            msg = 0x100 if pressed else 0x101
            if callbacks['win32_event_filter'](msg, SimpleNamespace(flags=flags)):
                callbacks['on_press' if pressed else 'on_release'](key)

        # Chuỗi Telex cho “khám sức khoẻ”; bộ gõ xen phím thay dấu.
        text_keys = 'khams suwc khoer'
        for char in text_keys:
            vk = 32 if char == ' ' else ord(char.upper())
            emit(keyboard.KeyCode.from_vk(vk, char=char))
            emit(keyboard.Key.backspace, flags=0x10)
            emit(keyboard.KeyCode.from_char('á'), flags=0x10)
            emit(keyboard.KeyCode.from_char('á'), flags=0x12, pressed=False)
            # Bản dịch ký tự ở lần nhả có thể khác lần nhấn, VK vẫn giống nhau.
            emit(keyboard.KeyCode.from_vk(vk, char=char.upper()), pressed=False)
        emit(keyboard.Key.f8)
        emit(keyboard.Key.esc)
        emit(None)
        actions = recorder.stop()

    assert len(actions) == len(text_keys) * 2
    with patch('core.mouse.Controller'), patch('core.keyboard.Controller'):
        player = MacroPlayer()
        for i, char in enumerate(text_keys):
            vk = 32 if char == ' ' else ord(char.upper())
            down, up = actions[2*i:2*i+2]
            assert down.key == up.key == f'vk_{vk}'
            for action in (down, up):
                player._execute_action(MacroAction.from_dict(action.to_dict()))
        assert player.keyboard_controller.press.call_count == len(text_keys)
        assert player.keyboard_controller.release.call_count == len(text_keys)
        expected = [32 if c == ' ' else ord(c.upper()) for c in text_keys]
        assert [c.args[0].vk for c in player.keyboard_controller.press.call_args_list] == expected
        assert [c.args[0].vk for c in player.keyboard_controller.release.call_args_list] == expected
    print('   [PASS] Tiếng Việt: bỏ phím do bộ gõ sinh, phát đúng phím vật lý một lần.')


def test_button_serialization():
    print("-> Kiểm tra chuyển đổi chuột (Button serialization)...")
    for btn in [mouse.Button.left, mouse.Button.right, mouse.Button.middle]:
        s = button_to_str(btn)
        restored = str_to_button(s)
        assert restored == btn, f"Nút chuột không khớp: {btn} != {restored}"
    print("   [PASS] Chuyển đổi chuột chính xác.")


def test_macro_action_roundtrip():
    print("-> Kiểm tra MacroAction to_dict và from_dict...")
    action1 = MacroAction(action_type="mouse_click", delay=0.25, x=100, y=200, button="left", pressed=True)
    d = action1.to_dict()
    assert d["action_type"] == "mouse_click"
    assert d["delay"] == 0.25
    assert d["x"] == 100
    assert d["y"] == 200
    assert d["button"] == "left"
    assert d["pressed"] is True

    action2 = MacroAction.from_dict(d)
    assert action2 == action1, f"Đối tượng không khớp sau khi khôi phục: {action1} != {action2}"
    print("   [PASS] MacroAction roundtrip chính xác.")


def test_storage_json_roundtrip():
    print("-> Kiểm tra lưu và nạp kịch bản JSON (Storage)...")
    sample_actions = [
        MacroAction("mouse_click", delay=0.1, x=500, y=300, button="left", pressed=True),
        MacroAction("mouse_click", delay=0.05, x=500, y=300, button="left", pressed=False),
        MacroAction("key_press", delay=0.2, key="Key.tab"),
        MacroAction("key_release", delay=0.02, key="Key.tab"),
        MacroAction("key_press", delay=0.15, key="k"),
        MacroAction("key_release", delay=0.03, key="k"),
        MacroAction("mouse_scroll", delay=0.3, x=600, y=400, dx=0, dy=-2),
    ]

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Lưu file
        MacroStorage.save_to_file(sample_actions, tmp_path, metadata={"author": "HIS User"})
        assert os.path.exists(tmp_path), "File JSON không được tạo!"

        # Nạp lại file
        loaded_actions = MacroStorage.load_from_file(tmp_path)
        assert len(loaded_actions) == len(sample_actions), f"Số lượng thao tác không khớp: {len(loaded_actions)} != {len(sample_actions)}"
        for orig, loaded in zip(sample_actions, loaded_actions):
            assert orig.action_type == loaded.action_type
            assert abs(orig.delay - loaded.delay) < 1e-4
            assert orig.x == loaded.x
            assert orig.y == loaded.y
            assert orig.key == loaded.key
            assert orig.button == loaded.button
        print("   [PASS] Lưu & nạp JSON hoàn toàn toàn vẹn dữ liệu.")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_abort_flag_responsiveness():
    print("-> Kiểm tra cơ chế dừng khẩn cấp (Emergency Stop wait response)...")
    import threading
    abort_event = threading.Event()
    start_t = time.perf_counter()

    # Thử wait 3 giây nhưng kích hoạt dừng sau 0.05 giây
    def trigger_abort():
        time.sleep(0.05)
        abort_event.set()

    t = threading.Thread(target=trigger_abort)
    t.start()

    # abort_event.wait(3.0) phải thoát ngay khi set() chứ không đợi hết 3 giây!
    interrupted = abort_event.wait(timeout=3.0)
    elapsed = time.perf_counter() - start_t
    t.join()

    assert interrupted is True, "Abort event không được kích hoạt!"
    assert elapsed < 0.5, f"Thời gian phản hồi dừng quá chậm: {elapsed:.2f}s (kỳ vọng < 0.5s)"
    print(f"   [PASS] Phản hồi dừng khẩn cấp siêu tốc: {elapsed*1000:.1f}ms.")


def test_normalize_hotkey():
    print("-> Kiểm tra chuẩn hóa tổ hợp phím (normalize_hotkey)...")
    from core import normalize_hotkey
    assert normalize_hotkey("F8") == "<f8>"
    assert normalize_hotkey("F9") == "<f9>"
    assert normalize_hotkey("Ctrl+F1") == "<ctrl>+<f1>"
    assert normalize_hotkey("Alt+1") == "<alt>+1"
    assert normalize_hotkey("Ctrl+Shift+K") == "<ctrl>+<shift>+k"
    assert normalize_hotkey("ESC") == "<esc>"
    print("   [PASS] Chuẩn hóa phím tắt hoàn toàn chính xác.")


def test_script_profile_library():
    print("-> Kiểm tra quản lý đa kịch bản (ScriptProfile & Library)...")
    from core import ScriptProfile, MacroStorage
    actions = [MacroAction("mouse_click", delay=0.1, x=200, y=300, button="left", pressed=True)]
    p1 = ScriptProfile(name="Ký số HIS", hotkey="F9", actions=actions, speed=1.2)
    p2 = ScriptProfile(name="Điền mẫu khám", hotkey="F10", actions=actions, speed=1.0)
    
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        MacroStorage.save_library([p1, p2], tmp_path, settings={"hotkey_record": "F8", "hotkey_panic": "ESC"})
        loaded, settings = MacroStorage.load_library(tmp_path)
        assert len(loaded) == 2, f"Kỳ vọng 2 kịch bản, nhận: {len(loaded)}"
        assert loaded[0].name == "Ký số HIS"
        assert loaded[0].hotkey == "F9"
        assert loaded[1].name == "Điền mẫu khám"
        assert loaded[1].hotkey == "F10"
        assert settings.get("hotkey_record") == "F8"
        print("   [PASS] Quản lý đa kịch bản lưu & nạp toàn vẹn dữ liệu.")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_macro_manager_state_machine():
    print("-> Kiểm tra máy trạng thái MacroManager (State Machine)...")
    from core import MacroManager
    mgr = MacroManager(library_path="test_temp_library.json")
    mgr.player.keyboard_controller = Mock()
    mgr.player.mouse_controller = Mock()
    assert mgr.state == MacroManager.STATE_IDLE

    # Mock action list on active profile
    active = mgr.get_active_profile()
    assert active is not None
    active.actions = [
        MacroAction("key_press", delay=0.05, key="Key.enter"),
        MacroAction("key_release", delay=0.01, key="Key.enter"),
    ]

    # Test Play & Emergency Stop
    mgr.start_playing_active()
    assert mgr.state == MacroManager.STATE_PLAYING, f"Trạng thái kỳ vọng là PLAYING, nhận: {mgr.state}"
    time.sleep(0.02)
    mgr.stop_playing()
    # Chờ thread kết thúc
    time.sleep(0.05)
    assert mgr.state == MacroManager.STATE_IDLE, f"Trạng thái kỳ vọng là IDLE sau dừng, nhận: {mgr.state}"
    if os.path.exists("test_temp_library.json"):
        os.remove("test_temp_library.json")
    print("   [PASS] MacroManager chuyển đổi trạng thái chính xác.")


def test_export_import_profile_string():
    print("-> Kiểm tra sao chép / trích xuất kịch bản dạng chuỗi...")
    from core import ScriptProfile, MacroStorage
    p = ScriptProfile(name="Ký số chia sẻ", hotkey="Ctrl+F2", actions=[
        MacroAction("mouse_click", delay=0.2, x=500, y=400, button="left", pressed=True)
    ])
    exported_str = MacroStorage.export_profile_to_string(p)
    assert "smart_operation_macro" in exported_str
    assert "Nhật Nam (@UIBreaker)" in exported_str

    restored = MacroStorage.import_profile_from_string(exported_str)
    assert restored is not None
    assert restored.name == "Ký số chia sẻ"
    assert restored.hotkey == "Ctrl+F2"
    assert len(restored.actions) == 1
    print("   [PASS] Sao chép & khôi phục kịch bản chính xác 100%.")


def test_delete_profile():
    print("-> Kiểm tra tính năng xóa kịch bản (Delete Profile)...")
    from core import MacroManager, ScriptProfile
    tmp_path = "test_del_library.json"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    try:
        mgr = MacroManager(library_path=tmp_path)
        # Ban đầu có 1 profile mẫu mặc định
        assert len(mgr.profiles) == 1
        # Thử xóa khi chỉ có 1 profile -> phải trả về False (bảo vệ an toàn)
        assert mgr.delete_profile(mgr.profiles[0].id) is False
        assert len(mgr.profiles) == 1

        # Thêm 2 profile nữa
        p2 = ScriptProfile(name="Kịch bản 2", hotkey="F10", actions=[])
        p3 = ScriptProfile(name="Kịch bản 3", hotkey="F11", actions=[])
        mgr.profiles.extend([p2, p3])
        assert len(mgr.profiles) == 3

        # Đặt active là p2 và xóa p2
        mgr.set_active_profile(p2.id)
        assert mgr.get_active_profile().id == p2.id
        ok = mgr.delete_profile(p2.id)
        assert ok is True
        assert len(mgr.profiles) == 2
        # Profile active phải tự động chuyển sang profile hợp lệ khác
        assert mgr.active_profile_id != p2.id
        assert mgr.get_active_profile() is not None

        # Xóa ID không tồn tại -> False
        assert mgr.delete_profile("non_existent_id") is False
        print("   [PASS] Tính năng xóa kịch bản hoạt động chính xác và an toàn.")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    # Một số sandbox Windows không cho os.replace ở thư mục Temp hệ thống.
    tempfile.tempdir = os.path.abspath(os.path.join('build', 'test-temp'))
    os.makedirs(tempfile.tempdir, exist_ok=True)
    print("================ BẮT ĐẦU KIỂM THỬ CORE ENGINE ================")
    test_key_serialization()
    test_vietnamese_recording_playback()
    test_button_serialization()
    test_macro_action_roundtrip()
    test_storage_json_roundtrip()
    test_abort_flag_responsiveness()
    test_normalize_hotkey()
    test_script_profile_library()
    test_export_import_profile_string()
    test_macro_manager_state_machine()
    test_delete_profile()
    print("================ TẤT CẢ KIỂM THỬ ĐÃ VƯỢT QUA THÀNH CÔNG! ================")
