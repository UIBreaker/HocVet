"""Kiểm tra các hộp thoại dùng giao diện chung và hành vi Lưu / Hủy."""
import tkinter as tk
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
        self.addCleanup(self.root.destroy)

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
