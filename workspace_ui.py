"""Giao diện phiên web / cửa sổ riêng, không phát sự kiện vào desktop."""
import io
import json
import queue
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog

from PIL import Image, ImageTk
from workspace import WorkspaceEngine, validate_actions, window_list
from ui_theme import VINTAGE_BG, VINTAGE_CARD_BG, VINTAGE_TEXT_HEAD, VINTAGE_TEXT_MUTED, BTN_RED_TOP


class WorkspacePanel:
    def __init__(self, parent, app):
        self.app, self.parent = app, parent
        self.engine = None
        self.actions = []
        self.job_mode = None
        self.job_size = None
        self._needs_open = True
        self.windows = []
        self.image = self.photo = None
        self._settings_built = False
        self.mode = tk.StringVar(value='web')
        self.address = tk.StringVar(value='https://example.com')
        self.text = tk.StringVar()
        self.name = tk.StringVar(value='Công việc mới')
        self.library_path = Path(app.manager.library_path).with_name('workspace_scripts.json')
        self.library = {}
        if self.library_path.exists():
            try:
                self.library = json.loads(self.library_path.read_text(encoding='utf-8'))
                if not isinstance(self.library, dict):
                    raise ValueError('Thư viện công việc phải là một đối tượng.')
            except (ValueError, OSError):
                self.library = {}
                self._library_unreadable = True
                app._post(app.notify_app, 'Chưa đọc được công việc đã lưu', 'File được giữ nguyên; hãy kiểm tra bản dự phòng trước khi lưu mới.')
        row = ttk.Frame(parent, padding=(12, 8))
        row.pack(fill='x')
        ttk.Radiobutton(row, text='Web riêng', variable=self.mode, value='web', command=self._mode_changed).pack(side='left')
        ttk.Radiobutton(row, text='Cửa sổ Windows / HIS', variable=self.mode, value='window', command=self._mode_changed).pack(side='left', padx=12)
        self.connect = ttk.Button(row, text='Mở phiên', command=self.open)
        self.connect.pack(side='right')
        self.target_row = ttk.Frame(parent, padding=(12, 0))
        self.target_row.pack(fill='x')
        self.url_entry = ttk.Entry(self.target_row, textvariable=self.address)
        self.window_combo = ttk.Combobox(self.target_row, state='readonly')
        self.refresh = ttk.Button(self.target_row, text='Làm mới cửa sổ', command=self._windows)
        self.info = ttk.Label(parent, wraplength=700, foreground=VINTAGE_TEXT_MUTED)
        self.info.pack(fill='x', padx=14, pady=6)
        controls = ttk.Frame(parent, padding=(12, 4))
        controls.pack(fill='x')
        self.activation_buttons = []
        for label, command in (('Học trong tab', self.learn), ('Dừng', self.stop), ('Chạy công việc', self.run),
                               ('Lưu', self.save), ('Nhập', self.load), ('Chia sẻ', self.export)):
            if label == 'Dừng': command = lambda:self.stop() if self.app.manager.script_activation=='mouse' else None
            button = ttk.Button(controls, text=label, command=command)
            button.pack(side='left', padx=(0, 5))
            if label in ('Học trong tab','Dừng','Chạy công việc'): self.activation_buttons.append(button)
        saved = ttk.Frame(parent, padding=(12, 4))
        saved.pack(fill='x')
        ttk.Label(saved, text='Công việc:').pack(side='left')
        self.saved = ttk.Combobox(saved, textvariable=self.name, values=list(self.library))
        self.saved.pack(side='left', fill='x', expand=True, padx=8)
        self.saved.bind('<<ComboboxSelected>>', self._load_saved)
        self.status = ttk.Label(parent, text='Chưa mở phiên làm việc.')
        self.status.pack(fill='x', padx=14, pady=4)
        self.preview = tk.Canvas(parent, bg='#282924', highlightthickness=0, takefocus=True)
        self.preview.pack(fill='both', expand=True, padx=12, pady=(2, 6))
        self.preview.bind('<Configure>', lambda event: self._draw())
        self.preview.bind('<Button-1>', lambda event: self._click(event, 'left'))
        self.preview.bind('<Button-3>', lambda event: self._click(event, 'right'))
        self.preview.bind('<MouseWheel>', self._scroll)
        self.preview.bind('<KeyPress>', self._key)
        text_row = ttk.Frame(parent, padding=(12, 4, 12, 10))
        text_row.pack(fill='x')
        ttk.Label(text_row, text='Nhập chữ:').pack(side='left')
        entry = ttk.Entry(text_row, textvariable=self.text)
        entry.pack(side='left', fill='x', expand=True, padx=8)
        entry.bind('<Return>', lambda event: self._send_text())
        ttk.Button(text_row, text='Gửi vào phiên', command=self._send_text).pack(side='right')
        self._mode_changed()

    def _mode_changed(self):
        if self.app.manager.external_busy and self.engine:
            self.mode.set(self.engine.mode)
            return
        for widget in (self.url_entry, self.window_combo, self.refresh): widget.pack_forget()
        if self.mode.get() == 'web':
            self.url_entry.pack(fill='x', expand=True)
            self.info.configure(text='Trình duyệt Edge riêng trong tab; chuột đỏ là chuột của phiên. Công việc tiếp tục khi đổi tab / thu vào khay. Đăng nhập ngay trong phiên nếu cần.')
        else:
            self.window_combo.pack(side='left', fill='x', expand=True)
            self.refresh.pack(side='right', padx=(8,0))
            self.info.configure(text='Windows tương thích: ô nhập Edit/RichEdit và nút chuẩn, trong một cửa sổ. Không dùng chuột thật; không thu nhỏ cửa sổ đích. Điều khiển tùy biến, popup hoặc ảnh đen cần phiên Windows/VM riêng.')

    def _windows(self):
        self.windows = window_list()
        self.window_combo.configure(values=[f'{w["title"]} · PID {w["pid"]}' for w in self.windows])
        if self.windows: self.window_combo.current(0)

    def _ensure_engine(self):
        if not self.engine:
            folder = self.library_path.parent / 'web-session'
            folder.mkdir(parents=True, exist_ok=True)
            self.engine = WorkspaceEngine(folder, lambda event, data: self.app._post(self._event, event, data))

    def _available(self):
        if self.app._closing:return False
        if self.app.manager.state != self.app.manager.STATE_IDLE:
            self.app.notify_app('Hãy dừng kịch bản màn hình trước', 'Không chạy đồng thời hai chế độ nhập liệu.')
            return False
        if self.app.manager.external_busy:
            self.app.notify_app('Công việc đang chạy / học', 'Dừng công việc hiện tại trước khi đổi phiên hoặc kịch bản.')
            return False
        return True

    def open(self):
        if not self._available(): return
        if self.mode.get() == 'window':
            index = self.window_combo.current()
            if not 0 <= index < len(self.windows):
                self.app.notify_app('Chọn cửa sổ', 'Bấm Làm mới rồi chọn đúng cửa sổ phần mềm đang mở.')
                return
            target = self.windows[index]
        else:
            target = self.address.get().strip()
        self._ensure_engine()
        self.status.configure(text='Đang mở phiên riêng…')
        self.connect.configure(state='disabled')
        self.engine.submit('open', (self.mode.get(), target))

    def _input(self, action):
        if self.app.manager.state!=self.app.manager.STATE_IDLE:return
        if not self.engine or not self.engine.ready or self.engine.running or self.engine.mode != self.mode.get():
            return
        try:
            self.engine.submit('input', action)
        except queue.Full:
            self.engine.stop()
            self.app.notify_app('Phiên đang xử lý chậm', 'Đã dừng nhận thao tác. Chờ phiên xử lý xong trước khi thử lại.')

    def _point(self, event):
        if not self.image: return None
        width, height = self.image.size
        scale = min(self.preview.winfo_width()/width, self.preview.winfo_height()/height)
        ox = (self.preview.winfo_width()-width*scale)/2
        oy = (self.preview.winfo_height()-height*scale)/2
        x, y = int((event.x-ox)/max(scale,.001)), int((event.y-oy)/max(scale,.001))
        return (x,y) if 0 <= x < width and 0 <= y < height else None

    def _click(self, event, button):
        point = self._point(event)
        if point:
            self.preview.focus_set()
            self._input({'kind':'click','x':point[0],'y':point[1],'button':button})

    def _scroll(self, event):
        point = self._point(event)
        if point:
            self._input({'kind':'scroll','x':point[0],'y':point[1],'delta':-event.delta})
        return 'break'

    def _key(self, event):
        keys = {'Return':'Enter','Tab':'Tab','BackSpace':'Backspace','Delete':'Delete',
                'Left':'ArrowLeft','Right':'ArrowRight','Up':'ArrowUp','Down':'ArrowDown',
                'Home':'Home','End':'End','Escape':'Escape'}
        if event.state & 4 and event.keysym.lower() == 'a':
            self._input({'kind':'key','key':'Control+A'})
        elif event.keysym in keys:
            self._input({'kind':'key','key':keys[event.keysym]})
        elif event.char and event.char.isprintable() and not event.state & 4:
            self._input({'kind':'text','text':event.char})
        return 'break'

    def _send_text(self):
        if self.text.get():
            self._input({'kind':'text','text':self.text.get()})
            self.text.set('')

    def set_activation_mode(self, mode):
        for button in self.activation_buttons:
            button.configure(state='normal' if mode=='mouse' else 'disabled')

    def learn(self, from_hotkey=False):
        if (self.app.manager.script_activation=='hotkey') != from_hotkey: return
        if not self._available() or not self.engine or not self.engine.ready:
            self.app.notify_app('Mở phiên trước', 'Mở Web hoặc chọn cửa sổ Windows, sau đó bấm Học trong tab.')
            return
        self.app.manager.external_busy = True
        self.job_mode = self.engine.mode
        self.job_size = getattr(self.engine.backend, 'size', (1280,720))
        self.engine.submit('record')
        self.status.configure(text='Đang học trong tab: bấm vào ảnh và gõ, hoặc dùng ô Nhập chữ. Bấm Dừng để kết thúc.')

    def stop(self):
        if not self.engine: return
        was_recording = self.engine.recording
        self.engine.stop()
        if was_recording:
            self.status.configure(text='Đang kết thúc lượt học và giữ các thao tác đã nhận…')

    def run(self, from_hotkey=False):
        if (self.app.manager.script_activation=='hotkey') != from_hotkey: return
        if not self._available(): return
        if not self.engine or not self.engine.ready or self._needs_open or self.job_mode != self.engine.mode or self.mode.get()!=self.engine.mode:
            self.app.notify_app('Chọn đúng phiên', 'Mở phiên cùng loại với công việc trước khi chạy. Kịch bản màn hình không dùng trực tiếp trong tab.')
            return
        if not self.actions:
            self.app.notify_app('Chưa có công việc', 'Bấm Học trong tab hoặc nhập file công việc đã học trong tab.')
            return
        self.app.manager.external_busy = True
        self.app._hide_to_tray()
        self.engine.submit('run', (list(self.actions), self.app._parse_speed(), self.job_size))
        self.app.notify_app('Đang chạy công việc riêng', 'Bạn có thể đổi tab hoặc làm việc ở màn hình khác.', progress=0)

    def _event(self, event, data):
        if event == 'ready':
            self._needs_open = False
            self.connect.configure(state='normal')
            self.status.configure(text='Phiên sẵn sàng. Nhấn Học trong tab hoặc tương tác thử trên ảnh xem trước.')
        elif event == 'recording':
            if self.engine and self.engine.recording:
                self.status.configure(text=f'Đang học trong tab · {data} bước')
        elif event == 'learned':
            self.actions = data
            self.app.manager.external_busy = False
            self.status.configure(text=f'Đã dừng học trong tab · {len(data)} bước.')
            if data: self.save()
        elif event == 'progress':
            done,total = data
            self.status.configure(text=f'Đang chạy · {done}/{total} bước · {done/max(1,total):.0%}')
            self.app.notify_app('Công việc riêng đang chạy', f'{self.name.get()} · {done}/{total} bước', progress=done/max(1,total)*100)
        elif event in ('done','stopped','error'):
            self.app.manager.external_busy = False
            self.connect.configure(state='normal')
            if event == 'done':
                count,mode = data
                text = f'Đã gửi {count} thao tác đến cửa sổ; hãy kiểm tra kết quả.' if mode == 'window' else f'Đã hoàn tất {count} thao tác trong trình duyệt riêng.'
                self.status.configure(text=text)
                self.app.notify_app('Công việc đã kết thúc', text, progress=100)
                self.app.record_notice.timer = self.app.root.after(4500, self.app.record_notice.close)
            else:
                text = str(data) if event == 'error' else f'Đã dừng tại bước {data[0]}/{data[1]}.'
                self.status.configure(text=text)
                self.app.notify_app('Công việc đã dừng', text)

    def poll_frame(self):
        if not self.engine: return
        data = self.engine.take_frame()
        if data:
            with Image.open(io.BytesIO(data)) as image:
                self.image = image.convert('RGB')
            self._draw()

    def _draw(self):
        self.preview.delete('all')
        if not self.image:
            self.preview.create_text(max(10,self.preview.winfo_width()/2), max(10,self.preview.winfo_height()/2),
                text='Mở một phiên để xem và thao tác bằng chuột riêng.', fill='#ece7de', width=420)
            return
        width, height = self.image.size
        scale = min(self.preview.winfo_width()/width, self.preview.winfo_height()/height)
        if scale <= 0: return
        image = self.image.resize((max(1,int(width*scale)),max(1,int(height*scale))), Image.Resampling.BILINEAR)
        self.photo = ImageTk.PhotoImage(image)
        ox, oy = (self.preview.winfo_width()-image.width)/2, (self.preview.winfo_height()-image.height)/2
        self.preview.create_image(ox,oy,anchor='nw',image=self.photo)
        if self.engine:
            x,y = self.engine.cursor; x,y = ox+x*scale, oy+y*scale
            self.preview.create_polygon(x,y,x+12,y+20,x+4,y+17,x,y+25,fill=BTN_RED_TOP,outline='white')

    def set_visible(self, visible):
        if self.engine: self.engine.preview_visible = visible

    def _data(self):
        if self.engine and self.engine.recording:
            raise ValueError('Dừng học trước khi lưu.')
        validate_actions(self.actions)
        return {'workspace_script':True,'version':1,'mode':self.job_mode,'size':self.job_size,
                'name':self.name.get().strip() or 'Công việc mới','actions':self.actions,
                'url':self.address.get().strip() if self.job_mode=='web' else ''}

    def save(self):
        if not self._available(): return
        try:
            if getattr(self, '_library_unreadable', False):
                raise ValueError('Thư viện không đọc được. Sao lưu / sửa workspace_scripts.json trước khi lưu; bạn vẫn có thể Chia sẻ công việc hiện tại.')
            data = self._data()
            if not self.actions: raise ValueError('Chưa có thao tác để lưu.')
            from core import MacroStorage
            self.library[data['name']] = data
            MacroStorage._atomic_json(self.library, self.library_path)
            self.saved.configure(values=list(self.library))
            self.app.notify_app('Đã lưu công việc', data['name'])
        except Exception as error:
            self.app.notify_app('Không thể lưu công việc', str(error))

    def _accept(self, data):
        if not isinstance(data,dict) or data.get('workspace_script') is not True or data.get('mode') not in ('web','window'):
            raise ValueError('Chỉ nhập file được học trong tab Công việc, không nhập macro tọa độ màn hình.')
        validate_actions(data.get('actions'))
        size = data.get('size')
        if not isinstance(size,(list,tuple)) or len(size)!=2 or not all(isinstance(v,int) and 0 < v <= 4096 for v in size):
            raise ValueError('Kích thước phiên không hợp lệ.')
        self.actions = [dict(a) for a in data['actions']]
        self.job_mode = data['mode']; self.job_size = tuple(size)
        self._needs_open = True
        if self.job_mode=='web' and isinstance(data.get('url'),str):self.address.set(data['url'])
        self.name.set(str(data.get('name','Công việc được chia sẻ'))[:200])
        self.mode.set(self.job_mode); self._mode_changed()
        self.status.configure(text=f'Đã nạp {len(self.actions)} bước. Mở / chọn đúng phiên rồi chạy.')

    def _load_saved(self, event=None):
        if not self._available(): return
        try: self._accept(self.library[self.name.get()])
        except Exception as error: self.app.notify_app('Không thể nạp',str(error))

    def load(self):
        if not self._available(): return
        path = filedialog.askopenfilename(parent=self.app.root,filetypes=[('Công việc trong tab','*.json')])
        if path:
            try:
                if Path(path).stat().st_size > 30*1024*1024: raise ValueError('File quá lớn.')
                self._accept(json.loads(Path(path).read_text(encoding='utf-8')))
            except Exception as error: self.app.notify_app('Không thể nhập công việc',str(error))

    def export(self):
        if not self._available(): return
        path = filedialog.asksaveasfilename(parent=self.app.root,defaultextension='.json',initialfile='cong-viec.json',filetypes=[('Công việc trong tab','*.json')])
        if path:
            try:
                from core import MacroStorage
                MacroStorage._atomic_json(self._data(),path)
            except Exception as error: self.app.notify_app('Không thể chia sẻ công việc',str(error))

    def close(self):
        if self.engine: self.engine.close()

    def save_on_exit(self):
        if not self.engine or not self.engine.actions:return
        if getattr(self,'_library_unreadable',False):
            raise ValueError('Không thể ghi đè thư viện công việc bị hỏng. Hãy khôi phục bản dự phòng.')
        self.engine.recording=False
        self.actions=[dict(action) for action in self.engine.actions]
        data=self._data()
        from core import MacroStorage
        library=dict(self.library);library[data['name']]=data
        MacroStorage._atomic_json(library,self.library_path)
        self.library=library
