import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

from core import MacroAction,MacroPlayer,MacroRecorder,MacroStorage,ScriptProfile
from date_paste import DatePaste,date_parts,paste_date
from his_environment import HisEnvironment
from pynput import keyboard


class DateTests(unittest.TestCase):
    def test_valid_dates_and_invalid_calendar_dates(self):
        self.assertEqual(date_parts('19/08/1987'),('19','08','1987'))
        self.assertEqual(date_parts(' 1/2/2000 '),('01','02','2000'))
        self.assertEqual(date_parts('29/02/2000'),('29','02','2000'))
        for value in ('29/02/1900','31/04/2000','00/01/2000','1/13/2000','19/08/87','19/08/1987 extra'):
            with self.subTest(value=value),self.assertRaises(ValueError):date_parts(value)

    def test_paste_replaces_three_fields_and_leaves_fourth_untouched(self):
        ctrl=Mock();cancel=Mock();cancel.is_set.return_value=False;cancel.wait.return_value=False
        with patch('date_paste.ctypes.windll.user32.GetForegroundWindow',return_value=123),patch('date_paste.set_clipboard_text') as clipboard,patch('date_paste.FocusedInput'):
            paste_date('19/08/1987',ctrl,cancel)
        self.assertEqual([call.args[0] for call in clipboard.call_args_list],['19','08','1987','19/08/1987'])
        self.assertEqual(sum(call.args==(keyboard.Key.tab,) for call in ctrl.press.call_args_list),2)
        self.assertEqual([getattr(call.args[0],'vk',None) for call in ctrl.press.call_args_list if call.args[0] not in (keyboard.Key.ctrl_l,keyboard.Key.tab)],[65,86]*3)

    def test_default_mode_detects_his_auto_advance_without_extra_tabs(self):
        controller=Mock();cancel=Mock();cancel.is_set.return_value=False;cancel.wait.return_value=False
        tracker=Mock();tracker.same.side_effect=[True,False,False]
        with patch('date_paste.ctypes.windll.user32.GetForegroundWindow',return_value=123),patch('date_paste.set_clipboard_text'),patch('date_paste.FocusedInput',return_value=tracker):
            paste_date('19/08/1989',controller,cancel)
        self.assertNotIn(unittest.mock.call(keyboard.Key.tab),controller.press.call_args_list)
        tracker.close.assert_called_once()

    def test_default_mode_detects_each_field_independently(self):
        controller=Mock();cancel=Mock();cancel.is_set.return_value=False;cancel.wait.return_value=False
        tracker=Mock();tracker.same.side_effect=[True,False,True,True,True,True,True]
        with patch('date_paste.ctypes.windll.user32.GetForegroundWindow',return_value=123),patch('date_paste.set_clipboard_text'),patch('date_paste.FocusedInput',return_value=tracker):
            paste_date('19/08/1989',controller,cancel)
        self.assertEqual(controller.press.call_args_list.count(unittest.mock.call(keyboard.Key.tab)),1)

    def test_focus_detection_failure_stops_before_pasting_parts(self):
        controller=Mock();cancel=Mock();cancel.is_set.return_value=False;cancel.wait.return_value=False
        with patch('date_paste.ctypes.windll.user32.GetForegroundWindow',return_value=123),patch('date_paste.set_clipboard_text') as clipboard,patch('date_paste.FocusedInput',side_effect=RuntimeError('no focus')),self.assertRaisesRegex(RuntimeError,'no focus'):
            paste_date('19/08/1989',controller,cancel)
        controller.press.assert_not_called();clipboard.assert_called_once_with('19/08/1989')

    def test_cancel_or_focus_change_blocks_input(self):
        ctrl=Mock();cancel=threading.Event();cancel.set()
        with patch('date_paste.set_clipboard_text'),self.assertRaises(InterruptedError):paste_date('19/08/1987',ctrl,cancel)
        ctrl.press.assert_not_called();cancel.clear()
        with patch('date_paste.ctypes.windll.user32.GetForegroundWindow',return_value=124),patch('date_paste.set_clipboard_text'),self.assertRaises(RuntimeError):
            paste_date('19/08/1987',ctrl,cancel,target=123)
        ctrl.press.assert_not_called()

    def test_auto_advance_does_not_send_extra_tabs(self):
        controller=Mock();cancel=Mock();cancel.is_set.return_value=False;cancel.wait.return_value=False
        with patch('date_paste.ctypes.windll.user32.GetForegroundWindow',return_value=123),patch('date_paste.set_clipboard_text') as clipboard:
            paste_date('19/08/1989',controller,cancel,navigation='auto')
        self.assertEqual([call.args[0] for call in clipboard.call_args_list],['19','08','1989','19/08/1989'])
        self.assertNotIn(unittest.mock.call(keyboard.Key.tab),controller.press.call_args_list)

    def test_hook_one_shot_and_recorder_skips_original_v(self):
        helper=DatePaste(lambda:False,Mock());helper.listener=Mock()
        recorder=MacroRecorder();recorder.is_recording=True
        helper.arm('19/08/1987',lambda:recorder.record_date_field('birth','Ngày sinh',1))
        data=SimpleNamespace(vkCode=86,flags=0)
        with patch.object(helper,'_ctrl',return_value=True),patch('date_paste.threading.Thread') as worker:
            self.assertTrue(helper.ignore_recording(0x100,data))
            helper._filter(0x100,data)
            self.assertEqual(recorder.actions[0].action_type,'paste_date')
            self.assertIsNone(helper.pending);worker.return_value.start.assert_called_once()
            helper._filter(0x101,data)
            self.assertTrue(helper.ignore_recording(0x101,data))
            self.assertFalse(helper.ignore_recording(0x100,data))
            self.assertFalse(helper.ignore_recording(0x101,data))

    def test_focus_change_while_click_settles_does_not_paste_parts(self):
        ctrl=Mock();cancel=threading.Event()
        with patch('date_paste.ctypes.windll.user32.GetForegroundWindow',side_effect=[123,124]), \
                patch('date_paste.set_clipboard_text') as clipboard, \
                self.assertRaises(RuntimeError):
            paste_date('19/08/1987',ctrl,cancel,target=123)
        ctrl.press.assert_not_called()
        self.assertEqual(clipboard.call_args_list, [unittest.mock.call('19/08/1987')])

    def test_expired_or_own_window_does_not_intercept(self):
        helper=DatePaste(lambda:True,Mock());helper.listener=Mock();callback=Mock()
        helper.arm('19/08/1987',callback)
        with patch.object(helper,'_ctrl',return_value=True):
            helper._filter(0x100,SimpleNamespace(vkCode=86,flags=0))
            self.assertFalse(helper.ignore_recording(0x100,SimpleNamespace(vkCode=86)))
        callback.assert_not_called()
        helper.pending=('19/08/1987',callback,time.monotonic()-1)
        helper._filter(0x100,SimpleNamespace(vkCode=86,flags=0));self.assertIsNone(helper.pending)
        helper.arm('19/08/1987',callback)
        with patch('date_paste.ctypes.windll.user32.GetClipboardSequenceNumber',return_value=helper.clipboard_sequence+1),patch('date_paste.get_clipboard_text',return_value='other text'):
            helper._filter(0x100,SimpleNamespace(vkCode=86,flags=0));self.assertIsNone(helper.pending)

    def test_same_clipboard_republished_and_injected_ctrl_v_still_trigger(self):
        helper=DatePaste(lambda:False,Mock());helper.listener=Mock();callback=Mock()
        helper.arm('19/08/1987',callback)
        with patch('date_paste.ctypes.windll.user32.GetClipboardSequenceNumber',return_value=helper.clipboard_sequence+1),patch('date_paste.get_clipboard_text',return_value='19/08/1987'),patch.object(helper,'_ctrl',return_value=True),patch('date_paste.threading.Thread'):
            helper._filter(0x100,SimpleNamespace(vkCode=86,flags=0x10))
        callback.assert_called_once();self.assertIsNone(helper.pending)
        helper._filter(0x100,SimpleNamespace(vkCode=86,flags=0x10))
        callback.assert_called_once()

    def test_worker_clears_trigger_key_before_sending_and_after_error(self):
        helper=DatePaste(lambda:False,Mock());helper.busy=True;helper.swallow_v=True
        def send(*args):
            self.assertFalse(helper.swallow_v)
            raise RuntimeError('test failure')
        with patch.object(helper,'_ctrl',return_value=False),patch('date_paste.keyboard.Controller'),patch('date_paste.paste_date',side_effect=send):
            helper._paste('19/08/1987',123)
        self.assertFalse(helper.busy);self.assertFalse(helper.swallow_v)
        helper.on_error.assert_called_once_with('test failure')


