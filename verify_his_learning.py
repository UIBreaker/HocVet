"""Kiểm thử tích hợp học rồi chạy nhiều hàng trên HIS giả lập (Windows)."""
import argparse
import json
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import sync_playwright
from pynput import keyboard,mouse
from core import MacroStorage,ScriptProfile
from ui import HocVetApp


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,default=Path(__file__).resolve().parent.parent/'GiaLapHis'/'ban-chay-truc-tiep.html',help='Trang HTML HIS giả lập trên máy')
    parser.add_argument('--auto-advance',action='store_true',help='Giả lập HIS tự chuyển ô khi ngày / tháng đủ hai chữ số')
    args=parser.parse_args()
    fixture=args.fixture.resolve()
    if not fixture.is_file():parser.error(f'Không tìm thấy trang HIS giả lập: {fixture}')
    output=Path('build/his-learning-auto' if args.auto_advance else 'build/his-learning');output.mkdir(parents=True,exist_ok=True)
    dates=['19/08/1989','29/02/2000','01/12/1995','31/01/1970','09/09/2009']
    report={'dates':dates,'runs':[],'messages':[]}
    with tempfile.TemporaryDirectory(dir=output) as directory,sync_playwright() as playwright:
        browser=playwright.chromium.launch(channel='chrome',headless=False,args=['--window-size=1500,1000','--window-position=0,0'])
        root=tk.Tk();root.withdraw()
        with patch.object(MacroStorage,'default_library_path',return_value=str(Path(directory)/'library.json')),patch.object(HocVetApp,'_setup_system_tray'):
            app=HocVetApp(root)
        original_notify=app.notify_app
        app.notify_app=lambda title,message,**kwargs:(report['messages'].append(title),original_notify(title,message,**kwargs))[-1]
        def pump(seconds):
            deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                root.update();page.wait_for_timeout(20)
        def values():
            return [page.locator('#'+name).input_value() for name in ('birth_day','birth_month','birth_year','birth_extra')]
        def click_day():
            position=page.locator('#birth_day').evaluate('el => {const r=el.getBoundingClientRect(); return {x:(screenX+(outerWidth-innerWidth)/2+r.x+r.width/2)*devicePixelRatio,y:(screenY+(outerHeight-innerHeight)-(outerWidth-innerWidth)/2+r.y+r.height/2)*devicePixelRatio}}')
            pointer=mouse.Controller();pointer.position=(round(position['x']),round(position['y']))
            pointer.click(mouse.Button.left);pump(.1)
            assert page.evaluate('document.activeElement.id')=='birth_day'
            assert not app._is_own_focus()
        try:
            page=browser.new_page(no_viewport=True)
            page.goto(fixture.as_uri())
            app._set_his_installed(True)
            field=app.his.add_field('Ngày sinh')
            app.his.paste(0,0,[[date] for date in dates])
            profile=ScriptProfile(name='Học ngày sinh rồi chạy nhiều hàng')
            app.manager.profiles=[profile];app.manager.active_profile_id=profile.id;app._refresh_profile_deck()
            page.locator('#birth_day').fill('');page.locator('#birth_month').fill('01');page.locator('#birth_year').fill('1999');page.locator('#birth_extra').fill('KEEP')
            keys=keyboard.Controller()
            app.his_panel.cell=(0,field);app.his_panel.copy_cell()
            app.his_window.withdraw();root.withdraw();app.record_notice.hide();root.update()
            page.bring_to_front();page.locator('#birth_day').click()
            click_day()
            keys.press(keyboard.Key.ctrl_l);keys.press('v');keys.release('v');keys.release(keyboard.Key.ctrl_l)
            pump(.2);report['before_configuration']=values()
            assert report['before_configuration']==['19','01','1999','KEEP'],report['before_configuration']
            if args.auto_advance:
                page.evaluate('''() => {
                    for (const [id,next] of [['birth_day','birth_month'],['birth_month','birth_year']]) {
                        document.getElementById(id).addEventListener('input',event => {
                            if(event.target.value.length===2) document.getElementById(next).focus();
                        });
                    }
                }''')
            app.his_panel.show_selection()
            app.his_panel.paste_mode_choice.current(2 if args.auto_advance else 1)
            app.his_panel.paste_mode_choice.event_generate('<<ComboboxSelected>>')
            assert app.his.fields[0].get('paste_mode')==('date_dmy_auto' if args.auto_advance else 'date_dmy')
            app._cmd_start_recording(force_countdown=True)
            pump(3.5)
            assert app.manager.state==app.manager.STATE_RECORDING
            app.his_panel.cell=(0,field);app.his_panel.copy_cell();root.update()
            assert app.date_paste.pending is not None
            app.his_window.withdraw();root.withdraw();app.record_notice.hide();root.update()
            page.bring_to_front();page.locator('#full_name').click()
            assert not app._is_own_focus()
            # Dùng đúng bộ chuột của phần mềm để listener ghi điểm bấm ô ngày.
            click_day()
            keys.press(keyboard.Key.ctrl_l);keys.press('v');keys.release('v');keys.release(keyboard.Key.ctrl_l)
            deadline=time.monotonic()+5
            while (app.date_paste.pending or app.date_paste.busy) and time.monotonic()<deadline:pump(.03)
            report['learning']=values()
            assert report['learning']==['19','08','1989','KEEP'],report
            app._cmd_stop_recording();pump(.15)
            report['actions']=[action.to_dict() for action in profile.actions]
            assert any(action.action_type=='mouse_click' for action in profile.actions),report['actions']
            assert sum(action.action_type=='paste_date' for action in profile.actions)==1,report['actions']
            # Kiểm tra chính kịch bản đã lưu, không tự dựng bước dán để chạy thử.
            loaded,_=MacroStorage.load_library(app.manager.library_path)
            saved=next(item for item in loaded if item.id==profile.id)
            assert [a.to_dict() for a in saved.actions]==report['actions']
            app.manager.profiles=[saved];app.manager.active_profile_id=saved.id
            for speed in ('1.0x','10.0x'):
                results=[]
                original_copied=app.manager.player.on_field_copied
                def verify_row(env,field_id,row):
                    actual=values();expected=dates[row-1].split('/')+['KEEP']
                    results.append({'row':row,'actual':actual,'expected':expected,'ok':actual==expected})
                    page.screenshot(path=str(output/f'{speed}-row-{row}.png'))
                    app._his_field_copied(env,field_id,row)
                app.manager.player.on_field_copied=lambda *args:app._post(verify_row,*args)
                app.speed_var.set(speed);app.loop_count_var.set(str(len(dates)));app.loop_delay_var.set('1')
                app._cmd_start_playing()
                deadline=time.monotonic()+30
                while (app._pending_play is not None or app.manager.player.is_playing or len(results)<len(dates)) and time.monotonic()<deadline:pump(.03)
                pump(.1)
                report['runs'].append({'speed':speed,'rows':results,'error':app.manager.player.last_error})
                assert not app.manager.player.last_error,report['runs'][-1]
                assert len(results)==len(dates) and all(row['ok'] for row in results),report['runs'][-1]
                app.manager.player.on_field_copied=original_copied
                print(json.dumps(report['runs'][-1],ensure_ascii=False),flush=True)
            report['ok']=True
        finally:
            (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            app.manager.player.stop();app.manager.stop_global_hotkeys();app.manager.recorder.stop()
            root.destroy();browser.close()


if __name__=='__main__':main()
