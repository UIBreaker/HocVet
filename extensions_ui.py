"""Tiện ích theo công việc và bảng dữ liệu học sao chép theo từng vòng."""
import csv
import io
import tkinter as tk
from tkinter import ttk

from clipboard_text import set_clipboard_text
from sheet_grid import SheetGrid
from ui_theme import ThemedInputs,ThemedMessages


class ExtensionsPanel:
    def __init__(self,parent,app):
        self.app=app
        body=ttk.Frame(parent,padding=18);body.pack(fill='both',expand=True)
        heading=ttk.Frame(body);heading.pack(fill='x')
        ttk.Label(heading,text='Tính năng mở rộng',font=('Segoe UI',17,'bold')).pack(side='left')
        ttk.Button(heading,text='Thoát toàn bộ',style='Danger.TButton',command=app._exit_app).pack(side='right')
        ttk.Label(body,text='Công cụ được thiết kế riêng cho từng công việc.',wraplength=650).pack(anchor='w',pady=(6,20))
        card=ttk.LabelFrame(body,text='Hỗ trợ ĐK KCB HIS',padding=16);card.pack(fill='x')
        ttk.Label(card,text='Bảng dữ liệu dạng ô: học sao chép từng trường ở một hàng, mỗi vòng chạy lấy hàng kế tiếp.',
            wraplength=620).pack(anchor='w')
        ttk.Label(card,text='Dữ liệu lưu trên máy. Gỡ công cụ sẽ ẩn tab; bảng đã nhập được giữ lại để cài lại.',
            wraplength=620).pack(anchor='w',pady=8)
        self.status=ttk.Label(card);self.status.pack(anchor='w',pady=8)
        actions=ttk.Frame(card);actions.pack(fill='x')
        self.install=ttk.Button(actions,text='Cài đặt',style='Primary.TButton',command=lambda:app._set_his_installed(True))
        self.install.pack(side='left')
        self.open=ttk.Button(actions,text='Mở môi trường thao tác',command=app._show_his_environment)
        self.open.pack(side='left',padx=8)
        self.remove=ttk.Button(actions,text='Gỡ tính năng',style='Danger.TButton',command=lambda:app._set_his_installed(False))
        self.remove.pack(side='right')
        self.refresh()

    def refresh(self):
        model=self.app.his
        self.status.configure(text=model.error or ('Đã cài đặt' if model.installed else 'Chưa cài đặt'))
        idle=self.app.manager.state==self.app.manager.STATE_IDLE and not self.app.manager.external_busy and self.app._pending_play is None
        self.install.configure(state='normal' if idle and not model.installed and not model.error else 'disabled')
        self.remove.configure(state='normal' if idle and model.installed else 'disabled')
        self.open.configure(state='normal' if model.installed else 'disabled')