class DataTests(unittest.TestCase):
    def setUp(self):
        folder=Path('build/test-dates');folder.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=folder);self.addCleanup(self.temp.cleanup)
        self.model=HisEnvironment(Path(self.temp.name)/'his.json');self.model.update(installed=True)

    def test_date_action_roundtrip_preflight_and_multiple_rows(self):
        field=self.model.add_field('Ngày sinh');self.model.set_paste_mode(field,'date_dmy')
        self.model.paste(0,0,[['19/08/1987'],['29/02/2000']])
        action=MacroAction('paste_date',0,data_field=field,data_label='Ngày sinh',data_row=1)
        profile=ScriptProfile(actions=[action]);MacroStorage.validate_profile(profile)
        self.assertEqual(MacroAction.from_dict(action.to_dict()),action)
        loops,reader=self.model.prepare([action],0);self.assertEqual(loops,2)
        with patch('core.mouse.Controller'),patch('core.keyboard.Controller'):
            player=MacroPlayer()
        player.field_reader=reader
        with patch('core.play_sound'),patch('date_paste.paste_date') as paste:
            player._run_playback([action],10,loops,0)
        self.assertEqual([call.args[0] for call in paste.call_args_list],['19/08/1987','29/02/2000'])
        self.model.set_cell(1,field,'31/02/2000')
        with self.assertRaisesRegex(ValueError,'STT 2'):self.model.prepare([action],0)
        self.assertEqual(HisEnvironment(self.model.path).fields[0]['paste_mode'],'date_dmy')

    def test_delete_board_preserves_other_board_and_blocks_old_scripts_after_reload(self):
        first=self.model.active_id;field=self.model.add_field('Ngày sinh')
        self.model.set_cell(0,field,'19/08/1987')
        action=MacroAction('paste_date',0,data_field=field,data_label='Ngày sinh',data_row=1)
        self.model.create_environment('Giữ lại');keep=self.model.add_field('Ngày sinh');self.model.set_cell(0,keep,'01/01/2000')
        self.model.select_environment(first);self.model.delete_environment()
        loaded=HisEnvironment(self.model.path)
        self.assertEqual(loaded.rows,[{keep:'01/01/2000'}])
        with self.assertRaisesRegex(ValueError,'đã bị xóa'):loaded.prepare([action],1)
        loaded.delete_environment();self.assertEqual(len(loaded.environments),1);self.assertEqual(loaded.fields,[])

    def test_delete_save_failure_keeps_in_memory_and_disk(self):
        field=self.model.add_field('Tên');before=self.model.path.read_bytes()
        with patch.object(MacroStorage,'_atomic_json',side_effect=OSError('disk full')),self.assertRaises(OSError):self.model.delete_environment()
        self.assertEqual(self.model.path.read_bytes(),before);self.assertEqual(self.model.fields[0]['id'],field)

    def test_old_single_cell_script_is_blocked_after_column_changes_to_split_date(self):
        field=self.model.add_field('Ngày sinh');self.model.set_cell(0,field,'19/08/1987')
        old=MacroAction('copy_field',0,data_field=field,data_label='Ngày sinh',data_row=1)
        self.model.prepare([old],1)
        self.model.set_paste_mode(field,'date_dmy')
        with self.assertRaisesRegex(ValueError,'kịch bản cũ'):self.model.prepare([old],1)

    def test_navigation_uses_saved_column_mode_when_replaying_existing_date_script(self):
        field=self.model.add_field('Ngày sinh');self.model.set_cell(0,field,'19/08/1989')
        action=MacroAction('paste_date',0,data_field=field,data_row=1)
        self.model.set_paste_mode(field,'date_dmy_auto')
        loaded=HisEnvironment(self.model.path)
        _,reader=loaded.prepare([action],1)
        with patch('core.mouse.Controller'),patch('core.keyboard.Controller'):player=MacroPlayer()
        player.field_reader=reader
        with patch('date_paste.paste_date') as paste:player._execute_action(action)
        self.assertEqual(paste.call_args.kwargs['navigation'],'auto')


if __name__=='__main__':unittest.main()
