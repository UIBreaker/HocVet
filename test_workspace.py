import io
import os
from pathlib import Path
import queue
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from PIL import Image
from workspace import BrowserWorkspace, WindowsWorkspace, WorkspaceEngine, validate_actions


def png():
    data=io.BytesIO();Image.new('RGB',(100,80),'white').save(data,format='PNG');return data.getvalue()


class Backend:
    size=(100,80)
    def __init__(self):self.actions=[];self.closed=False
    def open(self,target):self.target=target
    def execute(self,action):self.actions.append(dict(action))
    def screenshot(self):return png()
    def close(self):self.closed=True
    def _check(self):pass


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        folder=Path(__file__).parent/'build'/'test-workspace';folder.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=folder);self.addCleanup(self.temp.cleanup)
        self.events=queue.Queue();self.backend=Backend()
        self.engine=WorkspaceEngine(self.temp.name,lambda *event:self.events.put(event),lambda mode:self.backend)
        self.addCleanup(self.close)
    def close(self):
        self.engine.close();self.engine.thread.join(4)
        self.assertFalse(self.engine.thread.is_alive())
    def event(self,name):
        end=time.monotonic()+4
        while time.monotonic()<end:
            event,data=self.events.get(timeout=max(.01,end-time.monotonic()))
            if event=='error':self.fail(data)
            if event==name:return data
        self.fail('Missing event '+name)
    def open(self):
        self.engine.submit('open',('web','about:blank'));self.event('ready')

    def test_record_stop_and_replay_while_preview_hidden(self):
        self.open();self.engine.submit('record');self.event('recording')
        self.engine.submit('input',{'kind':'click','x':10,'y':20,'button':'left'});self.event('recording')
        self.engine.submit('input',{'kind':'text','text':'khám sức khoẻ'});self.event('recording')
        self.engine.stop();actions=self.event('learned')
        self.assertEqual(len(actions),2)
        self.backend.actions.clear();self.engine.preview_visible=False
        self.engine.submit('run',(actions,10,(100,80)));self.event('done')
        self.assertEqual([a['kind'] for a in self.backend.actions],['click','text'])
        self.assertEqual(self.engine.cursor,(10,20))

    def test_stop_interrupts_delay_before_any_input(self):
        self.open()
        self.engine.submit('run',([{'kind':'text','text':'no','delay':20}],1))
        end=time.monotonic()+1
        while not self.engine.running and time.monotonic()<end:time.sleep(.005)
        self.engine.stop();self.event('stopped')
        self.assertEqual(self.backend.actions,[])

    def test_cancel_queued_run_does_not_start_after_stop(self):
        entered=threading.Event();release=threading.Event()
        def blocked(target):entered.set();release.wait(3)
        self.backend.open=blocked
        self.engine.submit('open',('web','about:blank'));self.assertTrue(entered.wait(1))
        self.engine.submit('run',([{'kind':'text','text':'no'}],1))
        self.engine.stop();release.set();self.event('stopped')
        time.sleep(.1)
        self.assertEqual(self.backend.actions,[])

    def test_window_size_change_stops_job_before_click(self):
        self.engine.submit('open',('window',{}));self.event('ready')
        self.engine.submit('run',([{'kind':'click','x':1,'y':2}],1,(200,200)))
        while True:
            event,data=self.events.get(timeout=3)
            if event=='error':break
        self.assertIn('kích thước',data)
        self.assertEqual(self.backend.actions,[])

    def test_validation_rejects_desktop_macros_and_bad_values(self):
        for actions in ([{'action_type':'mouse_click','x':1,'y':2}], [{'kind':'click','x':-1,'y':0}],
                        [{'kind':'key','key':'Alt+F4'}],[{'kind':'text','text':4}],
                        [{'kind':'wait','delay':float('nan')}],[{'kind':'scroll','x':0,'y':0,'delta':999999}]):
            with self.assertRaises(ValueError):validate_actions(actions)
        validate_actions([{'kind':'text','text':'Tiếng Việt'},{'kind':'key','key':'Enter'}])


