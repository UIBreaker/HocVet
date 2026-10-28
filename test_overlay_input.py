import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from overlay_input import OverlayInput


class Suppressed(Exception): pass


class InputFilterTests(unittest.TestCase):
    def setUp(self):
        self.route=OverlayInput()
        self.route.listener=Mock()
        self.route.listener.suppress_event.side_effect=Suppressed
        self.route.active=True
        self.route.bounds=(10,10,200,300)
        self.route.stop_bounds=(100,240,190,290)
        self.route.on_stop=Mock()

    def data(self,x=150,y=260,flags=0,extra=0):
        return SimpleNamespace(pt=SimpleNamespace(x=x,y=y),flags=flags,dwExtraInfo=extra)

    def test_injected_click_and_scroll_pass_through_without_stop(self):
        for message in (0x200,0x201,0x202,0x20A):
            self.assertTrue(self.route._filter(message,self.data(flags=1)))
        self.route.listener.suppress_event.assert_not_called()
        self.route.on_stop.assert_not_called()

    def test_physical_drag_and_close_route_without_affecting_injected_actions(self):
        self.route.drag_bounds=(10,10,140,60);self.route.close_bounds=(150,10,195,60)
        self.route.on_drag_start=Mock();self.route.on_drag_move=Mock();self.route.on_hide=Mock()
        self.assertTrue(self.route._filter(0x201,self.data(x=30,y=30,flags=1)))
        self.assertTrue(self.route._filter(0x201,self.data(x=170,y=30,flags=1)))
        self.route.on_drag_start.assert_not_called();self.route.on_hide.assert_not_called()
        with self.assertRaises(Suppressed):self.route._filter(0x201,self.data(x=30,y=30))
        self.assertTrue(self.route._dragging)
        self.assertTrue(self.route._filter(0x200,self.data(x=400,y=400)))
        self.route.on_drag_move.assert_called_once_with(400,400)
        self.assertTrue(self.route._filter(0x202,self.data(flags=1)))
        self.assertTrue(self.route._dragging)
        with self.assertRaises(Suppressed):self.route._filter(0x202,self.data(x=400,y=400))
        self.assertFalse(self.route._dragging)
        with self.assertRaises(Suppressed):self.route._filter(0x201,self.data(x=170,y=30))
        self.route.on_hide.assert_called_once();self.route.on_stop.assert_not_called()
        self.route.bounds=(0,0,0,0)
        with self.assertRaises(Suppressed):self.route._filter(0x202,self.data(x=170,y=30))

    def test_physical_stop_is_swallowed_with_release_even_after_deactivation(self):
        with self.assertRaises(Suppressed):self.route._filter(0x201,self.data())
        self.route.on_stop.assert_called_once()
        self.route.active=False
        with self.assertRaises(Suppressed):self.route._filter(0x202,self.data(x=500,y=500))
        self.assertTrue(self.route._filter(0x202,self.data(x=500,y=500)))

    def test_keyboard_mode_and_non_stop_buttons_cannot_trigger_mouse_actions(self):
        self.route.allow_stop=False
        with self.assertRaises(Suppressed):self.route._filter(0x201,self.data())
        self.route.on_stop.assert_not_called()
        self.route.allow_stop=True
        with self.assertRaises(Suppressed):self.route._filter(0x201,self.data(x=20,y=20))
        self.route.on_stop.assert_not_called()
        self.assertTrue(self.route._filter(0x201,self.data(x=500,y=500)))

    def test_marker_acknowledges_queue_and_styles_are_restored(self):
        self.route.user=Mock()
        self.route.user.GetWindowLongPtrW.return_value=0x8000080
        self.route.active=False
        self.route.activate(123,(10,10,200,300),(100,240,190,290),Mock(),True)
        self.assertEqual(self.route.user.SetWindowLongPtrW.call_args.args,(123,-20,0x80800A0))
        with self.assertRaises(Suppressed):self.route._filter(0x20A,self.data(flags=1,extra=self.route._MARKER))
        self.assertTrue(self.route._drained.is_set())
        self.route.deactivate()
        self.assertEqual(self.route.user.SetWindowLongPtrW.call_args.args,(123,-20,0x8000080))