class HisPanel:
    PAGE_ROWS=12
    PAGE_FIELDS=4

    def __init__(self,parent,app):
        self.app=app;self.model=app.his;self.parent=parent
        self.row_page=self.field_page=0
        self.cell=None;self.editor=None
        top=ttk.Frame(parent,padding=(12,10));top.pack(fill='x')
        ttk.Label(top,text='Môi trường thao tác',font=('Segoe UI',15,'bold')).pack(side='left')
        self.learn=ttk.Button(top,text='Học với bảng',style='Primary.TButton',command=app._cmd_start_recording)
        self.learn.pack(side='right')
        self.stop=ttk.Button(top,text='Dừng học',style='Danger.TButton',command=app._cmd_stop_recording)
        self.stop.pack(side='right',padx=8)
        self.instructions=ttk.Label(parent,text='Nhấn + ở tiêu đề để thêm trường. Nhấp đúp ô để nhập; dán vùng Excel không gồm STT / tiêu đề.',wraplength=700)
        self.instructions.pack(fill='x',padx=14,pady=(0,6))
        controls=ttk.Frame(parent,padding=(12,4));controls.pack(fill='x')
        self.add_field_button=ttk.Button(controls,text='+ Trường dữ liệu',command=self.add_field);self.add_field_button.pack(side='left')
        self.add_row_button=ttk.Button(controls,text='+ Hàng',command=self.add_row);self.add_row_button.pack(side='left',padx=6)
        self.paste_button=ttk.Button(controls,text='Dán bảng từ Excel',command=self.paste);self.paste_button.pack(side='left')
        self.copy_button=ttk.Button(controls,text='Sao chép ô',style='Info.TButton',command=self.copy_cell);self.copy_button.pack(side='right')
        self.table=SheetGrid(parent,page_rows=self.PAGE_ROWS,max_rows=self.model.MAX_ROWS)
        self.table.pack(fill='both',expand=True,padx=12,pady=6)
        self.table.bind('<Button-1>',self.select_cell)
        self.table.bind('<Double-1>',self.edit_or_copy)
        self.table.bind('<Return>',self.edit_or_copy)
        self.table.bind('<Control-c>',lambda event:self.copy_cell())
        self.table.bind('<Control-v>',lambda event:self.paste())
        for key,delta in (('Left',(0,-1)),('Right',(0,1)),('Up',(-1,0)),('Down',(1,0))):
            self.table.bind(f'<{key}>',lambda event,d=delta:self.move_cell(*d))
        self.info=ttk.Label(parent,text='Chọn một ô dữ liệu để sao chép.');self.info.pack(fill='x',padx=14)
        navigation=ttk.Frame(parent,padding=(12,8));navigation.pack(fill='x')
        ttk.Button(navigation,text='‹ Hàng trước',command=lambda:self.change_page('row',-1)).pack(side='left')
        ttk.Button(navigation,text='Hàng sau ›',command=lambda:self.change_page('row',1)).pack(side='left',padx=6)
        self.pages=ttk.Label(navigation);self.pages.pack(side='left',expand=True)
        ttk.Button(navigation,text='‹ Trường trước',command=lambda:self.change_page('field',-1)).pack(side='left')
        ttk.Button(navigation,text='Trường sau ›',command=lambda:self.change_page('field',1)).pack(side='left',padx=(6,0))
        self.refresh();self.sync_state()

    def idle(self):
        return not self.app._closing and self.app.manager.state==self.app.manager.STATE_IDLE and not self.app.manager.external_busy and self.app._pending_play is None

    def sync_state(self):
        idle=self.idle()
        for button in (self.add_field_button,self.add_row_button,self.paste_button):button.configure(state='normal' if idle else 'disabled')
        learning=self.app.manager.state==self.app.manager.STATE_RECORDING
        self.copy_button.configure(state='normal' if idle or learning else 'disabled')
        self.learn.configure(state='normal' if idle and self.app.manager.script_activation=='mouse' else 'disabled')
        self.stop.configure(state='normal' if learning and self.app.manager.script_activation=='mouse' else 'disabled')
        self.instructions.configure(text='ĐANG HỌC: nhấp đúp hoặc Sao chép ô → quay về HIS dán. Bấm Môi trường ở bảng nổi để lấy trường tiếp theo.' if learning else
            'Nhấn + ở tiêu đề để thêm trường. Nhấp đúp ô để nhập; dán vùng Excel không gồm STT / tiêu đề. Khi học, lấy dữ liệu cùng một STT.')

    def refresh(self):
        self.row_page=min(self.row_page,max(0,(len(self.model.rows)-1)//self.PAGE_ROWS))
        self.field_page=min(self.field_page,max(0,(len(self.model.fields)-1)//self.PAGE_FIELDS))
        self.visible_fields=self.model.fields[self.field_page*self.PAGE_FIELDS:(self.field_page+1)*self.PAGE_FIELDS]
        start=self.row_page*self.PAGE_ROWS
        self.table.set_data(self.visible_fields,self.model.rows,start,self.cell)
        self.pages.configure(text=f'Hàng {self.row_page+1}/{max(1,(len(self.model.rows)+self.PAGE_ROWS-1)//self.PAGE_ROWS)} · Trường {self.field_page+1}/{max(1,(len(self.model.fields)+self.PAGE_FIELDS-1)//self.PAGE_FIELDS)}')

    def add_field(self):
        if not self.idle():return
        name=ThemedInputs.askstring('Thêm trường dữ liệu','Tên trường (ví dụ: Họ và tên, Ngày sinh, CCCD):',parent=self.parent)
        if not name:return
        try:
            if not self.idle():return
            self.model.add_field(name)
            self.field_page=(len(self.model.fields)-1)//self.PAGE_FIELDS
            self.refresh()
        except (ValueError,OSError) as error:self.app.notify_app('Chưa thêm được trường',str(error))

    def add_row(self):
        if not self.idle():return
        try:
            self.model.update(rows=self.model.rows+[{}])
            self.row_page=(len(self.model.rows)-1)//self.PAGE_ROWS
            self.refresh()
        except (ValueError,OSError) as error:self.app.notify_app('Chưa thêm được hàng',str(error))

    def change_page(self,kind,delta):
        if self.app.manager.state not in (self.app.manager.STATE_IDLE,self.app.manager.STATE_RECORDING):return
        self.commit_editor()
        self.cell=None
        self.info.configure(text='Chọn ô dữ liệu cần sao chép trên trang này.')
        if kind=='row':self.row_page=max(0,self.row_page+delta)
        else:self.field_page=max(0,self.field_page+delta)
        self.refresh()

    def select_cell(self,event):
        row=self.table.identify_row(event.y);column=self.table.identify_column(event.x)
        if not row:
            self.cell=None;self.table.selected=None;self.table.draw()
        if event.y<self.table.header_height and column==f'#{len(self.visible_fields)+2}':
            self.add_field();return
        if not row or not column:return
        self.table.focus_set()
        index=int(column[1:])-2
        if 0<=index<len(self.visible_fields):
            field=self.visible_fields[index]
            self.cell=(int(row),field['id'])
            self.info.configure(text=f'STT {int(row)+1} · {field["name"]} · Ctrl+C / Sao chép ô')
        else:self.cell=None
        self.table.selected=self.cell;self.table.draw()

    def move_cell(self,dr,dc):
        if not self.model.fields:return 'break'
        row,field=self.cell or (self.row_page*self.PAGE_ROWS,self.visible_fields[0]['id'])
        column=next((i for i,item in enumerate(self.model.fields) if item['id']==field),0)
        row=max(0,min(self.model.MAX_ROWS-1,row+dr))
        column=max(0,min(len(self.model.fields)-1,column+dc))
        self.row_page=min(row//self.PAGE_ROWS,max(0,(len(self.model.rows)-1)//self.PAGE_ROWS))
        row=min(row,(self.row_page+1)*self.PAGE_ROWS-1)
        self.field_page=column//self.PAGE_FIELDS
        self.cell=(row,self.model.fields[column]['id']);self.refresh()
        self.info.configure(text=f'STT {row+1} · {self.model.fields[column]["name"]} · Ctrl+C / Sao chép ô')
        return 'break'

    def edit_or_copy(self,event=None):
        if self.app.manager.state==self.app.manager.STATE_RECORDING:return self.copy_cell()
        if not self.idle() or not self.cell:return 'break'
        self.commit_editor()
        row,field=self.cell
        box=self.table.bbox(str(row),field)
        if not box:return 'break'
        entry=ttk.Entry(self.table)
        entry.insert(0,self.model.rows[row].get(field,'') if row<len(self.model.rows) else '')
        entry.place(x=box[0],y=box[1],width=box[2],height=box[3])
        self.editor=(entry,row,field)
        self.app.manager.shortcuts_suspended=True;self.app.manager.stop_global_hotkeys()
        entry.focus_set();entry.select_range(0,'end')
        entry.bind('<Return>',lambda e:self.commit_editor())
        entry.bind('<Escape>',lambda e:self.commit_editor(cancel=True))
        entry.bind('<FocusOut>',lambda e:self.commit_editor())
        return 'break'

    def commit_editor(self,cancel=False):
        if not self.editor:return
        entry,row,field=self.editor;self.editor=None
        value=entry.get();entry.destroy()
        try:
            if not cancel and self.idle():self.model.set_cell(row,field,value)
        except (ValueError,OSError) as error:self.app.notify_app('Chưa lưu được ô',str(error))
        finally:
            self.app.manager.shortcuts_suspended=False
            if not self.app._closing:self.app.manager.reload_global_hotkeys()
        self.refresh()

    def copy_cell(self):
        state=self.app.manager.state
        if state not in (self.app.manager.STATE_IDLE,self.app.manager.STATE_RECORDING) or self.app.manager.external_busy:return 'break'
        self.commit_editor()
        if not self.cell:
            self.app.notify_app('Chọn ô dữ liệu','Bấm vào ô cần lấy trước khi sao chép.');return 'break'
        row,field_id=self.cell
        field=next((field for field in self.model.fields if field['id']==field_id),None)
        if not field or not 0<=row<self.model.MAX_ROWS:return 'break'
        value=self.model.rows[row].get(field_id,'') if row<len(self.model.rows) else ''
        if not value.strip():
            self.app.notify_app('Ô đang trống',f'STT {row+1} · {field["name"]}: hãy nhập dữ liệu trước khi học.');return 'break'
        if state==self.app.manager.STATE_RECORDING:
            first=next((action for action in self.app.manager.recorder.actions if action.action_type=='copy_field'),None)
            if first and first.data_row!=row+1:
                self.app.notify_app('Hãy lấy cùng một STT',f'Lượt học này đang lấy STT {first.data_row}. Chọn các trường trên cùng hàng đó.');return 'break'
        try:set_clipboard_text(value)
        except (OSError,ValueError,RuntimeError) as error:
            self.app.notify_app('Chưa sao chép được',str(error));return 'break'
        if state==self.app.manager.STATE_RECORDING:
            self.app.manager.recorder.record_field(field_id,field['name'],row+1)
            self.app.root.withdraw()
            self.app.workspace.set_visible(False)
        self.app.notify_app('Đã sao chép ô',f'STT {row+1} · {field["name"]}. Quay về HIS và dán.')
        return 'break'

    def paste(self):
        if not self.idle():return 'break'
        self.commit_editor()
        try:
            text=self.app.root.clipboard_get()
            if len(text)>5000000:raise ValueError('Bảng dán quá lớn.')
            values=list(csv.reader(io.StringIO(text),delimiter='\t'))
            row,field=self.cell if self.cell else (0,self.model.fields[0]['id'] if self.model.fields else '')
            column=next((i for i,f in enumerate(self.model.fields) if f['id']==field),0)
            if values and values[0]:
                first=[value.strip().casefold() for value in values[0]]
                names=[item['name'].strip().casefold() for item in self.model.fields[column:column+len(first)]]
                if first[0]=='stt' or first==names:
                    raise ValueError('Vùng dán đang gồm STT / tiêu đề. Chỉ chọn các ô dữ liệu trong Excel rồi dán lại.')
            self.model.paste(row,column,values)
            self.refresh()
        except (tk.TclError,ValueError,OSError) as error:self.app.notify_app('Chưa dán được bảng',str(error))
        return 'break'
