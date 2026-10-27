"""Kiểm tra lưu bền vững, chia sẻ và điều kiện chờ; không bấm phím/chuột thật."""
import base64
import io
import gc
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
    def test_mouse_activation_disables_start_stop_hotkeys_and_persists(self):
        path = str(self.folder / 'activation.json')
        manager = MacroManager(path)
        manager.button_hotkeys.update(play='F6', stop_record='2')
        manager.button_hotkey_scopes['play'] = 'global'
        manager.on_record_toggle = Mock()
        manager.on_command = Mock()
        manager.on_panic = Mock()
        with patch('core.keyboard.GlobalHotKeys') as listener:
            manager.start_global_hotkeys()
            listener.assert_not_called()
        manager._on_hotkey_toggle_record()
        manager._on_command_hotkey('stop_record')
        manager._on_hotkey_panic()
        manager.on_record_toggle.assert_not_called()
        manager.on_command.assert_not_called()
        manager.on_panic.assert_not_called()
        manager.save_library()
        self.assertEqual(MacroManager(path).script_activation, 'mouse')
        manager.script_activation = 'hotkey'
        manager.save_library()
        restored = MacroManager(path)
        self.assertEqual(restored.script_activation, 'hotkey')
        with patch('core.keyboard.GlobalHotKeys') as listener:
            restored.start_global_hotkeys()
            self.assertIn('<f9>', listener.call_args.args[0])
            self.assertIn('2', listener.call_args.args[0])

    def test_playback_does_not_inject_input_into_own_panel(self):
        player = self.player()
        player.protect_mouse = Mock(return_value=True)
        for kind in ('mouse_click', 'mouse_move', 'mouse_scroll'):
            with self.assertRaises(RuntimeError):
                player._execute_action(MacroAction(kind, 0, x=12, y=34, pressed=True))
        player.mouse_controller.press.assert_not_called()
        player.mouse_controller.scroll.assert_not_called()
        player.protect_keyboard = Mock(return_value=True)
        with self.assertRaises(RuntimeError):
            player._execute_action(MacroAction('key_press', 0, key='a'))
        player.keyboard_controller.press.assert_not_called()

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
        manager.script_activation = 'hotkey'
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

    def test_stop_digit_is_global_after_loading_old_app_scope(self):
        path = str(self.folder / 'old-settings.json')
        MacroStorage.save_library([self.profile()], path,
            {'button_hotkeys': {'stop_record': '2'}, 'button_hotkey_scopes': {'stop_record': 'app'}})
        manager = MacroManager(path)
        manager.script_activation = 'hotkey'
        self.assertEqual(manager.button_hotkey_scopes['stop_record'], 'global')
        with patch('core.keyboard.GlobalHotKeys') as listener:
            manager.start_global_hotkeys()
            self.assertIn('2', listener.call_args.args[0])

    def test_new_profile_play_hotkey_works_after_learning_without_hook_restart(self):
        manager = MacroManager(str(self.folder / 'library.json'))
        manager.script_activation = 'hotkey'
        profile = ScriptProfile(name='Mới tạo', hotkey='F9', actions=[])
        manager.profiles = [profile]
        with patch('core.keyboard.GlobalHotKeys') as listener, patch.object(manager, 'start_playing_profile') as play:
            manager.start_global_hotkeys()
            activate = listener.call_args.args[0]['<f9>']
            activate()
            play.assert_not_called()
            profile.actions = [MacroAction('key_press', 0, key='a')]
            activate()
            play.assert_called_once_with(profile)

    def test_ignore_own_mouse_events_and_cache_hotkey_parsing(self):
        from core import MacroRecorder
        from pynput import keyboard, mouse
        recorder = MacroRecorder(record_movement=True)
        recorder.ignore_mouse = Mock(return_value=True)
        with patch('core.keyboard.Listener'), patch('core.mouse.Listener'), patch('core.play_sound'):
            recorder.start()
            recorder._on_mouse_click(20, 30, mouse.Button.left, True)
            recorder._on_mouse_scroll(20, 30, 0, 1)
            recorder._on_mouse_move(20, 30)
            with patch('core.hotkey_identities', side_effect=AssertionError('reparsed in hot path')):
                recorder._on_key_press(keyboard.KeyCode.from_vk(65, char='a'))
                recorder._on_key_release(keyboard.KeyCode.from_vk(65, char='a'))
            self.assertEqual([a.action_type for a in recorder.stop()], ['key_press', 'key_release'])

    def test_own_window_filter_uses_process_identity(self):
        from ui import HocVetApp
        def own_process(handle, pointer):
            pointer._obj.value = os.getpid()
        with patch('ui.ctypes.windll.user32.WindowFromPoint', return_value=123), \
                patch('ui.ctypes.windll.user32.GetWindowThreadProcessId', side_effect=own_process):
            self.assertTrue(HocVetApp._is_own_window(10, 20))
        def other_process(handle, pointer):
            pointer._obj.value = os.getpid()+1
        with patch('ui.ctypes.windll.user32.WindowFromPoint', return_value=456), \
                patch('ui.ctypes.windll.user32.GetWindowThreadProcessId', side_effect=other_process):
            self.assertFalse(HocVetApp._is_own_window(10, 20))


