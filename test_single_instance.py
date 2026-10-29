import subprocess
import sys
import unittest
import uuid
from unittest.mock import Mock,patch

from single_instance import SingleInstance


class InstanceTests(unittest.TestCase):
    def test_secondary_does_not_create_ui(self):
        import ui
        instance=Mock(primary=False)
        with patch('single_instance.SingleInstance',return_value=instance),patch.object(ui.tk,'Tk') as create_root:
            ui.run_app()
        create_root.assert_not_called();instance.close.assert_called_once()

    def test_primary_reopens_existing_ui_on_request_and_releases_lock(self):
        import ui
        instance=Mock(primary=True);instance.requested.return_value=True
        root=Mock();app=Mock();app._closing=False
        root.winfo_fpixels.return_value=96
        root.mainloop.side_effect=lambda:root.after.call_args.args[1]()
        with patch('single_instance.SingleInstance',return_value=instance),patch.object(ui.tk,'Tk',return_value=root),patch.object(ui,'HocVetApp',return_value=app),patch.object(ui,'apply_theme'),patch.object(ui,'enable_dpi_awareness'):
            ui.run_app()
        app._show_from_tray.assert_called_once();instance.close.assert_called_once()

    def test_second_process_notifies_primary_and_reopen_after_close(self):
        name='HocVet.Test.'+uuid.uuid4().hex
        first=SingleInstance(name)
        try:
            self.assertTrue(first.primary);self.assertFalse(first.requested())
            code='from single_instance import SingleInstance; import sys; x=SingleInstance(sys.argv[1]); print(x.primary); x.close()'
            children=[subprocess.Popen([sys.executable,'-c',code,name],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(6)]
            for child in children:
                stdout,stderr=child.communicate(timeout=10)
                self.assertEqual(child.returncode,0,stderr)
                self.assertEqual(stdout.strip(),'False')
            self.assertTrue(first.requested());self.assertFalse(first.requested())
        finally:first.close()
        new=SingleInstance(name)
        try:self.assertTrue(new.primary)
        finally:new.close()

    def test_crashed_primary_does_not_leave_stale_lock(self):
        name='HocVet.Test.'+uuid.uuid4().hex
        code='from single_instance import SingleInstance; import sys; x=SingleInstance(sys.argv[1]); print(x.primary,flush=True); sys.stdin.read()'
        child=subprocess.Popen([sys.executable,'-c',code,name],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(),'True')
            second=SingleInstance(name)
            try:self.assertFalse(second.primary)
            finally:second.close()
        finally:
            child.terminate();child.communicate(timeout=10)
        reopened=SingleInstance(name)
        try:self.assertTrue(reopened.primary)
        finally:reopened.close()


if __name__=='__main__':unittest.main()