class NativeRoutingTests(unittest.TestCase):
    def test_messages_only_go_to_locked_window(self):
        backend=WindowsWorkspace();backend.hwnd=100;backend.pid=9;backend.focus=101
        backend._check=Mock();backend.user=Mock()
        backend.user.GetAncestor.return_value=100
        def class_name(hwnd,buffer,size):buffer.value='Edit';return 4
        backend.user.GetClassNameW.side_effect=class_name
        backend.user.PostMessageW.return_value=True
        backend.execute({'kind':'text','text':'khám'})
        self.assertEqual(backend.user.PostMessageW.call_count,4)
        self.assertTrue(all(c.args[0]==101 and c.args[1]==0x102 for c in backend.user.PostMessageW.call_args_list))
        backend.user.PostMessageW.reset_mock();backend.user.GetAncestor.return_value=200
        with self.assertRaises(RuntimeError):backend.execute({'kind':'text','text':'no'})
        backend.user.PostMessageW.assert_not_called()

    def test_identity_change_and_minimize_fail_without_desktop_fallback(self):
        backend=WindowsWorkspace();backend.hwnd=100;backend.pid=9;backend.user=Mock()
        backend.user.IsWindow.return_value=True
        def wrong(hwnd,pointer):pointer._obj.value=8
        backend.user.GetWindowThreadProcessId.side_effect=wrong
        with self.assertRaisesRegex(RuntimeError,'đã đổi'):backend._check()
        def correct(hwnd,pointer):pointer._obj.value=9
        backend.user.GetWindowThreadProcessId.side_effect=correct
        backend.user.IsIconic.return_value=True
        with self.assertRaisesRegex(RuntimeError,'thu nhỏ'):backend._check()


@unittest.skipUnless(os.environ.get('HOCVET_INTEGRATION')=='1','Integration runs explicitly against local fixtures')
class IntegrationTests(unittest.TestCase):
    def setUp(self):
        folder=Path(__file__).parent/'build'/'test-integration';folder.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=folder);self.addCleanup(self.temp.cleanup)

    def test_real_headless_edge_uses_own_input_and_renders(self):
        backend=BrowserWorkspace(Path(self.temp.name)/'edge')
        try:
            backend.open('about:blank')
            backend.page.set_content('<input id="name" style="margin:40px;width:300px"><button id="ok" onclick="this.textContent=\'Done\'">Run</button>')
            box=backend.page.locator('#name').bounding_box()
            backend.execute({'kind':'click','x':int(box['x']+20),'y':int(box['y']+10)})
            backend.execute({'kind':'text','text':'Khám sức khoẻ'})
            self.assertEqual(backend.page.locator('#name').input_value(),'Khám sức khoẻ')
            box=backend.page.locator('#ok').bounding_box()
            backend.execute({'kind':'click','x':int(box['x']+10),'y':int(box['y']+10)})
            self.assertEqual(backend.page.locator('#ok').inner_text(),'Done')
            self.assertEqual(Image.open(io.BytesIO(backend.screenshot())).size,(1280,720))
        finally:backend.close()

    def test_real_windows_edit_accepts_messages_without_mouse_movement(self):
        import ctypes
        from ctypes import wintypes
        user=ctypes.windll.user32
        user.CreateWindowExW.argtypes=[wintypes.DWORD,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD,
            ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.HWND,wintypes.HMENU,wintypes.HINSTANCE,ctypes.c_void_p]
        user.CreateWindowExW.restype=wintypes.HWND
        user.DestroyWindow.argtypes=[wintypes.HWND]
        root=user.CreateWindowExW(0,'STATIC','HocVet test fixture',0x00CF0000,40,40,500,260,None,None,None,None)
        edit=user.CreateWindowExW(0,'EDIT','',0x50010080,20,20,350,70,root,None,None,None)
        self.assertTrue(root and edit)
        backend=WindowsWorkspace()
        try:
            user.ShowWindow(root,4)
            user.GetForegroundWindow.restype=wintypes.HWND
            foreground=user.GetForegroundWindow()
            point=wintypes.POINT();user.GetCursorPos(ctypes.byref(point));before=(point.x,point.y)
            backend.open({'hwnd':int(root),'pid':os.getpid()})
            backend.execute({'kind':'click','x':30,'y':30})
            backend.execute({'kind':'text','text':'Khám sức khoẻ'})
            msg=wintypes.MSG()
            while user.PeekMessageW(ctypes.byref(msg),None,0,0,1):
                user.TranslateMessage(ctypes.byref(msg));user.DispatchMessageW(ctypes.byref(msg))
            text=ctypes.create_unicode_buffer(100)
            user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
            user.GetWindowTextW(edit,text,100)
            self.assertEqual(text.value,'Khám sức khoẻ')
            self.assertTrue(backend.screenshot().startswith(b'\x89PNG'))
            user.GetCursorPos(ctypes.byref(point));self.assertEqual((point.x,point.y),before)
            self.assertEqual(user.GetForegroundWindow(),foreground)
            backend.close()
            self.assertTrue(user.IsWindow(root))
        finally:user.DestroyWindow(root)


if __name__=='__main__':unittest.main()