class UITest(unittest.TestCase):
    def test_speed_scale_marks_every_level_and_repeat_inputs_keep_values(self):
        from types import SimpleNamespace
        slider=self.app.speed_slider
        self.root.update_idletasks()
        labels=[slider.itemcget(item,'text') for item in slider.find_withtag('speed_tick_label')]
        self.assertEqual(labels,[f'{n}×' for n in range(1,11)])
        with patch.object(slider,'winfo_width',return_value=600):
            slider.set(1.5)
            thumb=slider.coords(slider.find_withtag('speed_thumb')[0])
            self.assertAlmostEqual((thumb[0]+thumb[2])/2,24+552/18)
            slider._drag(SimpleNamespace(x=576))
        self.assertEqual(self.app.speed_readout.cget('text'),'10×')
        self.app.loop_count_var.set('0')
        self.app.loop_delay_var.set('2.5')
        self.assertEqual(self.app._parse_loop_count(),0)
        self.assertEqual(self.app._parse_loop_delay(),2.5)

    def test_panel_repeat_number_opens_visible_editor_with_hidden_main(self):
        import tkinter as tk
        from tkinter import ttk
        self.app._hide_to_tray()
        self.root.update()
        def edit():
            dialog=next(w for w in self.app.record_notice.window.winfo_children() if isinstance(w,tk.Toplevel))
            self.assertTrue(dialog.winfo_ismapped())
            entry=next(w for w in dialog.body.winfo_children() if isinstance(w,ttk.Entry))
            entry.delete(0,'end');entry.insert(0,'12')
            next(w for w in dialog.footer.winfo_children() if isinstance(w,ttk.Button) and w.cget('text')=='Lưu').invoke()
        self.root.after(40,edit)
        self.app._set_panel_repeat(self.profile.id)
        self.assertEqual(self.profile.loop_count,12)

    def _destroy_ui(self):
        self.root.destroy()
        self.app = None
        self.root = None
        gc.collect()

    def test_panel_repeat_edits_selected_profile_only_and_persists(self):
        second=ScriptProfile(name='Công việc hai',actions=[MacroAction('key_press',0,key='b')])
        self.app.manager.profiles.append(second)
        self.app._set_panel_repeat(second.id,'17')
        self.assertEqual(second.loop_count,17)
        self.assertEqual(self.profile.loop_count,1)
        self.assertEqual(self.app.manager.active_profile_id,self.profile.id)
        restored=MacroManager(self.app.manager.library_path)
        self.assertEqual(next(p.loop_count for p in restored.profiles if p.id==second.id),17)
        self.app._set_panel_repeat(self.profile.id,0)
        self.assertEqual(self.app.loop_count_var.get(),'0')
        self.app.manager.external_busy=True
        self.app._set_panel_repeat(second.id,4)
        self.assertEqual(second.loop_count,17)

    def test_panel_repeat_validation_cancel_save_failure_and_size_persistence(self):
        with patch.object(self.app,'notify_app'),patch.object(self.ui.simpledialog,'askstring',return_value=None):
            self.app._set_panel_repeat(self.profile.id)
            for value in ('-1','2.5','abc'):self.app._set_panel_repeat(self.profile.id,value)
        self.assertEqual(self.profile.loop_count,1)
        with patch.object(self.app.manager,'save_library',side_effect=OSError('disk full')),patch.object(self.app,'notify_app'):
            self.app._set_panel_repeat(self.profile.id,8)
            self.app._save_panel_size(480,680)
        self.assertEqual(self.profile.loop_count,1)
        self.assertIsNone(self.app.manager.panel_size)
        self.app._save_panel_size(480,680)
        self.assertEqual(MacroManager(self.app.manager.library_path).panel_size,[480,680])

    def test_keyboard_mode_disables_mouse_activation_and_mouse_mode_unbinds_all_hotkeys(self):
        self.app._handle_state_ui(MacroManager.STATE_IDLE)
        for button in (self.app.btn_rec,self.app.btn_play,self.app.btn_stop,self.app.btn_panic):
            self.assertEqual(button.state,'disabled')
        self.assertTrue(all('disabled' in b.state() for b in self.app.workspace.activation_buttons))
        self.app._cmd_start_playing()
        self.app._cmd_start_recording()
        self.app._run_from_panel(self.profile.id)
        self.assertIsNone(self.app._pending_play)
        self.assertEqual(self.app.manager.state,MacroManager.STATE_IDLE)
        self.app._hide_to_tray()
        self.assertTrue(all('disabled' in b.state() for b in self.app.record_notice.run_buttons))
        self.app.manager.script_activation='mouse'
        self.app._install_shortcuts()
        self.assertEqual(self.app._shortcut_bindings,[])
        self.assertEqual(self.app._settings_bindings,[])

    def test_mouse_mode_keeps_old_stop_digit_as_text_and_panel_stop_saves(self):
        from pynput import keyboard
        app=self.app
        app.manager.script_activation='mouse'
        app.manager.button_hotkeys['stop_record']='2'
        app.countdown_var.set(False)
        with patch('core.keyboard.Listener'),patch('core.mouse.Listener'),patch('core.play_sound'):
            app._cmd_start_recording()
            recorder=app.manager.recorder
            recorder.ignore_keyboard=Mock(return_value=False)
            digit=keyboard.KeyCode.from_vk(50,char='2')
            recorder._on_key_press(digit);recorder._on_key_release(digit)
            self.assertEqual(app.manager.state,MacroManager.STATE_RECORDING)
            app._cmd_emergency_stop()
            self.assertEqual(app.manager.state,MacroManager.STATE_IDLE)
            self.assertEqual([a.key for a in self.profile.actions],['vk_50','vk_50'])

    def test_profile_hotkey_uses_ui_hide_before_play_path(self):
        with patch.object(self.app.manager,'start_playing_profile') as play:
            self.app.manager._on_hotkey_play_profile(self.profile)
            play.assert_not_called()
            self.app._process_ui_events()
            self.assertEqual(self.root.state(),'withdrawn')
            self.assertIsNotNone(self.app._pending_play)
            play.assert_not_called()
            self.app._cmd_emergency_stop()

    def test_real_panel_bounds_are_protected_from_macro_click(self):
        self.app._hide_to_tray()
        self.root.update()
        win=self.app.record_notice.window
        x,y=win.winfo_rootx()+40,win.winfo_rooty()+40
        with patch.object(self.app.manager.player,'mouse_controller') as mouse:
            with self.assertRaises(RuntimeError):
                self.app.manager.player._execute_action(MacroAction('mouse_click',0,x=x,y=y,pressed=True))
            mouse.press.assert_not_called()

    def test_play_hides_main_before_start_and_stop_cancels_pending_play(self):
        self.app.manager.script_activation = 'mouse'
        with patch.object(self.app.manager, 'start_playing_profile') as play, patch.object(self.app.overlay_input,'activate'):
            self.app._cmd_start_playing()
            self.assertEqual(self.root.state(), 'withdrawn')
            self.assertTrue(self.app.record_notice.pinned)
            play.assert_not_called()
            self.app._cmd_start_playing()
            self.app._cmd_emergency_stop()
            until = time.monotonic()+.25
            while time.monotonic()<until: self.root.update(); time.sleep(.01)
            play.assert_not_called()
            self.assertIsNone(self.app._pending_play)
            self.app._cmd_start_playing()
            until = time.monotonic()+.25
            while time.monotonic()<until: self.root.update(); time.sleep(.01)
            play.assert_called_once_with(self.profile)
            self.assertEqual(self.root.state(), 'withdrawn')

    def test_settings_activation_saves_and_rebuilds_listeners(self):
        from tkinter import ttk
        self.app._cmd_open_settings()
        self.app.activation_var.set('mouse')
        save = next(w for w in self.app.settings_tab.footer.winfo_children()
                    if isinstance(w,ttk.Button) and w.cget('text')=='Lưu cài đặt')
        save.invoke()
        self.assertEqual(self.app.manager.script_activation, 'mouse')
        self.assertEqual(MacroManager(self.app.manager.library_path).script_activation, 'mouse')

    def test_script_selector_is_readable_and_shows_explicit_hotkey(self):
        second = ScriptProfile(name='Web auto', hotkey='0', actions=[])
        self.app.manager.profiles.append(second)
        self.app._refresh_profile_deck()
        self.assertIn('Web auto   |   Phím: 0', self.app.profile_choice.cget('values'))
        self.app._style_profile_dropdown()
        popup = self.root.tk.call('ttk::combobox::PopdownWindow', self.app.profile_choice)
        font = self.root.tk.call(f'{popup}.f.l', 'cget', '-font')
        self.assertEqual(self.root.tk.splitlist(font), ('Segoe UI', '11'))
        self.app.profile_choice.current(1)
        self.app._choose_profile()
        self.assertEqual(self.app.manager.get_active_profile(), second)
        self.assertIn('0 bước thao tác', self.app.profile_summary.cget('text'))
        self.assertIn('Phím chạy: 0', self.app.profile_summary.cget('text'))
        second.actions.append(MacroAction('key_press', 0, key='a'))
        self.app._refresh_action_tree()
        self.assertIn('1 bước thao tác', self.app.profile_summary.cget('text'))

    def test_visible_delete_button_cancels_then_deletes_selected_script_and_persists(self):
        second = ScriptProfile(name='Web auto', hotkey='0')
        self.app.manager.profiles.append(second)
        self.app.manager.set_active_profile(second.id)
        self.app._refresh_profile_deck()
        self.app.manager.save_library()
        with patch.object(self.ui.messagebox, 'askyesno', return_value=False):
            self.app.btn_delete_profile.invoke()
        self.assertEqual(self.app.manager.get_active_profile(), second)
        with patch.object(self.ui.messagebox, 'askyesno', return_value=True) as confirm, \
                patch.object(self.app, 'notify_app'):
            self.app.btn_delete_profile.invoke()
        self.assertIn('Web auto', confirm.call_args.args[1])
        self.assertEqual(self.app.manager.get_active_profile(), self.profile)
        self.assertEqual(self.app.profile_choice.current(), 0)
        saved = MacroStorage.load_library(self.app.manager.library_path)[0]
        self.assertEqual([p.id for p in saved], [self.profile.id])

    def test_delete_failure_keeps_script_and_busy_delete_is_blocked(self):
        second = ScriptProfile(name='Giữ lại khi lỗi')
        self.app.manager.profiles.append(second)
        with patch.object(self.ui.messagebox, 'askyesno', return_value=True), \
                patch.object(self.app.manager, 'save_library', side_effect=OSError('Disk full')), \
                patch.object(self.ui.messagebox, 'showerror') as error:
            self.app._cmd_delete_active_profile()
        error.assert_called_once()
        self.assertEqual(self.app.manager.profiles, [self.profile, second])
        self.assertEqual(self.app.manager.get_active_profile(), self.profile)
        self.app.manager.external_busy = True
        with patch.object(self.ui.messagebox, 'askyesno') as confirm, patch.object(self.app, 'notify_app'):
            self.app._cmd_delete_active_profile()
        confirm.assert_not_called()
        self.assertEqual(len(self.app.manager.profiles), 2)

    def test_tabs_speed_and_app_only_progress_notification(self):
        from tkinter import ttk
        self.assertEqual(len(self.app.tabs.tabs()), 6)
        self.app._cmd_open_settings()
        self.assertEqual(self.app.tabs.select(), str(self.app.settings_tab))
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        self.assertFalse(any(isinstance(w, ttk.Scrollbar) for w in descendants(self.app.tabs)))
        self.app._set_speed('10x')
        self.assertEqual(self.app._parse_speed(), 10)
        with patch.object(self.app.record_notice, 'show') as notice:
            self.app.notify_app('Tiến độ', '4/10', progress=40)
        notice.assert_called_once_with('Tiến độ', '4/10', duration=None, progress=40)

    def test_workspace_import_keeps_desktop_macro_separate(self):
        panel = self.app.workspace
        with self.assertRaises(ValueError):
            panel._accept({'actions': [a.to_dict() for a in self.profile.actions]})
        panel._accept({'workspace_script': True, 'version': 1, 'mode': 'web', 'size': [1280,720],
            'name': 'Mẫu riêng', 'url': 'about:blank', 'actions': [{'kind':'text','text':'Khám sức khoẻ'}]})
        self.assertTrue(panel._needs_open)
        self.assertEqual(len(self.profile.actions), 1)
        panel.save()
        self.assertTrue(panel.library_path.exists())
        self.assertEqual(panel._data()['actions'][0]['text'], 'Khám sức khoẻ')

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
        self.addCleanup(self._destroy_ui)
        self.hotkeys = patch.object(MacroManager, 'start_global_hotkeys')
        self.hotkeys.start()
        self.addCleanup(self.hotkeys.stop)
        with patch.object(MacroStorage, 'default_library_path', return_value=str(Path(self.temporary.name) / 'library.json')), \
                patch.object(ui.HocVetApp, '_setup_system_tray'):
            self.app = ui.HocVetApp(self.root)
        self.app.manager.script_activation = 'hotkey'
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
        dialog = self.app.settings_tab
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
        self.app._show_settings_page(list(SHORTCUT_ACTIONS).index('wait_window')//6)
        self.root.update()
        capture = next(w for w in rows.grid_slaves(row=entry.grid_info()['row']) if isinstance(w, ttk.Button))
        capture.invoke()
        entry.focus_force()
        self.root.update()
        entry.event_generate('<KeyPress>', keysym='j', state=4)
        self.root.update()
        self.assertEqual(entry.get(), 'Ctrl+J')
        entries['help'].delete(0, 'end')
        entries['help'].insert(0, 'F6')
        entries['stop_record'].delete(0, 'end')
        entries['stop_record'].insert(0, '2')
        button(dialog, 'Lưu cài đặt').invoke()
        self.root.update()
        self.assertFalse(self.app.manager.shortcuts_suspended)
        restored = MacroManager(self.app.manager.library_path)
        self.assertEqual(restored.button_hotkeys['help'], 'F6')
        self.assertEqual(restored.button_hotkeys['stop_record'], '2')
        self.assertEqual(restored.button_hotkey_scopes['stop_record'], 'global')
        self.assertIn('2', self.app.btn_stop.text)
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
        dialog = self.app.settings_tab
        entry = self.app.shortcut_entries['help']
        entry.delete(0, 'end')
        entry.insert(0, 'F6')
        buttons = dialog.footer
        save = next(w for w in buttons.winfo_children() if isinstance(w, ttk.Button) and w.cget('text') == 'Lưu cài đặt')
        with patch.object(self.app.manager, 'save_library', side_effect=OSError('disk unavailable')), patch('ui.messagebox.showerror'):
            save.invoke()
        self.assertEqual(self.app.manager.button_hotkeys['help'], 'F1')
        self.app.tabs.select(self.app.content)
        self.app._tab_changed()

    def test_background_f8_countdown_digit_stop_and_saved_notice(self):
        from pynput import keyboard
        app = self.app
        app.manager.button_hotkeys['stop_record'] = '2'
        original = list(self.profile.actions)
        with patch.object(app.record_notice, 'show') as notice, patch.object(app, 'notify_app'), \
                patch('core.keyboard.Listener'), patch('core.mouse.Listener'), patch('core.play_sound'):
            self.root.withdraw()
            app.manager._on_hotkey_toggle_record()
            app._process_ui_events()
            self.assertEqual(app.manager.state, MacroManager.STATE_COUNTDOWN)
            self.assertFalse(app.manager.recorder.is_recording)
            self.assertEqual(self.profile.actions, original)
            self.assertEqual(notice.call_args.kwargs['number'], 3)
            for second in (2, 1, 0):
                self.root.after_cancel(app.countdown_timer)
                app._start_countdown(second)
            self.assertTrue(app.manager.recorder.is_recording)
            recorder = app.manager.recorder
            recorder._on_key_press(keyboard.KeyCode.from_vk(65, char='a'))
            recorder._on_key_release(keyboard.KeyCode.from_vk(65, char='a'))
            # Phím 2 thật được pynput canonical hóa, không chỉ gọi thẳng callback giả.
            stop_key = keyboard.KeyCode.from_vk(50, char='2')
            recorder._on_key_press(stop_key)
            recorder._on_key_release(stop_key)
            listener = keyboard.GlobalHotKeys({'2': lambda: app.manager._on_command_hotkey('stop_record')})
            listener._on_press(stop_key, False)
            listener._on_release(stop_key, False)
            app._process_ui_events()
            self.assertEqual(app.manager.state, MacroManager.STATE_IDLE)
            self.assertEqual([a.key for a in self.profile.actions], ['vk_65', 'vk_65'])
            self.assertIn('LƯU THÀNH CÔNG', notice.call_args.args[0])
            saved = MacroStorage.load_library(app.manager.library_path)[0][0]
            self.assertEqual([a.key for a in saved.actions], ['vk_65', 'vk_65'])

    def test_cancel_countdown_by_f8_and_panic_preserves_script(self):
        app = self.app
        original = list(self.profile.actions)
        with patch.object(app.record_notice, 'show'), patch.object(app.manager.recorder, 'start') as start:
            app.manager._on_hotkey_toggle_record()
            app._process_ui_events()
            app.manager._on_hotkey_toggle_record()
            app._process_ui_events()
            self.assertEqual(app.manager.state, MacroManager.STATE_IDLE)
            self.assertIsNone(app.countdown_timer)
            app.manager._on_hotkey_toggle_record()
            app._process_ui_events()
            app.manager._on_hotkey_panic()
            app._process_ui_events()
            self.assertEqual(app.manager.state, MacroManager.STATE_IDLE)
            self.assertEqual(self.profile.actions, original)
            start.assert_not_called()

    def test_numpad_stop_not_stored(self):
        from pynput import keyboard
        recorder = self.app.manager.recorder
        recorder.control_hotkeys = ['2']
        with patch('core.keyboard.Listener'), patch('core.mouse.Listener'), patch('core.play_sound'):
            recorder.start()
            recorder._on_key_press(keyboard.KeyCode.from_vk(98, char='2'))
            recorder._on_key_release(keyboard.KeyCode.from_vk(98, char='2'))
            self.assertEqual(recorder.stop(), [])

    def test_ui_stop_click_is_not_recorded(self):
        from pynput import mouse
        app = self.app
        app.manager.script_activation = 'mouse'
        self.root.deiconify()
        self.root.lift()
        self.root.update()
        with patch('core.keyboard.Listener'), patch('core.mouse.Listener'), patch('core.play_sound'), \
                patch.object(app.record_notice, 'show'), patch.object(app, 'notify_app'):
            app.manager.start_recording()
            app._process_ui_events()
            self.root.focus_force()
            self.root.update()
            x = app.btn_stop.winfo_rootx() + 12
            y = app.btn_stop.winfo_rooty() + 12
            # Không phụ thuộc cửa sổ khác đang che desktop của máy chạy kiểm thử.
            app.manager.recorder.ignore_mouse = Mock(return_value=True)
            app.manager.recorder.ignore_keyboard = Mock(return_value=True)
            app.manager.recorder._on_mouse_click(x, y, mouse.Button.left, True)
            app.manager.recorder.ignore_mouse.assert_called_once_with(x, y)
            from pynput import keyboard
            app.manager.recorder._on_key_press(keyboard.Key.space)
            app.btn_stop._activate()
            self.assertEqual(self.profile.actions, [])

    def test_recording_events_do_not_schedule_or_redraw_per_action(self):
        app = self.app
        action = MacroAction('key_press', 0, key='a')
        with patch.object(self.root, 'after') as schedule, patch.object(app.tree, 'insert') as insert:
            for count in range(10000):
                app._on_action_recorded(action, count)
                app._on_player_step(count, 10000, 1, 1)
            schedule.assert_not_called()
            insert.assert_not_called()
            self.assertEqual(app._recorded_count, 9999)
            self.assertEqual(app._pending_progress[0], 9999)

    def test_large_preview_keeps_correct_original_action_index(self):
        self.profile.actions = [MacroAction('key_press', 0, key='a') for _ in range(2000)]
        self.app._refresh_action_tree()
        self.assertEqual(len(self.app.tree.get_children()), 12)
        self.assertEqual(self.app.tree.get_children()[0], '0')
        self.app._preview_start=1500
        self.app._refresh_action_tree()
        self.assertEqual(self.app.tree.get_children()[0], '1500')
        self.app.tree.selection_set('1500')
        with patch('ui.simpledialog.askfloat', return_value=1.25):
            self.app._cmd_edit_delay()
        self.assertEqual(self.profile.actions[1500].delay, 1.25)
        self.assertEqual(self.profile.actions[500].delay, 0)

    def test_save_failure_does_not_report_success_or_discard_recording(self):
        from pynput import keyboard
        app = self.app
        app.manager.script_activation = 'mouse'
        with patch('core.keyboard.Listener'), patch('core.mouse.Listener'), patch('core.play_sound'), \
                patch.object(app.record_notice, 'show') as notice, patch.object(app, 'notify_app'), \
                patch.object(app.manager, 'save_library', side_effect=OSError('disk unavailable')):
            app.manager.start_recording()
            app.manager.recorder._on_key_press(keyboard.KeyCode.from_vk(65, char='a'))
            app._post(app._cmd_stop_recording)
            app._process_ui_events()
            self.assertEqual(app.manager.state, MacroManager.STATE_IDLE)
            self.assertFalse(app.manager.recorder.is_recording)
            self.assertEqual(self.profile.actions[0].key, 'vk_65')
            self.assertFalse(any('THÀNH CÔNG' in call.args[0] for call in notice.call_args_list))


if __name__ == '__main__':
    unittest.main()
