"""Kiểm tra lưu bền vững, chia sẻ và điều kiện chờ; không bấm phím/chuột thật."""
import base64
import io
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
import zipfile

from PIL import Image
from core import MacroAction, MacroManager, MacroPlayer, MacroStorage, ScriptProfile
from conditions import condition_check, image_matches


def reference_png():
    output = io.BytesIO()
    Image.new('RGB', (12, 10), 'red').save(output, format='PNG')
    return base64.b64encode(output.getvalue()).decode('ascii')


class FeaturesTest(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).parent / 'build' / 'test-features'
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=parent)
        self.folder = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def profile(self):
        return ScriptProfile(name='Khám sức khoẻ', hotkey='Ctrl+F2', speed=1.5,
            loop_count=3, loop_delay=2, description='Mẫu chia sẻ', actions=[
                MacroAction('wait_window', 0, window_title='HIS', timeout=15),
                MacroAction('wait_image', 0.2, x=-100, y=40, image=reference_png(), timeout=5),
                MacroAction('key_press', 0, key='vk_65'),
                MacroAction('key_release', 0, key='vk_65')])

    def player(self):
        with patch('core.mouse.Controller'), patch('core.keyboard.Controller'):
            return MacroPlayer()

    def test_compressed_share_is_self_contained(self):
        original = self.profile()
        for suffix in ('.hocvet', '.json'):
            path = self.folder / ('shared' + suffix)
            MacroStorage.export_profile(original, path)
            restored = MacroStorage.import_profile(path)
            self.assertNotEqual(original.id, restored.id)
            data = original.to_dict()
            data['id'] = restored.id
            self.assertEqual(data, restored.to_dict())
        with zipfile.ZipFile(self.folder / 'shared.hocvet') as archive:
            self.assertEqual(archive.namelist(), ['script.json'])
            self.assertEqual(archive.getinfo('script.json').compress_type, zipfile.ZIP_DEFLATED)

    def test_legacy_json_keeps_metadata(self):
        path = self.folder / 'old.json'
        MacroStorage.save_to_file([MacroAction('key_press', 0, key='á')], path,
                                 metadata={'name': 'Mẫu cũ', 'hotkey': 'F11', 'speed': 2})
        restored = MacroStorage.import_profile(path)
        self.assertEqual((restored.name, restored.hotkey, restored.speed), ('Mẫu cũ', 'F11', 2))

    def test_invalid_or_oversized_import(self):
        for action in (MacroAction('wait_image', 0, image='bad', x=0, y=0),
                       MacroAction('wait_window', 0, window_title=''),
                       MacroAction('wait_window', 0, window_title='HIS', timeout=float('nan')),
                       MacroAction('unknown', 0)):
            profile = ScriptProfile(actions=[action])
            self.assertIsNone(MacroStorage.import_profile_from_string(MacroStorage.export_profile_to_string(profile)))
        path = self.folder / 'large.hocvet'
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('script.json', ' ' * 1000)
        with patch.object(MacroStorage, 'MAX_SCRIPT_BYTES', 500):
            with self.assertRaises(ValueError):
                MacroStorage.import_profile(path)

    def test_library_atomic_backup_and_recovery(self):
        path = self.folder / 'library.json'
        profile = self.profile()
        MacroStorage.save_library([profile], path, {'hotkey_record': 'F7'})
        profile.name = 'Mới'
        MacroStorage.save_library([profile], path)
        self.assertEqual(MacroStorage.load_library(str(path) + '.bak')[0][0].name, 'Khám sức khoẻ')
        path.write_text('{broken', encoding='utf-8')
        profiles, settings = MacroStorage.load_library(path)
        self.assertEqual(profiles[0].name, 'Khám sức khoẻ')
        self.assertEqual(settings['hotkey_record'], 'F7')
        MacroStorage.save_library(profiles, path, settings)
        self.assertEqual(MacroStorage.load_library(str(path) + '.bak')[0][0].name, 'Khám sức khoẻ')

    def test_failed_replace_preserves_previous_library(self):
        path = self.folder / 'library.json'
        MacroStorage.save_library([self.profile()], path)
        old = path.read_bytes()
        with patch('core.os.replace', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):
                MacroStorage.save_library([], path)
        self.assertEqual(path.read_bytes(), old)
        self.assertFalse(list(self.folder.glob('*.tmp')))

    def test_migration_and_update_from_another_folder(self):
        legacy_folder = self.folder / 'old-app'
        legacy_folder.mkdir()
        legacy = legacy_folder / 'scripts_library.json'
        MacroStorage.save_library([self.profile()], legacy)
        with patch.dict(os.environ, {'LOCALAPPDATA': str(self.folder / 'user-data')}), \
                patch('core.__file__', str(legacy_folder / 'core.py')):
            target = MacroStorage.default_library_path()
            self.assertTrue(legacy.is_file())
            self.assertEqual(MacroStorage.load_library(target)[0][0].name, 'Khám sức khoẻ')
            changed = self.profile()
            changed.name = 'Đã học thêm'
            MacroStorage.save_library([changed], target)
            with patch('core.__file__', str(self.folder / 'new-app' / 'core.py')), \
                    patch('core.Path.cwd', return_value=self.folder / 'other'):
                self.assertEqual(MacroStorage.default_library_path(), target)
                manager = MacroManager()
                self.assertEqual(manager.get_active_profile().name, 'Đã học thêm')

    def test_frozen_executable_migration(self):
        app_folder = self.folder / 'exe-folder'
        app_folder.mkdir()
        MacroStorage.save_library([self.profile()], app_folder / 'scripts_library.json')
        with patch.dict(os.environ, {'LOCALAPPDATA': str(self.folder / 'user')}), \
                patch('core.sys.frozen', True, create=True), \
                patch('core.sys.executable', str(app_folder / 'Học Vẹt.exe')):
            target = MacroStorage.default_library_path()
            self.assertEqual(MacroStorage.load_library(target)[0][0].name, 'Khám sức khoẻ')

    def test_window_title_condition(self):
        with patch('conditions.foreground_title', return_value='HIS — Khám sức khỏe'):
            self.assertTrue(condition_check(MacroAction('wait_window', 0, window_title='his'))())
            self.assertFalse(condition_check(MacroAction('wait_window', 0, window_title='Notepad'))())

    def test_image_match_and_capture_coordinates(self):
        image = Image.new('RGB', (12, 10), 'red')
        self.assertTrue(image_matches(image, image.copy(), 0))
        self.assertFalse(image_matches(image, Image.new('RGB', image.size, 'white'), .02))
        self.assertFalse(image_matches(image, Image.new('RGB', (1, 1), 'red'), .02))
        almost = image.copy()
        almost.putpixel((0, 0), (255, 0, 255))
        self.assertTrue(image_matches(image, almost, .02))
        self.assertFalse(image_matches(image, almost, 0))
        with patch('conditions.ImageGrab.grab', return_value=image) as capture:
            check = condition_check(self.profile().actions[1])
            self.assertTrue(check())
            capture.assert_called_once_with(bbox=(-100, 40, -88, 50), all_screens=True)

    def test_wait_success_retries_then_continues(self):
        player = self.player()
        actions = [MacroAction('wait_window', 0, window_title='HIS', timeout=1),
                   MacroAction('key_press', 0, key='vk_65')]
        player.on_finished = Mock()
        player.on_wait = Mock()
        check = Mock(side_effect=[False, True])
        with patch('core.condition_check', return_value=check), patch('core.play_sound'):
            player._run_playback(actions, 1, 1, 0)
        self.assertEqual(check.call_count, 2)
        player.keyboard_controller.press.assert_called_once()
        player.on_finished.assert_called_once_with(True, False)
        player.on_wait.assert_called_once()

    def test_timeout_does_not_execute_following_action(self):
        player = self.player()
        player.on_finished = Mock()
        actions = [MacroAction('wait_window', 0, window_title='HIS', timeout=.01),
                   MacroAction('key_press', 0, key='vk_65')]
        with patch('core.condition_check', return_value=lambda: False), patch('core.play_sound'):
            player._run_playback(actions, 10, 1, 0)
        self.assertIn('Hết', player.last_error)
        player.keyboard_controller.press.assert_not_called()
        player.on_finished.assert_called_once_with(False, True)

    def test_stop_during_final_wait_is_not_success(self):
        player = self.player()
        player.on_finished = Mock()
        action = MacroAction('wait_window', 0, window_title='HIS', timeout=30)
        with patch('core.condition_check', return_value=lambda: False), patch('core.play_sound'):
            player.is_playing = True
            thread = threading.Thread(target=player._run_playback, args=([action], 1, 1, 0))
            thread.start()
            start = time.monotonic()
            player.stop()
            thread.join(1)
            self.assertFalse(thread.is_alive())
            self.assertLess(time.monotonic() - start, 1)
        player.on_finished.assert_called_once_with(False, True)
        self.assertEqual(player.last_error, '')

    def test_shortcut_validation_and_persistence(self):
        from shortcuts import parse_hotkey
        path = str(self.folder / 'library.json')
        manager = MacroManager(path)
        values = manager.shortcut_values()
        values.update(record='Ctrl+Alt+R', panic='Ctrl+Alt+X', wait_image='F6', dialog_save='Alt+Enter')
        scopes = dict(manager.button_hotkey_scopes, wait_image='global')
        manager.apply_shortcuts(values, scopes)
        manager.save_library()
        restored = MacroManager(path)
        self.assertEqual(restored.hotkey_record_str, 'CTRL+ALT+R')
        self.assertEqual(restored.button_hotkeys['wait_image'], 'F6')
        self.assertEqual(restored.button_hotkey_scopes['wait_image'], 'global')
        self.assertEqual(parse_hotkey('Control+Shift+K'), parse_hotkey('Shift+Ctrl+K'))
        self.assertEqual(parse_hotkey('Escape'), parse_hotkey('ESC'))
        for bad in ('Ctrl+', 'Ctrl++A', 'F999', 'Ctrl', 'A+B'):
            with self.assertRaises(ValueError, msg=bad):
                parse_hotkey(bad)
        for action, value in (('help', 'F9'), ('wait_window', 'Shift+F6'),
                              ('wait_window', 'Alt+Ctrl+R'), ('record', '')):
            invalid = dict(values, **{action: value})
            with self.assertRaises(ValueError):
                manager.apply_shortcuts(invalid, scopes)
        self.assertEqual(manager.button_hotkeys['wait_image'], 'F6')

    def test_global_commands_use_saved_scope_and_ignore_injected_keys(self):
        manager = MacroManager(str(self.folder / 'library.json'))
        manager.button_hotkeys.update(wait_image='F6', wait_window='F7')
        manager.button_hotkey_scopes.update(wait_image='global', wait_window='app')
        manager.on_command = Mock()
        with patch('core.keyboard.GlobalHotKeys') as listener:
            manager.start_global_hotkeys()
            mapping = listener.call_args.args[0]
            self.assertIn('<f6>', mapping)
            self.assertNotIn('<f7>', mapping)
            event_filter = listener.call_args.kwargs['win32_event_filter']
            from types import SimpleNamespace
            self.assertFalse(event_filter(0x100, SimpleNamespace(flags=0x10)))
            mapping['<f6>']()
            manager.on_command.assert_called_once_with('wait_image')
            manager.state = MacroManager.STATE_PLAYING
            mapping['<f6>']()
            self.assertEqual(manager.on_command.call_count, 1)
            manager.shortcuts_suspended = True
            listener.reset_mock()
            manager.start_global_hotkeys()
            listener.assert_not_called()

    def test_record_stop_combination_is_not_recorded(self):
        from core import MacroRecorder
        from pynput import keyboard
        recorder = MacroRecorder()
        recorder.control_hotkeys = ['Ctrl+Alt+R', 'ESC']
        with patch('core.keyboard.Listener'), patch('core.mouse.Listener'), patch('core.play_sound'):
            recorder.start()
            # Chữ r bình thường vẫn được ghi.
            recorder._on_key_press(keyboard.KeyCode.from_vk(82, char='r'))
            recorder._on_key_release(keyboard.KeyCode.from_vk(82, char='r'))
            recorder._on_key_press(keyboard.Key.ctrl_l)
            recorder._on_key_press(keyboard.Key.alt_l)
            recorder._on_key_press(keyboard.KeyCode.from_vk(82, char='r'))
            recorder._on_key_release(keyboard.KeyCode.from_vk(82, char='r'))
            recorder._on_key_release(keyboard.Key.alt_l)
            recorder._on_key_release(keyboard.Key.ctrl_l)
            actions = recorder.stop()
        self.assertEqual([(a.action_type, a.key) for a in actions], [('key_press', 'vk_82'), ('key_release', 'vk_82')])