@unittest.skipUnless(os.getenv('HOCVET_INTEGRATION')=='1','Chỉ chạy trên cửa sổ kiểm thử cục bộ')
class NativePassThroughTests(unittest.TestCase):
    def test_real_playback_reaches_window_under_panel_without_pressing_panel(self):
        import ctypes
        from ctypes import wintypes
        import tkinter as tk
        from pynput import mouse
        from core import MacroPlayer,MacroAction,ScriptProfile
        from record_notice import RecordNotice
        from ui_theme import apply_theme
        root=tk.Tk();root.withdraw();apply_theme(root,root.winfo_fpixels('1i')/96)
        notice=RecordNotice(root);route=OverlayInput();controller=mouse.Controller()
        original_position=controller.position
        under=None
        player=None
        try:
            run=Mock();stop=Mock()
            notice.pin([ScriptProfile(name='Chỉ là kịch bản mẫu',actions=[MacroAction('key_press',0,key='a')])],run,stop,Mock())
            notice.set_busy(True);root.update()
            win=notice.window
            x,y,w,h=win.winfo_rootx(),win.winfo_rooty(),win.winfo_width(),win.winfo_height()
            under=tk.Toplevel(root);under.overrideredirect(True);under.attributes('-topmost',True)
            under.geometry(f'{w}x{h}+{x}+{y}')
            canvas=tk.Canvas(under,bg='#bbddbb',highlightthickness=0);canvas.pack(fill='both',expand=True)
            clicks=[];wheels=[]
            canvas.bind('<Button-1>',lambda e:clicks.append((e.x_root,e.y_root)))
            canvas.bind('<MouseWheel>',lambda e:wheels.append(e.delta))
            root.update();win.lift();root.update()
            button=notice.stop_button
            bx,by=button.winfo_rootx(),button.winfo_rooty()
            bw,bh=button.winfo_width(),button.winfo_height()
            px,py=bx+bw//2,by+bh//2
            events=[]
            event_filter=route._filter
            def traced(message,data):
                events.append((message,data.flags,data.dwExtraInfo))
                return event_filter(message,data)
            route._filter=traced
            route.activate(notice.hwnd,(x,y,x+w,y+h),(bx,by,bx+bw,by+bh),stop,True)
            user=ctypes.windll.user32
            user.WindowFromPoint.argtypes=[wintypes.POINT];user.WindowFromPoint.restype=wintypes.HWND
            target=user.WindowFromPoint(wintypes.POINT(px,py))
            user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT];user.GetAncestor.restype=wintypes.HWND
            self.assertEqual(user.GetAncestor(target,2),user.GetAncestor(under.winfo_id(),2),'Không gửi chuột nếu bên dưới không phải cửa sổ kiểm thử')
            actions=[]
            for _ in range(5):
                actions += [MacroAction('mouse_click',.1,x=px,y=py,button='left',pressed=True),
                            MacroAction('mouse_click',.1,x=px,y=py,button='left',pressed=False)]
            actions.append(MacroAction('mouse_scroll',.1,x=px,y=py,dy=-1))
            player=MacroPlayer();player.on_input_finished=route.drain
            player.protect_mouse=lambda xx,yy:user.GetAncestor(user.WindowFromPoint(wintypes.POINT(xx,yy)),2)==notice.hwnd
            import queue
            progress=queue.Queue()
            player.on_step=lambda step,total,*_:progress.put((step,total))
            finished=[];player.on_finished=lambda *args:finished.append(args)
            with patch('core.play_sound'):
                player.play_async(actions,speed=10)
                until=time.monotonic()+5
                while time.monotonic()<until and player.is_playing:
                    while not progress.empty():
                        step,total=progress.get_nowait()
                        notice.show('Đang phát qua bảng',f'Bước {step}/{total}',progress=step/total*100)
                    root.update();time.sleep(.005)
                self.assertFalse(player.is_playing)
            root.update()
            self.assertEqual(finished,[(True,False)],f'{player.last_error}; events={events[-20:]}')
            self.assertEqual(len(clicks),5)
            self.assertTrue(wheels)
            run.assert_not_called();stop.assert_not_called()
            notice.show('Đã hoàn tất','Bảng nhận chuột trở lại.',progress=100)
            route.deactivate();root.update()
            self.assertEqual(user.GetAncestor(user.WindowFromPoint(wintypes.POINT(px,py)),2),notice.hwnd)
        finally:
            if player and player.is_playing:player.stop();player._play_thread.join(3)
            route.close()
            controller.position=original_position
            if under:under.destroy()
            notice.close(force=True);root.destroy()
