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
    def __init__(self,parent,app):
        self.app=app;self.model=app.his;self.parent=parent
        self.cell=None;self.editor=None;self.anchor=None;self.extent=None;self.drag_timer=None
        top=ttk.Frame(parent,padding=(12,10));top.pack(fill='x')
        ttk.Label(top,text='Môi trường thao tác',font=('Segoe UI',15,'bold')).pack(side='left')
        self.learn=ttk.Button(top,text='Học với bảng',style='Primary.TButton',command=app._cmd_start_recording)
        self.learn.pack(side='right')
        self.stop=ttk.Button(top,text='Dừng học',style='Danger.TButton',command=app._cmd_stop_recording)
        self.stop.pack(side='right',padx=8)
        self.instructions=ttk.Label(parent,text='Nhấn + ở tiêu đề để thêm trường. Nhấp đúp ô để nhập; dán vùng Excel không gồm STT / tiêu đề.',wraplength=700)
        self.instructions.pack(fill='x',padx=14,pady=(0,6))
        environments=ttk.Frame(parent,padding=(12,4));environments.pack(fill='x')
        ttk.Label(environments,text='Bảng:').pack(side='left',padx=(0,6))
        self.environment_choice=ttk.Combobox(environments,state='readonly',width=26)
        self.environment_choice.pack(side='left',fill='x',expand=True)
        self.environment_choice.bind('<<ComboboxSelected>>',self.switch_environment)
        self.new_button=ttk.Button(environments,text='+ Tạo mới',command=self.new_environment)
        self.new_button.pack(side='left',padx=6)
        self.clear_all_button=ttk.Button(environments,text='Làm trống bảng',style='Danger.TButton',command=self.clear_all)
        self.clear_all_button.pack(side='right')
        controls=ttk.Frame(parent,padding=(12,4));controls.pack(fill='x')
        self.add_field_button=ttk.Button(controls,text='+ Trường dữ liệu',command=self.add_field);self.add_field_button.pack(side='left')
        self.add_row_button=ttk.Button(controls,text='+ Hàng',command=self.add_row);self.add_row_button.pack(side='left',padx=6)
        self.paste_button=ttk.Button(controls,text='Dán dữ liệu · Ctrl+V',command=self.paste);self.paste_button.pack(side='left')
        self.copy_button=ttk.Button(controls,text='Sao chép',style='Info.TButton',command=self.copy_cell);self.copy_button.pack(side='right')
        self.delete_button=ttk.Button(controls,text='Xóa vùng chọn',command=self.clear_selection)
        self.delete_button.pack(side='right',padx=6)
        grid=ttk.Frame(parent);grid.pack(fill='both',expand=True,padx=12,pady=6)
        grid.rowconfigure(0,weight=1);grid.columnconfigure(0,weight=1)
        self.table=SheetGrid(grid,max_rows=self.model.MAX_ROWS)
        self.table.grid(row=0,column=0,sticky='nsew')
        self.vertical=ttk.Scrollbar(grid,orient='vertical',command=self.table.yview)
        self.vertical.grid(row=0,column=1,sticky='ns')
        self.horizontal=ttk.Scrollbar(grid,orient='horizontal',command=self.scroll_horizontal)
        self.horizontal.grid(row=1,column=0,sticky='ew')
        self.table.on_yview_change=self.vertical.set
        self.table.configure(xscrollcommand=self.horizontal.set)
        self.table.before_scroll=self.commit_editor
        self.table.bind('<Button-1>',self.select_cell)
        self.table.bind('<B1-Motion>',self.drag_select)
        self.table.bind('<ButtonRelease-1>',self.end_drag)
        self.table.bind('<Destroy>',self.end_drag)
        self.table.bind('<Double-1>',self.edit_or_copy)
        self.table.bind('<Return>',self.edit_or_copy)
        self.table.bind('<Control-c>',lambda event:self.copy_cell())
        self.table.bind('<Control-v>',lambda event:self.paste())
        self.table.bind('<Control-a>',self.select_all)
        self.table.bind('<Delete>',lambda event:self.clear_selection())
        for key,direction in (('Prior',-1),('Next',1)):
            self.table.bind(f'<{key}>',lambda event,d=direction:self.scroll_page(d))
        for key,delta in (('Left',(0,-1)),('Right',(0,1)),('Up',(-1,0)),('Down',(1,0))):
            self.table.bind(f'<{key}>',lambda event,d=delta:self.move_cell(*d))
            self.table.bind(f'<Shift-{key}>',lambda event,d=delta:self.move_cell(*d,extend=True))
        self.info=ttk.Label(parent,text='Chọn một ô dữ liệu để sao chép.');self.info.pack(fill='x',padx=14)
        ttk.Label(parent,text='Kéo chuột / Shift để quét ô · Ctrl+A chọn tất cả · Delete xóa vùng · Ctrl+C / Ctrl+V sao chép / dán.',
                  wraplength=700).pack(fill='x',padx=14,pady=(4,10))
        self.refresh();self.sync_state()

    def idle(self):
        return not self.app._closing and self.app.manager.state==self.app.manager.STATE_IDLE and not self.app.manager.external_busy and self.app._pending_play is None

    def sync_state(self):
        idle=self.idle()
        for button in (self.add_field_button,self.add_row_button,self.paste_button,self.new_button,self.clear_all_button,self.delete_button):button.configure(state='normal' if idle else 'disabled')
        self.environment_choice.configure(state='readonly' if idle else 'disabled')
        learning=self.app.manager.state==self.app.manager.STATE_RECORDING
        self.copy_button.configure(state='normal' if idle or learning else 'disabled')
        self.learn.configure(state='normal' if idle and self.app.manager.script_activation=='mouse' else 'disabled')
        self.stop.configure(state='normal' if learning and self.app.manager.script_activation=='mouse' else 'disabled')
        self.instructions.configure(text='ĐANG HỌC: nhấp đúp hoặc Sao chép ô → quay về HIS dán. Bấm Môi trường ở bảng nổi để lấy trường tiếp theo.' if learning else
            'Chọn ô rồi Ctrl+V để dán danh sách: mỗi dòng vào một STT. Nhấp đúp để sửa. Dán từ Excel không gồm STT / tiêu đề.')

    def refresh(self):
        self.environment_choice.configure(values=[env['name'] for env in self.model.environments])
        self.environment_choice.current(next(i for i,env in enumerate(self.model.environments) if env['id']==self.model.active_id))
        self.visible_fields=self.model.fields
        self.table.selection=self.selection_bounds()
        self.table.set_data(self.visible_fields,self.model.rows,self.table.start,self.cell)

    def reset_selection(self):
        self.end_drag()
        self.cell=self.anchor=self.extent=None;self.table.selection=None;self.table.start=0
        self.table.xview_moveto(0);self.refresh()

    def new_environment(self):
        if not self.idle():return
        self.commit_editor()
        name=ThemedInputs.askstring('Tạo môi trường mới','Tên bảng mới (bảng hiện tại được giữ lại):',parent=self.parent)
        if not name or not self.idle():return
        try:self.model.create_environment(name);self.reset_selection()
        except (ValueError,OSError) as error:self.app.notify_app('Chưa tạo được môi trường',str(error))

    def switch_environment(self,event=None):
        if not self.idle():self.refresh();return
        index=self.environment_choice.current();self.commit_editor()
        if not 0<=index<len(self.model.environments):return
        try:self.model.select_environment(self.model.environments[index]['id']);self.reset_selection()
        except (ValueError,OSError) as error:self.refresh();self.app.notify_app('Chưa đổi được môi trường',str(error))

    def clear_all(self):
        if not self.idle():return
        self.commit_editor()
        name=next(env['name'] for env in self.model.environments if env['id']==self.model.active_id)
        if not ThemedMessages.askyesno('Làm trống bảng',f'Xóa toàn bộ dữ liệu trong “{name}”? Giữ tên trường, STT và các bảng khác.',parent=self.parent):return
        if not self.idle():return
        try:
            self.model.update(rows=[{}]);self.reset_selection()
            self.info.configure(text=f'Đã làm trống “{name}”. Có thể dán dữ liệu mới.')
        except (ValueError,OSError) as error:self.app.notify_app('Chưa xóa được dữ liệu',str(error))

    def selection_bounds(self):
        if not self.model.fields:return None
        ids=[field['id'] for field in self.model.fields]
        first=self.anchor or self.cell;last=self.extent or self.cell
        if not first or not last or first[1] not in ids or last[1] not in ids:return None
        return min(first[0],last[0]),min(ids.index(first[1]),ids.index(last[1])),max(first[0],last[0]),max(ids.index(first[1]),ids.index(last[1]))

    def show_selection(self):
        self.table.selection=self.selection_bounds();self.table.selected=self.cell;self.table.draw()
        if self.table.selection:
            r1,c1,r2,c2=self.table.selection
            self.info.configure(text=f'Đã chọn {r2-r1+1} hàng × {c2-c1+1} cột · STT {r1+1}–{r2+1} · Delete để xóa dữ liệu')

    def select_all(self,event=None):
        if not self.idle() or not self.model.fields:return 'break'
        self.commit_editor()
        self.cell=self.anchor=(0,self.model.fields[0]['id'])
        self.extent=(max(0,len(self.model.rows)-1),self.model.fields[-1]['id']);self.show_selection()
        return 'break'

    def clear_selection(self):
        if not self.idle():return 'break'
        self.commit_editor();bounds=self.selection_bounds()
        if not bounds:return 'break'
        r1,c1,r2,c2=bounds
        try:
            self.model.clear_cells(r1,r2,c1,c2);self.refresh()
            self.info.configure(text=f'Đã xóa dữ liệu vùng STT {r1+1}–{r2+1}. Giữ nguyên hàng và trường.')
        except (ValueError,OSError) as error:self.app.notify_app('Chưa xóa được vùng chọn',str(error))
        return 'break'

    def scroll_horizontal(self,*args):
        self.commit_editor();self.table.xview(*args)

    def scroll_page(self,direction):
        self.table.yview('scroll',direction,'pages');return 'break'

    def add_field(self):
        if not self.idle():return
        name=ThemedInputs.askstring('Thêm trường dữ liệu','Tên trường (ví dụ: Họ và tên, Ngày sinh, CCCD):',parent=self.parent)
        if not name:return
        try:
            if not self.idle():return
            self.model.add_field(name)
            self.refresh()
            self.cell=(0,self.model.fields[-1]['id'])
            self.anchor=self.extent=self.cell;self.table.selection=self.selection_bounds()
            self.table.selected=self.cell;self.table.see(*self.cell)
        except (ValueError,OSError) as error:self.app.notify_app('Chưa thêm được trường',str(error))

    def add_row(self):
        if not self.idle():return
        try:
            self.model.update(rows=self.model.rows+[{}])
            self.refresh()
            if self.model.fields:
                self.cell=(len(self.model.rows)-1,self.model.fields[0]['id'])
                self.anchor=self.extent=self.cell;self.table.selection=self.selection_bounds()
                self.table.selected=self.cell;self.table.see(*self.cell)
        except (ValueError,OSError) as error:self.app.notify_app('Chưa thêm được hàng',str(error))

    def select_cell(self,event):
        self.end_drag()
        self.commit_editor()
        row=self.table.identify_row(event.y);column=self.table.identify_column(event.x)
        if not row:
            self.cell=self.anchor=self.extent=None;self.table.selection=None;self.table.selected=None;self.table.draw()
        if event.y<self.table.header_height and column==f'#{len(self.visible_fields)+2}':
            self.add_field();return
        if not row or not column:return
        self.table.focus_set()
        index=int(column[1:])-2
        if 0<=index<len(self.visible_fields):
            field=self.visible_fields[index]
            self.cell=(int(row),field['id'])
            if not self.idle() or not getattr(event,'state',0)&1 or not self.anchor:self.anchor=self.cell
            self.extent=self.cell
            self.info.configure(text=f'STT {int(row)+1} · {field["name"]} · Ctrl+C / Sao chép ô')
        else:self.cell=self.anchor=self.extent=None
        self.show_selection()

    def drag_select(self,event):
        if not self.idle() or not self.anchor:return 'break'
        self.end_drag()
        table=self.table
        if event.y<table.header_height:table.yview('scroll',-1,'units')
        elif event.y>=table.header_height+table.page_rows*table.row_height:table.yview('scroll',1,'units')
        if event.x<0:table.xview_scroll(-1,'units')
        elif event.x>=table.winfo_width():table.xview_scroll(1,'units')
        y=max(table.header_height,min(event.y,table.header_height+table.page_rows*table.row_height-1))
        row=table.identify_row(y)
        column=table.identify_column(max(1,min(event.x,table.winfo_width()-2)))
        if row and column:
            index=max(0,min(len(self.model.fields)-1,int(column[1:])-2))
            self.extent=(int(row),self.model.fields[index]['id']);self.show_selection()
        if event.y<table.header_height or event.y>=table.header_height+table.page_rows*table.row_height or event.x<0 or event.x>=table.winfo_width():
            self.drag_timer=table.after(80,lambda:self.drag_select(event))
        return 'break'

    def end_drag(self,event=None):
        if self.drag_timer:
            self.table.after_cancel(self.drag_timer);self.drag_timer=None

    def move_cell(self,dr,dc,extend=False):
        if not self.model.fields:return 'break'
        row,field=(self.extent if extend else self.cell) or (self.table.start,self.visible_fields[0]['id'])
        column=next((i for i,item in enumerate(self.model.fields) if item['id']==field),0)
        row=max(0,min(self.model.MAX_ROWS-1,max(len(self.model.rows),self.table.page_rows-1),row+dr))
        column=max(0,min(len(self.model.fields)-1,column+dc))
        target=(row,self.model.fields[column]['id'])
        if extend and self.idle():
            self.anchor=self.anchor or self.cell or target;self.extent=target
        else:self.cell=self.anchor=self.extent=target
        self.refresh();self.table.see(*target)
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
        entry.bind('<MouseWheel>',self.table._wheel)
        entry.bind('<Shift-MouseWheel>',self.table._horizontal_wheel)
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
        bounds=self.selection_bounds()
        if state==self.app.manager.STATE_IDLE and bounds and (bounds[0]!=bounds[2] or bounds[1]!=bounds[3]):
            r1,c1,r2,c2=bounds
            stream=io.StringIO(newline='');writer=csv.writer(stream,delimiter='\t',lineterminator='\r\n')
            for row in range(r1,r2+1):writer.writerow([self.model.rows[row].get(field['id'],'') if row<len(self.model.rows) else '' for field in self.model.fields[c1:c2+1]])
            try:set_clipboard_text(stream.getvalue())
            except (OSError,ValueError,RuntimeError) as error:self.app.notify_app('Chưa sao chép được',str(error))
            else:self.info.configure(text=f'Đã sao chép {r2-r1+1} hàng × {c2-c1+1} cột.')
            return 'break'
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
            values=list(csv.reader(io.StringIO(text,newline=None),delimiter='\t'))
            if not values or not any(values):raise ValueError('Clipboard chưa có dữ liệu để dán.')
            if not self.model.fields:raise ValueError('Nhấn + để thêm trường dữ liệu trước khi dán danh sách.')
            bounds=self.selection_bounds()
            row,field=(bounds[0],self.model.fields[bounds[1]]['id']) if bounds else self.cell if self.cell else (0,self.model.fields[0]['id'])
            column=next((i for i,f in enumerate(self.model.fields) if f['id']==field),0)
            if values and values[0]:
                first=[value.strip().casefold() for value in values[0]]
                names=[item['name'].strip().casefold() for item in self.model.fields[column:column+len(first)]]
                if first[0]=='stt' or first==names:
                    raise ValueError('Vùng dán đang gồm STT / tiêu đề. Chỉ chọn các ô dữ liệu trong Excel rồi dán lại.')
            self.model.paste(row,column,values)
            self.refresh()
            self.cell=(row,self.model.fields[column]['id'])
            self.anchor=self.cell;self.extent=(row+len(values)-1,self.model.fields[column+max(map(len,values))-1]['id'])
            self.table.selection=self.selection_bounds()
            self.table.selected=self.cell;self.table.see(*self.cell);self.table.focus_set()
            self.info.configure(text=f'Đã dán {len(values)} hàng · STT {row+1}–{row+len(values)} · {self.model.fields[column]["name"]}')
        except (tk.TclError,ValueError,OSError,csv.Error) as error:self.app.notify_app('Chưa dán được bảng',str(error))
        return 'break'