class UITest(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        import ui
        self.ui = ui
        parent = Path(__file__).parent / 'build' / 'test-features'
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.hotkeys = patch.object(MacroManager, 'start_global_hotkeys')
        self.hotkeys.start()
        self.addCleanup(self.hotkeys.stop)
        with patch.object(MacroStorage, 'default_library_path', return_value=str(Path(self.temporary.name) / 'library.json')), \
                patch.object(ui.HocVetApp, '_setup_system_tray'):
            self.app = ui.HocVetApp(self.root)
        self.profile = ScriptProfile(name='Kịch bản giữ lại', actions=[MacroAction('key_press', 0, key='a')])
        self.app.manager.profiles = [self.profile]
        self.app.manager.active_profile_id = self.profile.id
        self.app._refresh_profile_deck()

    def test_condition_dialog_inserts_before_selection(self):
        import tkinter as tk
        from tkinter import ttk
        first = self.app.tree.get_children()[0]
        self.app.tree.selection_set(first)
        self.app._cmd_add_condition('wait_window')
        dialog = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel))
        box = dialog.body
        entries = [w for w in box.winfo_children() if isinstance(w, ttk.Entry)]
        entries[0].insert(0, 'HIS')
        entries[1].delete(0, 'end')
        entries[1].insert(0, '20')
        save = next(w for w in dialog.footer.winfo_children() if isinstance(w, ttk.Button) and w.cget('text') == 'Lưu điều kiện')
        save.invoke()
        self.assertEqual([a.action_type for a in self.profile.actions], ['wait_window', 'key_press'])
        self.assertEqual(self.profile.actions[0].window_title, 'HIS')
        self.assertEqual(self.profile.actions[0].timeout, 20)
        loaded = MacroStorage.load_library(self.app.manager.library_path)[0]
        self.assertEqual(loaded[0].actions[0].window_title, 'HIS')

    def test_import_adds_profile_and_clears_conflicting_hotkey(self):
        shared = ScriptProfile(name='Được chia sẻ', hotkey=self.profile.hotkey)
        with patch('ui.messagebox.showinfo'):
            self.app._accept_import(shared)
        self.assertEqual(len(self.app.manager.profiles), 2)
        self.assertEqual(self.app.manager.profiles[0].id, self.profile.id)
        self.assertEqual(shared.hotkey, '')
        self.assertEqual(self.app.manager.active_profile_id, shared.id)

    def test_capture_region_embeds_selected_pixels_and_can_cancel(self):
        import tkinter as tk
        from screen_capture import capture_region
        from conditions import decode_reference
        result = Mock()
        with patch('screen_capture.ImageGrab.grab', return_value=Image.new('RGB', (200, 100), 'red')):
            capture_region(self.root, result)
            overlay = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel))
            canvas = overlay.winfo_children()[0]
            self.root.update()
            canvas.event_generate('<ButtonPress-1>', x=10, y=20)
            canvas.event_generate('<B1-Motion>', x=50, y=70)
            canvas.event_generate('<ButtonRelease-1>', x=50, y=70)
            self.root.update()
            result.assert_called_once()
            x, y, encoded = result.call_args.args[0]
            self.assertEqual(decode_reference(encoded).size, (40, 50))
            self.assertEqual(decode_reference(encoded).getpixel((0, 0)), (255, 0, 0))
            result.reset_mock()
            capture_region(self.root, result)
            overlay = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel))
            self.root.update()
            overlay.event_generate('<Escape>')
            self.root.update()
            result.assert_called_once_with(None)

    def test_settings_records_validates_saves_and_rebinds_shortcuts(self):
        import tkinter as tk
        from tkinter import ttk
        from shortcuts import SHORTCUT_ACTIONS
        self.root.deiconify()
        self.root.update()
        self.app._cmd_open_settings()
        self.root.update()
        dialog = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel))
        self.assertTrue(self.app.manager.shortcuts_suspended)
        self.assertEqual(set(self.app.shortcut_entries), set(SHORTCUT_ACTIONS))
        self.assertEqual(set(self.app._shortcut_commands),
                         {name for name, (_, _, scope) in SHORTCUT_ACTIONS.items()
                          if scope != 'dialog' and name not in ('record', 'panic')})
        def button(widget, text):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button) and child.cget('text') == text:
                    return child
                found = button(child, text)
                if found:
                    return found
        entries = self.app.shortcut_entries
        entries['help'].delete(0, 'end')
        entries['help'].insert(0, 'F9')
        with patch('ui.messagebox.showerror') as error:
            button(dialog, 'Lưu cài đặt').invoke()
            error.assert_called_once()
        self.assertTrue(dialog.winfo_exists())
        self.assertEqual(self.app.manager.button_hotkeys['help'], 'F1')
        # Ghi trực tiếp một tổ hợp vào dòng Thêm chờ cửa sổ.
        entry = entries['wait_window']
        rows = entry.master
        row = entry.grid_info()['row']
        capture = next(w for w in rows.grid_slaves(row=row) if isinstance(w, ttk.Button))
        capture.invoke()
        entry.focus_force()
        self.root.update()
        entry.event_generate('<KeyPress>', keysym='j', state=4)
        self.root.update()
        self.assertEqual(entry.get(), 'Ctrl+J')
        entries['help'].delete(0, 'end')
        entries['help'].insert(0, 'F6')
        button(dialog, 'Lưu cài đặt').invoke()
        self.root.update()
        self.assertFalse(self.app.manager.shortcuts_suspended)
        restored = MacroManager(self.app.manager.library_path)
        self.assertEqual(restored.button_hotkeys['help'], 'F6')
        with patch.object(self.app, '_dispatch_shortcut') as dispatch:
            self.root.deiconify()
            self.root.update()
            self.root.focus_force()
            self.root.event_generate('<F6>')
            self.root.update()
            dispatch.assert_called_once_with('help')
            self.root.event_generate('<F1>')
            self.root.update()
            self.assertEqual(dispatch.call_count, 1)

    def test_settings_failed_save_restores_previous_values(self):
        import tkinter as tk
        from tkinter import ttk
        self.app._cmd_open_settings()
        self.root.update()
        dialog = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel))
        entry = self.app.shortcut_entries['help']
        entry.delete(0, 'end')
        entry.insert(0, 'F6')
        buttons = dialog.footer
        save = next(w for w in buttons.winfo_children() if isinstance(w, ttk.Button) and w.cget('text') == 'Lưu cài đặt')
        with patch.object(self.app.manager, 'save_library', side_effect=OSError('disk unavailable')), patch('ui.messagebox.showerror'):
            save.invoke()
        self.assertEqual(self.app.manager.button_hotkeys['help'], 'F1')
        dialog.destroy()


if __name__ == '__main__':
    unittest.main()
