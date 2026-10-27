import ctypes
import gc
import tempfile
import threading
import tkinter as tk
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock,patch

from core import MacroAction,MacroManager,MacroPlayer,MacroRecorder,MacroStorage,ScriptProfile,key_identity,str_to_key
from his_environment import HisEnvironment


class HisDataTests(unittest.TestCase):
    def setUp(self):
        folder=Path('build/test-his');folder.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=folder);self.addCleanup(self.temp.cleanup)
        self.model=HisEnvironment(Path(self.temp.name)/'his.json');self.model.update(installed=True)
        self.name=self.model.add_field('Họ và tên');self.code=self.model.add_field('CCCD')
        self.model.paste(0,0,[['Mẫu A','00123'],['Mẫu B','00456'],['Mẫu C','00789']])

    def copies(self):
        return [MacroAction('copy_field',0,data_field=self.name,data_label='Họ và tên',data_row=1),
                MacroAction('copy_field',0,data_field=self.code,data_label='CCCD',data_row=1)]

    def test_rows_advance_each_loop_and_snapshot_keeps_original_text(self):
        loops,reader=self.model.prepare(self.copies(),0)
        self.assertEqual(loops,3)
        self.model.set_cell(1,self.name,'Đã đổi sau khi chụp')
        with patch('core.mouse.Controller'),patch('core.keyboard.Controller'):
            player=MacroPlayer()
        player.field_reader=reader;copied=[]
        with patch('core.play_sound'),patch('core.set_clipboard_text',side_effect=lambda value,event:copied.append(value)):
            player._run_playback(self.copies(),10,loops,0)
        self.assertEqual(copied,['Mẫu A','00123','Mẫu B','00456','Mẫu C','00789'])
        self.assertIsNone(player.field_reader)
        self.assertEqual(player.last_error,'')

    def test_preflight_rejects_missing_cells_rows_and_uninstalled_extension(self):
        with self.assertRaises(ValueError):self.model.prepare(self.copies(),4)
        mixed=self.copies();mixed[1].data_row=2
        with self.assertRaisesRegex(ValueError,'cùng một STT'):self.model.prepare(mixed,1)
        self.model.set_cell(1,self.code,'')
        with self.assertRaisesRegex(ValueError,'STT 2'):self.model.prepare(self.copies(),3)
        self.model.update(installed=False)
        with self.assertRaises(ValueError):self.model.prepare(self.copies(),1)
        self.model.update(installed=True)
        self.assertEqual(self.model.rows[0][self.code],'00123')

    def test_template_export_import_matches_field_name_on_another_machine(self):
        profile=ScriptProfile(name='Mẫu',actions=self.copies())
        file=Path(self.temp.name)/'template.hocvet';MacroStorage.export_profile(profile,file)
        imported=MacroStorage.import_profile(file)
        other=HisEnvironment(Path(self.temp.name)/'other.json');other.update(installed=True)
        other.add_field('Họ và tên');other.add_field('CCCD');other.paste(0,0,[['Máy khác','00001']])
        loops,reader=other.prepare(imported.actions,1)
        self.assertEqual(reader(imported.actions[1].data_field,1),'00001')
        with zipfile.ZipFile(file) as package:
            exported=package.read('script.json').decode('utf-8')
        self.assertNotIn('Mẫu A',exported)
        self.assertNotIn('00123',exported)

    def test_manager_caps_continuous_data_run_without_changing_saved_repeat(self):
        manager=MacroManager(str(Path(self.temp.name)/'library.json'))
        manager.prepare_field_data=self.model.prepare
        profile=ScriptProfile(actions=self.copies(),loop_count=0)
        with patch.object(manager.player,'play_async') as play:
            manager.start_playing_profile(profile)
        self.assertEqual(play.call_args.kwargs['loop_count'],3)
        self.assertEqual(profile.loop_count,0)

    def test_atomic_update_invalid_input_and_corrupt_file_preserve_data(self):
        previous=self.model.rows
        with patch.object(MacroStorage,'_atomic_json',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.model.set_cell(0,self.code,'x')
        self.assertIs(self.model.rows,previous)
        for name in ('STT','Họ và tên',''):
            with self.assertRaises(ValueError):self.model.add_field(name)
        with self.assertRaises(ValueError):self.model.paste(0,0,[['a','b','c']])
        self.model.path.write_text('{bad',encoding='utf-8')
        broken=HisEnvironment(self.model.path)
        self.assertTrue(broken.error)
        with self.assertRaises(ValueError):broken.update(installed=True)
        self.assertEqual(self.model.path.read_text(),'{bad')

    def test_copy_action_metadata_validation_rejects_bad_rows_and_missing_field(self):
        for row,field in ((0,self.name),(-1,self.name),(True,self.name),(1,None)):
            profile=ScriptProfile(actions=[MacroAction('copy_field',0,data_field=field,data_row=row)])
            with self.assertRaises(ValueError):MacroStorage.validate_profile(profile)
        conflicting=[MacroAction('copy_field',0,data_field='foreign',data_label=label,data_row=1) for label in ('Họ và tên','CCCD')]
        with self.assertRaisesRegex(ValueError,'không nhất quán'):self.model.prepare(conflicting,1)


class RecorderFocusTests(unittest.TestCase):
    def test_ctrl_held_from_table_to_his_records_paste_with_balanced_keys(self):
        from pynput import keyboard
        recorder=MacroRecorder();recorder.is_recording=True
        own=[True];recorder.ignore_keyboard=lambda:own[0]
        ctrl=keyboard.Key.ctrl_l;c=keyboard.KeyCode.from_char('c');v=keyboard.KeyCode.from_char('v')
        recorder._on_key_press(ctrl);recorder._on_key_press(c)
        recorder.record_field('name','Họ và tên',1)
        own[0]=False
        recorder._on_key_release(c);recorder._on_key_press(v)
        recorder._on_key_release(v);recorder._on_key_release(ctrl)
        self.assertEqual([(a.action_type,key_identity(str_to_key(a.key)) if a.key else None) for a in recorder.actions],
                         [('copy_field',None),('key_press','ctrl'),('key_press',86),('key_release',86),('key_release','ctrl')])

    def test_foreign_modifier_is_released_even_over_table(self):
        from pynput import keyboard
        recorder=MacroRecorder();recorder.is_recording=True
        own=[False];recorder.ignore_keyboard=lambda:own[0]
        recorder._on_key_press(keyboard.Key.ctrl_l)
        own[0]=True;recorder._on_key_release(keyboard.Key.ctrl_l)
        self.assertEqual([a.action_type for a in recorder.actions],['key_press','key_release'])


class ClipboardTests(unittest.TestCase):
    def test_unicode_memory_is_transferred_and_owner_is_cleaned(self):
        from clipboard_text import set_clipboard_text
        user=Mock();kernel=Mock();memory=ctypes.create_string_buffer(1000)
        user.CreateWindowExW.return_value=123;user.SetClipboardData.return_value=99
        kernel.GlobalAlloc.return_value=99;kernel.GlobalLock.return_value=ctypes.addressof(memory)
        with patch('clipboard_text.ctypes.WinDLL',side_effect=[user,kernel]):set_clipboard_text('00123 · Nguyễn mẫu')
        expected=('00123 · Nguyễn mẫu\0').encode('utf-16-le')
        self.assertEqual(memory.raw[:len(expected)],expected)
        user.OpenClipboard.assert_called_with(123)
        user.SetClipboardData.assert_called_with(13,99)
        kernel.GlobalFree.assert_not_called();user.CloseClipboard.assert_called_once();user.DestroyWindow.assert_called_with(123)

    def test_cancelled_copy_does_not_empty_clipboard(self):
        from clipboard_text import set_clipboard_text
        user=Mock();kernel=Mock();user.CreateWindowExW.return_value=123
        cancel=threading.Event();cancel.set()
        with patch('clipboard_text.ctypes.WinDLL',side_effect=[user,kernel]):
            with self.assertRaises(InterruptedError):set_clipboard_text('x',cancel)
        user.EmptyClipboard.assert_not_called();user.DestroyWindow.assert_called_with(123)


class HisUITests(unittest.TestCase):
    def setUp(self):
        import ui
        self.ui=ui
        folder=Path('build/test-his');folder.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=folder);self.addCleanup(self.temp.cleanup)
        self.root=tk.Tk();self.root.withdraw();self.addCleanup(self.cleanup_ui)
        hook=patch.object(MacroManager,'start_global_hotkeys');hook.start();self.addCleanup(hook.stop)
        with patch.object(MacroStorage,'default_library_path',return_value=str(Path(self.temp.name)/'library.json')),patch.object(ui.HocVetApp,'_setup_system_tray'):
            self.app=ui.HocVetApp(self.root)
        self.profile=ScriptProfile(name='Mẫu học',actions=[])
        self.app.manager.profiles=[self.profile];self.app.manager.active_profile_id=self.profile.id
        self.app._refresh_profile_deck()

    def cleanup_ui(self):
        self.root.destroy();self.app=None;self.root=None;gc.collect()

    def install(self):
        with patch.object(self.app,'_show_his_environment'):self.app._set_his_installed(True)

    def test_install_remove_reinstall_keeps_fields_and_rows(self):
        self.assertEqual(len(self.app.tabs.tabs()),5)
        self.install();self.assertEqual(len(self.app.tabs.tabs()),6)
        field=self.app.his.add_field('Họ và tên');self.app.his.set_cell(0,field,'Dữ liệu mẫu')
        self.app._set_his_installed(False)
        self.assertIsNone(self.app.his_panel);self.assertEqual(len(self.app.tabs.tabs()),5)
        self.install()
        self.assertEqual(self.app.his.rows[0][field],'Dữ liệu mẫu')
        self.assertTrue(HisEnvironment(self.app.his.path).installed)

    def test_learning_copy_records_field_then_replay_pastes_next_rows(self):
        from pynput import keyboard
        self.install();field=self.app.his.add_field('Họ và tên')
        self.app.his.paste(0,0,[['Mẫu A'],['Mẫu B'],['Mẫu C']]);self.app.his_panel.refresh()
        with patch('core.keyboard.Listener'),patch('core.mouse.Listener'),patch('core.play_sound'),patch('extensions_ui.set_clipboard_text') as copied:
            self.app.manager.start_recording()
            self.app.his_panel.cell=(0,field);self.app.his_panel.copy_cell()
            copied.assert_called_once_with('Mẫu A')
            recorder=self.app.manager.recorder;recorder.ignore_keyboard=Mock(return_value=False)
            for key in (keyboard.Key.ctrl_l,keyboard.KeyCode.from_vk(86,char='v')):recorder._on_key_press(key)
            for key in (keyboard.KeyCode.from_vk(86,char='v'),keyboard.Key.ctrl_l):recorder._on_key_release(key)
            self.app.manager.stop_recording()
        actions=self.profile.actions
        self.assertEqual(actions[0].action_type,'copy_field')
        self.assertEqual(actions[0].data_row,1)
        self.assertEqual(sum(a.action_type=='copy_field' for a in actions),1)
        for action in actions:action.delay=0
        loops,reader=self.app.his.prepare(actions,3)
        sink=[];clipboard=['']
        with patch('core.mouse.Controller'),patch('core.keyboard.Controller'):
            player=MacroPlayer()
        player.field_reader=reader
        player.keyboard_controller.press.side_effect=lambda key:sink.append(clipboard[0]) if getattr(key,'vk',None)==86 else None
        with patch('core.play_sound'),patch('core.set_clipboard_text',side_effect=lambda value,event:clipboard.__setitem__(0,value)):
            player._run_playback(actions,10,loops,0)
        self.assertEqual(sink,['Mẫu A','Mẫu B','Mẫu C'])

    def test_missing_data_blocks_before_hiding_or_starting_and_busy_uninstall_is_blocked(self):
        self.install();field=self.app.his.add_field('Họ và tên')
        self.profile.actions=[MacroAction('copy_field',0,data_field=field,data_label='Họ và tên',data_row=1)]
        with patch.object(self.app,'_hide_to_tray') as hide,patch.object(self.app.manager,'start_playing_profile') as play,patch.object(self.app,'notify_app'):
            self.app._cmd_start_playing()
            hide.assert_not_called();play.assert_not_called()
            self.app.manager.external_busy=True
            self.app._set_his_installed(False)
        self.assertTrue(self.app.his.installed)

    def test_grid_add_select_edit_blank_cell_and_keyboard_navigation(self):
        from types import SimpleNamespace
        from extensions_ui import ThemedInputs
        self.install();panel=self.app.his_panel
        panel.table.configure(width=700,height=420);self.root.update_idletasks()
        with patch.object(ThemedInputs,'askstring',return_value='Họ và tên'):
            panel.add_field()
        field=self.app.his.fields[0]['id']
        panel.table.geometry_cells();x=(panel.table.edges[1]+panel.table.edges[2])/2
        panel.select_cell(SimpleNamespace(x=x,y=panel.table.header_height+panel.table.row_height*2+.5))
        self.assertEqual(panel.cell,(2,field))
        panel.edit_or_copy();entry=panel.editor[0];entry.insert(0,'Mẫu hàng mới');panel.commit_editor()
        self.assertEqual(self.app.his.rows[2][field],'Mẫu hàng mới')
        panel.move_cell(-1,0);self.assertEqual(panel.cell,(1,field))

    def test_learning_environment_opens_without_stopping_recording(self):
        self.install()
        with patch('core.keyboard.Listener'),patch('core.mouse.Listener'),patch('core.play_sound'):
            self.app.manager.start_recording()
            self.app._pin_controls();self.app._process_ui_events()
            self.assertTrue(self.app.record_notice.environment_enabled)
            self.app._show_his_environment()
            self.assertEqual(self.app.tabs.select(),str(self.app.his_tab))
            self.assertEqual(self.app.manager.state,MacroManager.STATE_RECORDING)
            self.app.manager.stop_recording()

    def test_full_exit_preserves_private_learning_actions(self):
        engine=Mock();engine.recording=True;engine.thread.is_alive.return_value=False
        engine.actions=[{'kind':'text','text':'Mẫu công việc'}]
        panel=self.app.workspace;panel.engine=engine;panel.job_mode='web';panel.job_size=(1280,720)
        with patch.object(self.root,'destroy'):
            self.app._exit_app();self.root.update()
        self.assertTrue(panel.library_path.exists())
        self.assertEqual(panel.actions,engine.actions)

    def test_exit_waits_for_private_worker_then_destroys_root(self):
        engine=Mock();engine.thread.is_alive.side_effect=[True,False]
        self.app.workspace.engine=engine
        with patch.object(self.root,'destroy') as destroy:
            self.app._exit_app()
            engine.close.assert_called_once();destroy.assert_not_called()
            self.app._finish_exit();self.root.update()
            destroy.assert_called_once()


if __name__=='__main__':unittest.main()

