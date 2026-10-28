"""Kiểm tra các hộp thoại dùng giao diện chung và hành vi Lưu / Hủy."""
import tkinter as tk
import gc
from tkinter import ttk
import unittest
from pathlib import Path
import hashlib
import tempfile
import zipfile
from unittest.mock import patch

from app_info import APP_VERSION
from ui_theme import apply_theme, create_dialog, ThemedInputs, ThemedMessages, VINTAGE_BG, VINTAGE_CARD_BG


class ThemeTests(unittest.TestCase):
    def _destroy_root(self):
        self.root.destroy()
        self.root = None
        gc.collect()

    def test_panel_keeps_footer_visible_after_busy_shrink_environment_and_reopen(self):
        from record_notice import RecordNotice
        from core import ScriptProfile,MacroAction
        from unittest.mock import Mock
        notice=RecordNotice(self.root);self.addCleanup(lambda:notice.close(force=True))
        profiles=[ScriptProfile(name='Kịch bản có tên dài để kiểm tra bố cục',actions=[MacroAction('key_press',0,key='a')])]
        notice.pin(profiles,Mock(),Mock(),Mock(),size=(420,680))
        self.root.update()
        notice.set_busy(True)
        notice.window.geometry('420x430')
        self.root.update()
        self.assertTrue(notice.stop_button.winfo_ismapped())
        self.assertLessEqual(notice.stop_button.winfo_rooty()+notice.stop_button.winfo_height(),notice.window.winfo_rooty()+notice.window.winfo_height())
        for installed in (True,False,True):
            notice.set_environment_enabled(installed,False)
            notice.show('Đang chạy','Thông báo đổi nội dung khi bảng đang nhỏ.',progress=40)
            self.root.update()
            self.assertTrue(notice.stop_button.winfo_ismapped())
            if installed:
                self.assertTrue(notice.environment_button.winfo_ismapped())
                self.assertLessEqual(notice.environment_button.winfo_rooty()+notice.environment_button.winfo_height(),notice.window.winfo_rooty()+notice.window.winfo_height())
        notice.set_busy(False);notice.hide();notice.hidden=False
        notice.pin(profiles,Mock(),Mock(),Mock(),size=(420,430))
        self.root.update()
        self.assertTrue(notice.stop_button.winfo_ismapped())

    def test_panel_repeated_layout_changes_at_different_dpi_keep_controls_inside(self):
        from record_notice import RecordNotice
        from core import ScriptProfile
        from unittest.mock import Mock
        from types import SimpleNamespace
        original=float(self.root.tk.call('tk','scaling'))
        try:
            for scaling in (4/3,5/3,2,8/3):
                self.root.tk.call('tk','scaling',scaling);apply_theme(self.root,self.root.winfo_fpixels('1i')/96)
                notice=RecordNotice(self.root)
                with patch.object(notice,'_work_area',return_value=SimpleNamespace(left=0,top=0,right=1400,bottom=760)):
                    try:
                        notice.pin([ScriptProfile(name='Kịch bản mẫu để kiểm tra chiều cao')],Mock(),Mock(),Mock(),size=(440,600))
                        for cycle in range(6):
                            notice.set_busy(bool(cycle%2));notice.set_environment_enabled(bool(cycle%3),False)
                            notice.show('Bảng điều khiển · đang cập nhật','Nội dung tiến độ thay đổi nhưng các nút vẫn phải hiển thị.',progress=cycle*10)
                            self.root.update()
                            for button in [notice.stop_button,notice.repeat_buttons[-1]]+([notice.environment_button] if notice.environment_button else []):
                                self.assertTrue(button.winfo_ismapped(),(scaling,cycle))
                                self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),notice.window.winfo_rooty()+notice.window.winfo_height(),(scaling,cycle))
                            notice.hide();notice.hidden=False
                    finally:notice.close(force=True)
        finally:self.root.tk.call('tk','scaling',original)

    def test_panel_repeat_controls_and_resizing_reflow_without_clipping_stop(self):
        from record_notice import RecordNotice
        from core import ScriptProfile,MacroAction
        from unittest.mock import Mock
        profiles=[ScriptProfile(name=f'Kịch bản {i}',actions=[MacroAction('key_press',0,key='a')]) for i in range(20)]
        notice=RecordNotice(self.root);self.addCleanup(lambda:notice.close(force=True))
        repeat=Mock();resized=Mock()
        notice.pin(profiles,Mock(),Mock(),Mock(),on_repeat=repeat,on_resize=resized)
        self.root.update()
        notice.repeat_buttons[2].invoke()
        repeat.assert_called_with(profiles[0].id,2)
        notice.repeat_buttons[1].invoke()
        repeat.assert_called_with(profiles[0].id,None)
        notice.resize(340,300)
        self.root.update()
        self.assertEqual(notice.per_page,1)
        self.assertTrue(notice.stop_button.winfo_ismapped())
        self.assertLessEqual(notice.stop_button.winfo_rooty()+notice.stop_button.winfo_height(),notice.window.winfo_rooty()+notice.window.winfo_height())
        notice.resize(500,900)
        self.root.update()
        self.assertGreater(notice.per_page,1)
        self.assertGreater(int(notice.name_labels[0].cget('wraplength')),200)
        previous=(notice.window.winfo_width(),notice.window.winfo_height())
        notice.show('Tiến trình','Không đổi kích thước khi cập nhật',progress=50)
        self.root.update()
        self.assertEqual(previous,(notice.window.winfo_width(),notice.window.winfo_height()))
        notice.set_busy(True)
        notice.resize(700,950)
        self.root.update()
        self.assertEqual(previous,(notice.window.winfo_width(),notice.window.winfo_height()))
        self.assertTrue(all('disabled' in button.state() for button in notice.repeat_buttons))

    def test_pinned_panel_pages_scripts_keeps_progress_and_disables_runs_when_busy(self):
        from record_notice import RecordNotice
        from core import ScriptProfile, MacroAction
        from unittest.mock import Mock
        profiles=[ScriptProfile(name=f'Công việc số {i}', actions=[MacroAction('key_press',0,key='a')]) for i in range(17)]
        notice=RecordNotice(self.root);self.addCleanup(lambda:notice.close(force=True))
        run=Mock()
        notice.pin(profiles,run,Mock(),Mock())
        self.root.update()
        notice._page(1)
        notice.run_buttons[0].invoke()
        run.assert_called_once_with(profiles[3].id)
        notice.show('Đang chạy','6/10 bước',progress=60,duration=10)
        self.assertIsNone(notice.timer)
        self.assertEqual(notice.progress.cget('value'),60)
        self.assertLess(notice.progress.winfo_rooty(), notice.launcher.winfo_rooty())
        notice.set_busy(True)
        self.assertTrue(all('disabled' in button.state() for button in notice.run_buttons))
        notice.close()
        self.assertTrue(notice.window.winfo_exists())

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        apply_theme(self.root, self.root.winfo_fpixels('1i') / 96)
        self.addCleanup(self._destroy_root)

    def dialog(self):
        return next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel))

    def click(self, win, label):
        next(w for w in win.footer.winfo_children()
             if isinstance(w, ttk.Button) and w.cget('text') == label).invoke()

    def test_shared_styles_and_version_header(self):
        win = create_dialog(self.root, 'Điều kiện', 'Thông tin hỗ trợ')
        self.assertEqual(win.cget('background'), VINTAGE_BG)
        self.assertEqual(ttk.Style().lookup('TFrame', 'background'), VINTAGE_CARD_BG)
        header = win.winfo_children()[0]
        self.assertIn(APP_VERSION, header.winfo_children()[0].cget('text'))
        self.assertTrue(win.body.winfo_exists())
        self.assertTrue(win.footer.winfo_exists())
        win.destroy()

    def test_text_input_save_and_cancel(self):
        def save():
            win = self.dialog()
            entry = next(w for w in win.body.winfo_children() if isinstance(w, ttk.Entry))
            entry.delete(0, 'end')
            entry.insert(0, 'Khám sức khoẻ')
            self.click(win, 'Lưu')
        self.root.after(20, save)
        self.assertEqual(ThemedInputs.askstring('Tên', 'Nhập tên:', parent=self.root), 'Khám sức khoẻ')
        self.root.after(20, lambda: self.click(self.dialog(), 'Hủy'))
        self.assertIsNone(ThemedInputs.askstring('Tên', 'Nhập tên:', parent=self.root))

    def test_confirmation_preserves_cancel_and_accept(self):
        self.root.after(20, lambda: self.click(self.dialog(), 'Hủy'))
        self.assertFalse(ThemedMessages.askyesno('Xóa?', 'Xóa kịch bản?', parent=self.root))
        self.root.after(20, lambda: self.click(self.dialog(), 'Xác nhận'))
        self.assertTrue(ThemedMessages.askyesno('Xóa?', 'Xóa kịch bản?', parent=self.root))

    def test_numeric_input_rejects_nan_then_accepts_valid_delay(self):
        observations = []
        def edit():
            win = self.dialog()
            entry = next(w for w in win.body.winfo_children() if isinstance(w, ttk.Entry))
            entry.insert(0, 'nan')
            self.click(win, 'Lưu')
            observations.append(win.winfo_exists())
            entry.delete(0, 'end')
            entry.insert(0, '1.25')
            self.click(win, 'Lưu')
        with patch.object(ThemedMessages, 'showerror') as error:
            self.root.after(20, edit)
            result = ThemedInputs.askfloat('Độ trễ', 'Giây:', parent=self.root, minvalue=0, maxvalue=300)
            error.assert_called_once()
        self.assertEqual(observations, [1])
        self.assertEqual(result, 1.25)

    def test_record_notice_visible_with_hidden_root_without_focus_change(self):
        import ctypes
        from ctypes import wintypes
        from record_notice import RecordNotice
        self.root.update()
        ctypes.windll.user32.GetForegroundWindow.restype = wintypes.HWND
        before = ctypes.windll.user32.GetForegroundWindow()
        notice = RecordNotice(self.root)
        try:
            notice.show('Sắp bắt đầu học', 'Chuyển sang phần mềm cần thao tác', number=3)
            self.root.update()
            self.assertTrue(notice.window.winfo_ismapped())
            self.assertEqual(notice.number.cget('text'), '3')
            self.assertEqual(ctypes.windll.user32.GetForegroundWindow(), before)
            notice.show('Đã dừng và lưu', '12 thao tác', duration=1000)
            self.assertEqual(notice.title.cget('text'), 'Đã dừng và lưu')
        finally:
            notice.close()


class PackageTests(unittest.TestCase):
    def test_package_manifest_and_checksums_exclude_personal_library(self):
        from build_release import package_release
        folder = Path(__file__).parent / 'build' / 'test-packages'
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as temporary:
            root = Path(temporary)
            (root / 'dist').mkdir()
            (root / 'dist' / 'Học Vẹt.exe').write_bytes(b'test executable')
            for name in ('README.md', 'RELEASE_NOTES.md', 'LICENSE'):
                (root / name).write_text(name, encoding='utf-8')
            (root / 'scripts_library.json').write_text('private library', encoding='utf-8')
            exe, archive, sums = package_release(root)
            with zipfile.ZipFile(archive) as package:
                self.assertEqual(set(package.namelist()), {'Học Vẹt.exe', 'README.md', 'RELEASE_NOTES.md', 'LICENSE'})
            expected = '\n'.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}' for path in (exe, archive)) + '\n'
            self.assertEqual(sums.read_text(encoding='utf-8'), expected)


if __name__ == '__main__':
    unittest.main()
