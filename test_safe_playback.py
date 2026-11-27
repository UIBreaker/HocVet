"""Kiểm thử phát lại với hai cửa sổ giả và dữ liệu mẫu."""
import json
from pathlib import Path
from queue import Queue
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from PIL import Image
from core import MacroAction, MacroManager, ScriptProfile, _check_send_result
from test_features import reference_png


class FakeMouse:
    def __init__(self, app):
        self._position = (40, 60)
        self.after_move = None
        self.press = Mock(side_effect=lambda _: app.input.append(('press', app.foreground)))
        self.release = Mock(side_effect=lambda _: app.input.append(('release', app.foreground)))
        self.scroll = Mock(side_effect=lambda *_: app.input.append(('scroll', app.foreground)))

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, point):
        self._position = point
        if self.after_move:
            self.after_move()


class SafePlaybackTests(unittest.TestCase):
    def setUp(self):
        folder = Path(__file__).parent / 'build'
        folder.mkdir(exist_ok=True)
        temporary = self.enterContext(TemporaryDirectory(dir=folder))
        self.manager = MacroManager(str(Path(temporary) / 'library.json'))
        self.player = self.manager.player
        self.input = []
        self.foreground = 101
        self.pointer_window = 101
        self.titles = {101: 'Cửa sổ thử A', 202: 'Cửa sổ thử B — chuỗi giả nhạy cảm'}
        self.player.mouse_controller = FakeMouse(self)
        self.player.keyboard_controller = Mock()
        self.player.keyboard_controller.press.side_effect = lambda _: self.input.append(('key down', self.foreground))
        self.player.keyboard_controller.release.side_effect = lambda _: self.input.append(('key up', self.foreground))
        self.enterContext(patch('core.play_sound'))
        self.enterContext(patch('core.foreground_window', side_effect=lambda: self.foreground))
        self.enterContext(patch('core.window_title', side_effect=self.titles.__getitem__))
        self.enterContext(patch('conditions.window_title', side_effect=self.titles.__getitem__))
        self.enterContext(patch('core.window_at', side_effect=lambda x, y: self.pointer_window))
        self.pauses = Queue()
        self.manager.on_play_paused = lambda *args: self.pauses.put(args)
        self.player.on_wait = Mock()
        self.addCleanup(self.stop_worker)

    def stop_worker(self):
        self.manager.stop_playing()
        if self.player._play_thread:
            self.join_worker()

    def join_worker(self):
        self.player._play_thread.join(3)
        self.assertFalse(self.player._play_thread.is_alive())
        self.assertEqual(self.manager.state, self.manager.STATE_IDLE)

    def pause(self, step, total):
        name, current, count, reason = self.pauses.get(timeout=3)
        self.assertEqual((name, current, count), ('Kịch bản mẫu', step, total))
        self.assertEqual(self.manager.state, self.manager.STATE_PAUSED)
        return reason

    def start(self, *actions):
        self.manager.start_playing_profile(ScriptProfile(name='Kịch bản mẫu', actions=list(actions)))

    def events(self):
        return [json.loads(line) for line in self.player.log_path.read_text(encoding='utf-8').splitlines()]

    def test_window_changes_after_cursor_moves_but_before_press(self):
        mouse = self.player.mouse_controller
        mouse.after_move = lambda: setattr(self, 'foreground', 202)
        self.start(MacroAction('mouse_click', 0, x=40, y=60, pressed=True),
                   MacroAction('mouse_click', 0, x=40, y=60, pressed=False))
        self.assertIn('mất tiêu điểm', self.pause(1, 2))
        self.assertEqual(self.input, [])
        self.manager.resume_playing()
        self.assertIn('mất tiêu điểm', self.pause(1, 2))
        self.assertEqual(self.input, [])
        self.foreground = 101
        mouse.after_move = None
        self.manager.resume_playing()
        self.join_worker()
        self.assertEqual(self.input, [('press', 101), ('release', 101)])
        events = self.events()
        self.assertEqual([entry['event'] for entry in events],
                         ['paused', 'resume_requested', 'paused', 'resume_requested', 'resumed'])
        self.assertTrue(all(entry['step'] == 1 and entry['time'] and entry['script'] == 'Kịch bản mẫu' for entry in events))

    def test_title_and_hit_test_prevent_send_to_wrong_window(self):
        self.start(MacroAction('key_press', 0, key='vk_65', window_title='thử B'))
        self.assertIn('không khớp', self.pause(1, 1))
        self.assertEqual(self.input, [])
        self.manager.stop_playing()
        self.join_worker()
        self.pointer_window = 202
        self.start(MacroAction('mouse_scroll', 0, x=40, y=60, dy=-1))
        self.assertIn('tọa độ', self.pause(1, 1).lower())
        self.assertEqual(self.input, [])
        self.manager.stop_playing()
        self.join_worker()
        self.assertEqual(self.input, [])

    def test_image_timeout_rechecks_same_step_on_each_resume(self):
        screenshot = Image.new('RGB', (12, 10), 'blue')
        with patch('conditions.ImageGrab.grab', side_effect=lambda **_: screenshot):
            self.start(MacroAction('wait_image', 0, x=40, y=60, image=reference_png(), timeout=.02),
                       MacroAction('mouse_scroll', 0, x=40, y=60, dy=-1))
            self.assertIn('0.02 giây', self.pause(1, 2))
            self.manager.resume_playing()
            self.assertIn('Vẫn chưa tìm thấy ảnh / nút', self.pause(1, 2))
            self.assertEqual(self.input, [])
            screenshot = Image.new('RGB', (12, 10), 'red')
            self.manager.resume_playing()
            self.join_worker()
        self.assertEqual(self.input, [('scroll', 101)])
        self.assertEqual(self.events()[0]['reason'], 'wait_image_timeout')

    def test_stop_interrupts_wait_before_deadline(self):
        checking = Queue()
        self.player.on_wait.side_effect = checking.put
        self.start(MacroAction('wait_window', 0, window_title='Không tồn tại', timeout=30),
                   MacroAction('key_press', 0, key='vk_65'))
        checking.get(timeout=3)
        self.manager.stop_playing()
        self.join_worker()
        self.assertTrue(self.pauses.empty())
        self.assertEqual(self.input, [])
        self.assertEqual(self.events()[-1]['reason'], 'user_stop_during_wait_window')

    def test_legacy_json_wait_allows_window_handoff(self):
        profile = ScriptProfile.from_dict({'name': 'Kịch bản mẫu', 'actions': [
            {'action_type': 'mouse_click', 'pressed': True, 'x': 40, 'y': 60},
            {'action_type': 'mouse_click', 'pressed': False, 'x': 40, 'y': 60},
            {'action_type': 'wait_window', 'window_title': 'thử b', 'timeout': .5},
            {'action_type': 'key_press', 'key': 'vk_65'},
            {'action_type': 'key_release', 'key': 'vk_65'},
        ]})
        def handoff(_):
            self.input.append(('release', self.foreground))
            self.foreground = 202
        self.player.mouse_controller.release.side_effect = handoff
        self.manager.start_playing_profile(profile)
        self.join_worker()
        self.assertTrue(self.pauses.empty())
        self.assertEqual(self.input, [('press', 101), ('release', 101), ('key down', 202), ('key up', 202)])

    def test_uncertain_input_is_never_replayed_and_log_omits_payload(self):
        def focus_changes_during_scroll(*_):
            self.input.append(('scroll', self.foreground))
            self.foreground = 202
        self.player.mouse_controller.scroll.side_effect = focus_changes_during_scroll
        self.start(MacroAction('mouse_scroll', 0, x=40, y=60, dy=-1),
                   MacroAction('key_press', 0, key='vk_65'))
        self.assertIn('Tiếp tục sẽ kết thúc', self.pause(1, 2))
        self.foreground = 101
        self.manager.resume_playing()
        self.join_worker()
        self.assertEqual(self.input, [('scroll', 101)])
        self.assertEqual(self.events()[-1]['reason'], 'uncertain_input')
        for entry in self.events():
            self.assertEqual(set(entry), {'time', 'script', 'step', 'event', 'reason'})
        self.assertNotIn('chuỗi giả nhạy cảm', self.player.log_path.read_text(encoding='utf-8'))

    def test_windows_partial_send_requires_verification_then_stops(self):
        mouse = self.player.mouse_controller
        mouse.scroll.side_effect = lambda *_: _check_send_result(1, None, (2,))
        self.start(MacroAction('mouse_scroll', 0, x=40, y=60, dx=1, dy=1),
                   MacroAction('key_press', 0, key='vk_65'))
        self.assertIn('Chưa xác nhận được', self.pause(1, 2))
        self.manager.resume_playing()
        self.join_worker()
        mouse.scroll.assert_called_once()
        self.assertEqual(self.input, [])
        self.assertEqual(self.events()[0]['reason'], 'send_uncertain')
