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


class MultipleEnvironmentTests(unittest.TestCase):
    setUp=HisDataTests.setUp
    copies=HisDataTests.copies
    def test_field_customization_keeps_ids_and_deleted_sources_never_use_another_table(self):
        actions=self.copies();original=self.model.active_id
        self.model.rename_field(self.name,'Tên người đăng ký');self.model.move_field(self.name,1)
        self.assertEqual(self.model.fields[1]['id'],self.name)
        self.assertEqual(self.model.prepare(actions,1)[1](self.name,1),'Mẫu A')
        before=self.model.path.read_bytes()
        with patch.object(MacroStorage,'_atomic_json',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.model.delete_field(self.name)
        self.assertEqual(self.model.path.read_bytes(),before)
        self.model.delete_field(self.name);self.model.delete_field(self.code)
        self.assertEqual(self.model.fields,[]);self.assertEqual(self.model.rows,[{},{},{}])
        self.model.create_environment('Bảng khác');self.model.add_field('Họ và tên');self.model.add_field('CCCD')
        self.model.paste(0,0,[['Không được lấy','00000']])
        with self.assertRaisesRegex(ValueError,'đã bị xóa'):self.model.prepare(actions,1)
        loaded=HisEnvironment(self.model.path)
        with self.assertRaisesRegex(ValueError,'đã bị xóa'):loaded.prepare(actions,1)
        loaded.select_environment(original)
        self.assertEqual(len(loaded.environments[0]['removed_fields']),2)

    def test_copy_progress_callback_only_after_clipboard_success(self):
        _,reader=self.model.prepare(self.copies(),1)
        with patch('core.mouse.Controller'),patch('core.keyboard.Controller'):player=MacroPlayer()
        player.field_reader=reader;player.on_field_copied=Mock()
        with patch('core.set_clipboard_text'):
            player._execute_action(self.copies()[0])
        player.on_field_copied.assert_called_once_with(self.model.active_id,self.name,1)
        with patch('core.set_clipboard_text',side_effect=OSError('clipboard busy')):
            with self.assertRaises(OSError):player._execute_action(self.copies()[1])
        self.assertEqual(player.on_field_copied.call_count,1)
    def test_create_switch_reload_and_play_uses_learned_table(self):
        original=self.model.active_id;actions=self.copies()
        self.model.create_environment('Bảng mới')
        new=self.model.active_id;self.assertNotEqual(new,original);self.assertEqual(self.model.fields,[])
        field=self.model.add_field('Họ và tên');self.model.set_cell(0,field,'Bảng thứ hai')
        with self.assertRaisesRegex(ValueError,'nhiều môi trường'):
            self.model.prepare(actions+[MacroAction('copy_field',0,data_field=field,data_row=1)],1)
        loops,read=self.model.prepare(actions,3)
        self.assertEqual(read(self.name,2),'Mẫu B')
        self.model.select_environment(original)
        self.assertEqual(self.model.rows[0][self.code],'00123')
        self.model.update(rows=[{}])
        self.model.select_environment(new);self.assertEqual(self.model.rows[0][field],'Bảng thứ hai')
        loaded=HisEnvironment(self.model.path)
        self.assertEqual(loaded.active_id,new);self.assertEqual(len(loaded.environments),2)
        loaded.select_environment(original);self.assertEqual(loaded.rows,[{}]);self.assertEqual(len(loaded.fields),2)

    def test_clear_range_preserves_other_cells_and_failed_save_preserves_all(self):
        self.model.clear_cells(0,1,0,0)
        self.assertNotIn(self.name,self.model.rows[0]);self.assertEqual(self.model.rows[1][self.code],'00456')
        self.assertEqual(self.model.rows[2][self.name],'Mẫu C')
        before=self.model.path.read_bytes();rows=self.model.rows
        with patch.object(MacroStorage,'_atomic_json',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.model.clear_cells(0,2,0,1)
            with self.assertRaises(OSError):self.model.create_environment('Lỗi lưu')
        self.assertIs(self.model.rows,rows);self.assertEqual(self.model.path.read_bytes(),before)
        for args in ((-1,1,0,0),(0,1,0,9),(2,1,0,0)):
            with self.assertRaises(ValueError):self.model.clear_cells(*args)

    def test_old_file_migrates_without_losing_fields_or_rows(self):
        import json
        old=dict(installed=True,version=1,fields=self.model.fields,rows=self.model.rows)
        self.model.path.write_text(json.dumps(old,ensure_ascii=False),encoding='utf-8')
        loaded=HisEnvironment(self.model.path);self.assertFalse(loaded.error)
        loaded.create_environment('Mới');loaded.select_environment('default')
        self.assertEqual(loaded.rows[0][self.code],'00123')
        self.assertEqual(json.loads(loaded.path.read_text())['version'],2)
        before=loaded.path.read_bytes()
        with patch.object(loaded,'MAX_BYTES',1):
            with self.assertRaises(ValueError):loaded.set_cell(0,self.name,'Không được lưu')
        self.assertEqual(loaded.path.read_bytes(),before)


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
        self.app.his_window.focus_force=Mock()

    def test_install_remove_reinstall_keeps_fields_and_rows(self):
        self.assertEqual(len(self.app.tabs.tabs()),6)
        self.install();self.assertEqual(len(self.app.tabs.tabs()),6)
        self.assertIsInstance(self.app.his_window,tk.Toplevel)
        field=self.app.his.add_field('Họ và tên');self.app.his.set_cell(0,field,'Dữ liệu mẫu')
        self.app._set_his_installed(False)
        self.assertIsNone(self.app.his_panel);self.assertEqual(len(self.app.tabs.tabs()),6)
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
            self.assertEqual(self.app.his_window.state(),'normal')
            self.assertEqual(self.app.manager.state,MacroManager.STATE_RECORDING)
            self.app.manager.stop_recording()

    def test_paste_ten_names_from_external_text_then_multiple_excel_columns(self):
        self.install();name=self.app.his.add_field('Họ và tên');code=self.app.his.add_field('CCCD')
        panel=self.app.his_panel;panel.refresh();panel.cell=(0,name)
        text='\r\n'.join(f'Người mẫu {i}' for i in range(1,11))+'\r\n'
        with patch.object(self.root,'clipboard_get',return_value=text):panel.paste()
        self.assertEqual([row[name] for row in self.app.his.rows],[f'Người mẫu {i}' for i in range(1,11)])
        self.assertIn('STT 1–10',panel.info.cget('text'))
        panel.cell=panel.anchor=panel.extent=(8,name)
        with patch.object(self.root,'clipboard_get',return_value='Tên mới 9\t00009\r\nTên mới 10\t00010\r\n'):panel.paste()
        self.assertEqual(self.app.his.rows[9],{name:'Tên mới 10',code:'00010'})
        panel.cell=panel.anchor=panel.extent=(1,code)
        with patch.object(self.root,'clipboard_get',return_value='001\r002'):panel.paste()
        self.assertEqual(self.app.his.rows[1][code],'001')
        self.assertEqual(self.app.his.rows[2][name],'Người mẫu 3')

    def test_scroll_large_sheet_and_select_edit_after_scrolling(self):
        from types import SimpleNamespace
        self.install();field=self.app.his.add_field('Họ và tên')
        self.app.his.paste(0,0,[[f'Mẫu {i}'] for i in range(1,1001)])
        panel=self.app.his_panel;panel.refresh();table=panel.table
        table.yview('moveto',.5);self.assertGreater(table.start,450)
        self.root.update_idletasks()
        self.assertEqual(panel.vertical.get(),table.yview())
        x=(table.edges[1]+table.edges[2])/2-table.canvasx(0)
        panel.select_cell(SimpleNamespace(x=x,y=table.header_height+table.row_height/2))
        row=table.start;self.assertEqual(panel.cell,(row,field))
        panel.edit_or_copy();panel.editor[0].delete(0,'end');panel.editor[0].insert(0,'Đã sửa')
        table.yview('scroll',1,'units')
        self.assertIsNone(panel.editor);self.assertEqual(self.app.his.rows[row][field],'Đã sửa')
        self.assertEqual(table.start,row+1)
        table._wheel(SimpleNamespace(delta=-120));self.assertEqual(table.start,row+2)
        table.yview('moveto',1);self.assertEqual(table.yview()[1],1)
        self.assertLess(len(table.find_all()),300)
        self.assertEqual(table.identify_row(table.header_height-1),'')
        table.yview('moveto',0);self.assertEqual(table.start,0)

    def test_horizontal_scroll_and_keyboard_keep_selected_field_visible(self):
        from types import SimpleNamespace
        self.install()
        for i in range(10):self.app.his.add_field(f'Trường {i+1}')
        panel=self.app.his_panel;panel.refresh();table=panel.table
        with patch.object(table,'winfo_width',return_value=700):
            table.draw();panel.cell=(0,self.app.his.fields[0]['id'])
            for _ in range(9):panel.move_cell(0,1)
            box=table.bbox('0',self.app.his.fields[-1]['id'])
            self.assertTrue(box);self.assertGreaterEqual(box[0],0);self.assertLessEqual(box[0]+box[2],701)
            self.assertEqual(table.identify_column(box[0]+10),'#11')
            table._horizontal_wheel(SimpleNamespace(delta=120))

    def test_exit_has_own_tab_and_invokes_full_shutdown(self):
        labels=[self.app.tabs.tab(tab,'text') for tab in self.app.tabs.tabs()]
        self.assertEqual(labels[-1],'Thoát toàn bộ')
        for installed in (True,False,True):
            with patch.object(self.app,'_show_his_environment'):self.app._set_his_installed(installed)
            self.assertEqual(self.app.tabs.tabs()[-1],str(self.app.exit_tab))
        self.assertTrue(self.app.tabs.tab(self.app.exit_tab,'image'))
        self.root.update()
        with patch.object(self.app,'_exit_app') as exit_app:
            self.app.tabs.select(self.app.exit_tab);self.root.update()
            exit_app.assert_called_once()

    def test_drag_shift_select_copy_delete_and_select_all(self):
        from types import SimpleNamespace
        self.install();name=self.app.his.add_field('Họ và tên');code=self.app.his.add_field('CCCD')
        self.app.his.paste(0,0,[['Mẫu 1','001'],['Mẫu 2','002'],['Mẫu 3','003']])
        panel=self.app.his_panel;panel.refresh();table=panel.table
        with patch.object(table,'winfo_width',return_value=700):
            table.geometry_cells()
            x=(table.edges[1]+table.edges[2])/2-table.canvasx(0)
            panel.select_cell(SimpleNamespace(x=x,y=table.header_height+table.row_height/2,state=0))
            x2=(table.edges[2]+table.edges[3])/2-table.canvasx(0)
            panel.drag_select(SimpleNamespace(x=x2,y=table.header_height+table.row_height*1.5))
            panel.end_drag();self.assertEqual(panel.selection_bounds(),(0,0,1,1))
            with patch('extensions_ui.set_clipboard_text') as copy:panel.copy_cell()
            copy.assert_called_once_with('Mẫu 1\t001\r\nMẫu 2\t002\r\n')
            panel.clear_selection()
            self.assertEqual(self.app.his.rows,[{},{},{name:'Mẫu 3',code:'003'}])
            panel.select_all();self.assertEqual(panel.selection_bounds(),(0,0,2,1))
            panel.clear_selection();self.assertEqual(self.app.his.rows,[{},{},{}])
            panel.select_cell(SimpleNamespace(x=x,y=table.header_height+table.row_height/2,state=0))
            panel.move_cell(1,1,extend=True);self.assertEqual(panel.selection_bounds(),(0,0,1,1))
            panel.select_cell(SimpleNamespace(x=x2,y=table.header_height+table.row_height*2.5,state=1))
            self.assertEqual(panel.selection_bounds(),(0,0,2,1))
            panel.drag_select(SimpleNamespace(x=x2,y=table.header_height+table.row_height*table.page_rows+10))
            self.assertIsNotNone(panel.drag_timer)
            panel.end_drag();self.assertIsNone(panel.drag_timer)

    def test_new_switch_and_clear_all_only_current_environment(self):
        from extensions_ui import ThemedInputs,ThemedMessages
        self.install();field=self.app.his.add_field('Tên');self.app.his.set_cell(0,field,'Giữ lại')
        panel=self.app.his_panel;panel.refresh()
        with patch.object(ThemedInputs,'askstring',return_value='Bảng 2'):panel.new_environment()
        self.assertEqual(len(self.app.his.environments),2);self.assertEqual(self.app.his.fields,[])
        second=self.app.his.add_field('Tên');self.app.his.set_cell(0,second,'Xóa thử');panel.refresh()
        with patch.object(ThemedMessages,'askyesno',return_value=False):panel.clear_all()
        self.assertEqual(self.app.his.rows[0][second],'Xóa thử')
        with patch.object(ThemedMessages,'askyesno',return_value=True):panel.clear_all()
        self.assertEqual(self.app.his.rows,[{}]);self.assertEqual(self.app.his.fields[0]['id'],second)
        panel.environment_choice.current(0);panel.switch_environment()
        self.assertEqual(self.app.his.rows[0][field],'Giữ lại')
        self.app.manager.external_busy=True
        with patch.object(ThemedInputs,'askstring') as ask,patch.object(ThemedMessages,'askyesno') as confirm:
            panel.new_environment();panel.clear_all();panel.clear_selection();panel.select_all()
            ask.assert_not_called();confirm.assert_not_called()
        self.assertEqual(self.app.his.rows[0][field],'Giữ lại')

    def test_header_field_menu_rename_move_delete_confirmation_and_busy_guard(self):
        from extensions_ui import ThemedInputs,ThemedMessages
        from types import SimpleNamespace
        self.install();name=self.app.his.add_field('Tên');code=self.app.his.add_field('CCCD')
        self.app.his.paste(0,0,[['Mẫu','001']]);panel=self.app.his_panel;panel.refresh()
        panel.table.geometry_cells()
        x=(panel.table.edges[1]+panel.table.edges[2])/2-panel.table.canvasx(0)
        panel.select_cell(SimpleNamespace(x=x,y=5))
        self.assertEqual(panel.selected_field()['id'],name)
        with patch.object(ThemedInputs,'askstring',return_value='Họ và tên'):panel.rename_field()
        panel.move_field(1);self.assertEqual(self.app.his.fields[1]['id'],name)
        with patch.object(ThemedMessages,'askyesno',return_value=False):panel.delete_field()
        self.assertEqual(len(self.app.his.fields),2)
        with patch.object(ThemedMessages,'askyesno',return_value=True):panel.delete_field()
        self.assertEqual(self.app.his.fields,[{'id':code,'name':'CCCD'}])
        self.assertEqual(self.app.his.rows,[{code:'001'}])
        panel.cell=(0,code);self.app.manager.external_busy=True
        with patch.object(ThemedMessages,'askyesno') as ask:panel.delete_field();ask.assert_not_called()

    def test_his_button_always_counts_down_and_stop_cancels_before_learning(self):
        self.install();panel=self.app.his_panel;self.app.countdown_var.set(False)
        self.app._show_his_environment();self.root.update_idletasks()
        with patch.object(self.app,'_do_start_record') as start:
            panel.learn.invoke()
            self.assertEqual(self.app.manager.state,MacroManager.STATE_COUNTDOWN)
            self.assertIn('3 GIÂY',panel.instructions.cget('text'));self.assertFalse(self.app.manager.recorder.is_recording)
            self.assertIn('3',self.app.record_notice.title.cget('text'))
            self.assertEqual(str(panel.stop.cget('state')),'normal')
            panel.stop.invoke();start.assert_not_called()
            self.assertEqual(self.app.manager.state,MacroManager.STATE_IDLE)
            self.app._process_ui_events()
            panel.learn.invoke()
            for seconds in (2,1,0):
                self.root.after_cancel(self.app.countdown_timer);self.app._start_countdown(seconds)
                if seconds:self.assertIn(f'{seconds} GIÂY',panel.instructions.cget('text'))
            start.assert_called_once()

    def test_progress_tracks_real_rows_and_source_without_changing_data(self):
        self.install();name=self.app.his.add_field('Tên');code=self.app.his.add_field('CCCD')
        self.app.his.paste(0,0,[['Mẫu 1','001'],['Mẫu 2','002']]);panel=self.app.his_panel;panel.refresh()
        before=self.app.his.path.read_bytes();env=self.app.his.active_id
        self.app._his_field_copied(env,name,1);self.app._his_field_copied(env,code,1);panel.refresh()
        self.assertIn((0,name),panel.table.processed);self.assertEqual(panel.table.current_copy,(0,code))
        self.app._his_field_copied(env,name,2);panel.finish_progress(False)
        self.assertEqual(panel.current_copy,(env,1,name))
        self.assertIn('Đã dừng tại',panel.progress_info.cget('text'))
        panel.finish_progress(True);self.assertIsNone(panel.current_copy)
        self.assertEqual(len(panel.completed[env]),3)
        self.assertEqual(self.app.his.path.read_bytes(),before)
        panel.reset_progress();self.assertFalse(panel.table.processed)

    def test_worker_playback_reports_each_copied_cell_to_ui_in_loop_order(self):
        self.install();name=self.app.his.add_field('Tên');code=self.app.his.add_field('CCCD')
        self.app.his.paste(0,0,[['Mẫu 1','001'],['Mẫu 2','002'],['Mẫu 3','003']])
        actions=[MacroAction('copy_field',0,data_field=field,data_row=1) for field in (name,code)]
        player=self.app.manager.player;player.mouse_controller=Mock();player.keyboard_controller=Mock()
        player.field_reader=self.app.his.prepare(actions,3)[1]
        self.app.manager._set_state(MacroManager.STATE_PLAYING)
        with patch('core.play_sound'),patch('core.set_clipboard_text') as copied:
            player.play_async(actions,10,3,0);player._play_thread.join(3)
            self.assertFalse(player.is_playing)
            self.app._process_ui_events()
        self.assertEqual([call.args[0] for call in copied.call_args_list],['Mẫu 1','001','Mẫu 2','002','Mẫu 3','003'])
        panel=self.app.his_panel
        self.assertEqual(panel.table.processed,{(row,field) for row in range(3) for field in (name,code)})
        self.assertIsNone(panel.table.current_copy);self.assertIn('STT 3',panel.latest_copy)

    def test_full_exit_preserves_private_learning_actions(self):
        engine=Mock();engine.recording=True;engine.thread.is_alive.return_value=False
        engine.actions=[{'kind':'text','text':'Mẫu công việc'}]
        panel=self.app.workspace;panel.engine=engine;panel.job_mode='web';panel.job_size=(1280,720)
        with patch.object(self.root,'destroy'):
            self.app._exit_app();self.root.update()
        self.assertTrue(panel.library_path.exists())
        self.assertEqual(panel.actions,engine.actions)

    def test_installation_feedback_and_separate_window_lifecycle(self):
        from extensions_ui import ThemedMessages
        extension=self.app.extensions
        extension.change_installation(True)
        self.assertTrue(extension.busy)
        self.assertIn('Đang cài',extension.status.cget('text'))
        with patch.object(self.app,'_do_start_record') as start:
            self.app._cmd_start_recording();start.assert_not_called()
        extension.finish_installation(True)
        self.assertFalse(extension.busy);self.assertTrue(self.app.his.installed)
        self.assertIn('HOÀN TẤT',extension.status.cget('text'))
        win=self.app.his_window;win.focus_force=Mock()
        self.assertEqual(win.state(),'withdrawn');self.assertEqual(len(self.app.tabs.tabs()),6)
        self.assertNotIn('Môi trường thao tác',[self.app.tabs.tab(tab,'text') for tab in self.app.tabs.tabs()])
        field=self.app.his.add_field('Tên');self.app.his.set_cell(0,field,'Mẫu giữ lại')
        self.app._show_his_environment();self.assertEqual(self.root.state(),'withdrawn')
        self.app._hide_his_environment();self.assertEqual(win.state(),'withdrawn')
        with patch.object(ThemedMessages,'askyesno',return_value=False):extension.change_installation(False)
        self.assertTrue(self.app.his.installed)
        with patch.object(ThemedMessages,'askyesno',return_value=True):extension.change_installation(False)
        self.assertTrue(extension.busy);extension.finish_installation(False)
        self.assertIsNone(self.app.his_window);self.assertFalse(win.winfo_exists())
        extension.change_installation(True);extension.finish_installation(True)
        self.assertEqual(self.app.his.rows[0][field],'Mẫu giữ lại')

    def test_panel_environment_button_and_hide_move_restore_during_work(self):
        from types import SimpleNamespace
        self.install();self.app._pin_controls();notice=self.app.record_notice
        self.root.update_idletasks()
        self.assertIsNotNone(notice.environment_button)
        self.assertEqual(str(notice.environment_button.cget('state')),'normal')
        with patch.object(self.app,'_show_his_environment') as open_environment:
            notice.on_environment=open_environment;notice.environment_button.invoke();open_environment.assert_called_once()
        notice.set_busy(True);notice.start_drag_at(notice.window.winfo_x()+10,notice.window.winfo_y()+10)
        recorder=self.app.manager.recorder;recorder.is_recording=True
        from pynput import mouse
        with patch.object(self.app,'_is_own_window',return_value=False):
            recorder._on_mouse_click(5,5,mouse.Button.left,True)
            self.assertEqual(recorder.actions,[])
        recorder.is_recording=False
        self.app.overlay_input.active=True
        monitor=SimpleNamespace(left=-1920,top=0,right=0,bottom=1080)
        with patch.object(notice,'_work_area',return_value=monitor):
            notice.drag_to(-1500,200)
            self.assertEqual(notice.position,(-1510,190))
            self.assertEqual(self.app.overlay_input.bounds[0],notice.window.winfo_rootx())
            self.app._hide_controls();notice.show('Đang chạy','Vẫn tiếp tục',progress=40)
            self.assertEqual(notice.window.state(),'withdrawn')
            self.assertTrue(notice.hidden);self.assertEqual(notice.position,(-1510,190))
            self.assertEqual(self.app.overlay_input.bounds,(0,0,0,0))
            self.app._toggle_controls()
            self.assertFalse(notice.hidden);self.assertEqual(notice.window.state(),'normal')
        self.app.overlay_input.active=False

    def test_exit_waits_for_private_worker_then_destroys_root(self):
        engine=Mock();engine.thread.is_alive.side_effect=[True,False]
        self.app.workspace.engine=engine
        with patch.object(self.root,'destroy') as destroy:
            self.app._exit_app()
            engine.close.assert_called_once();destroy.assert_not_called()
            self.app._finish_exit();self.root.update()
            destroy.assert_called_once()

    def test_fast_panel_drag_keeps_only_latest_position_without_queue_backlog(self):
        before=self.app._ui_events.qsize()
        for index in range(1000):self.app._queue_panel_drag(index,index+1)
        self.assertEqual(self.app._ui_events.qsize(),before)
        with patch.object(self.app.record_notice,'drag_to') as move:
            self.app._process_ui_events()
            move.assert_called_once_with(999,1000)
        self.assertIsNone(self.app._pending_panel_drag)


if __name__=='__main__':unittest.main()

