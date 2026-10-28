"""Bảng ô có đường kẻ, chọn từng ô và sửa bằng Entry của giao diện."""
import tkinter as tk
from tkinter import font as tkfont


class SheetGrid(tk.Canvas):
    def __init__(self,parent,page_rows=12,max_rows=10000):
        super().__init__(parent,bg='#fffdf8',highlightthickness=1,highlightbackground='#c9c1b1',takefocus=True)
        self.page_rows=page_rows;self.max_rows=max_rows
        self.fields=[];self.rows=[];self.start=0;self.selected=None
        self.selection=None
        self.processed=set();self.current_copy=None
        self.before_scroll=None
        self.on_yview_change=None
        self.font=tkfont.Font(family='Segoe UI',size=10)
        self.header_font=tkfont.Font(family='Segoe UI',size=9,weight='bold')
        self.bind('<Configure>',lambda event:self.draw())
        self.bind('<Map>',lambda event:self.draw())
        self.bind('<MouseWheel>',self._wheel)
        self.bind('<Shift-MouseWheel>',self._horizontal_wheel)

    def set_data(self,fields,rows,start,selected):
        self.fields=fields;self.rows=rows;self.start=start;self.selected=selected;self.draw()

    def yview(self,*args):
        if args and self.before_scroll:self.before_scroll()
        self.geometry_cells()
        total=min(self.max_rows,max(len(self.rows)+1,self.page_rows))
        if not args:return self.start/total,min(1,(self.start+self.page_rows)/total)
        if args[0]=='moveto':start=round(float(args[1])*total)
        else:start=self.start+int(args[1])*(self.page_rows-1 if args[2]=='pages' else 1)
        self.start=max(0,min(start,total-self.page_rows));self.draw()

    def _wheel(self,event):
        self.yview('scroll',-int(event.delta/120) or (-1 if event.delta>0 else 1),'units')
        return 'break'

    def _horizontal_wheel(self,event):
        if self.before_scroll:self.before_scroll()
        self.xview_scroll(-int(event.delta/120) or (-1 if event.delta>0 else 1),'units')
        return 'break'

    def see(self,row,field):
        self.geometry_cells()
        if row<self.start:self.start=row
        elif row>=self.start+self.page_rows:self.start=row-self.page_rows+1
        self.draw()
        if self.winfo_width()<=1:return
        index=next((i+1 for i,f in enumerate(self.fields) if f['id']==field),None)
        if index is None:return
        left,right=self.edges[index:index+2];visible=self.canvasx(0)
        if left<visible:self.xview_moveto(left/self.edges[-1])
        elif right>visible+self.winfo_width():self.xview_moveto((right-self.winfo_width())/self.edges[-1])

    def geometry_cells(self):
        scale=self.winfo_fpixels('1i')/96
        self.row_height=self.font.metrics('linespace')+12
        self.header_height=self.header_font.metrics('linespace')+12
        if self.winfo_ismapped() and self.winfo_height()>1:
            self.page_rows=max(1,(self.winfo_height()-self.header_height-2)//self.row_height)
        self.start=min(self.start,max(0,min(self.max_rows,max(len(self.rows)+1,self.page_rows))-self.page_rows))
        width=max(200,self.winfo_width()-2)
        fixed=round(55*scale);plus=round(36*scale)
        field_width=max(round(170*scale),(width-fixed-plus)/max(1,len(self.fields)))
        edges=[1,fixed+1]
        for _ in self.fields:edges.append(edges[-1]+field_width)
        edges.append(edges[-1]+plus)
        self.edges=edges

    def identify_row(self,y):
        self.geometry_cells()
        offset=int((y-self.header_height)//self.row_height)
        row=self.start+offset
        return str(row) if y>=self.header_height and 0<=offset<self.page_rows and row<self.max_rows else ''

    def identify_column(self,x):
        self.geometry_cells()
        x=self.canvasx(x)
        for index,(left,right) in enumerate(zip(self.edges,self.edges[1:])):
            if left<=x<right:return f'#{index+1}'
        return ''

    def bbox(self,row,field):
        self.geometry_cells();offset=int(row)-self.start
        ids=[item['id'] for item in self.fields]
        if field not in ids or not 0<=offset<self.page_rows:return ()
        index=ids.index(field)+1
        return (self.edges[index]-self.canvasx(0),self.header_height+offset*self.row_height,
                self.edges[index+1]-self.edges[index],self.row_height)

    def fit_text(self,value,width,font):
        text=str(value).replace('\n',' ')[:200]
        if font.measure(text)<=width:return text
        lo,hi=0,len(text)
        while lo<hi:
            mid=(lo+hi+1)//2
            if font.measure(text[:mid]+'…')<=width:lo=mid
            else:hi=mid-1
        return text[:lo]+'…'

    def draw(self):
        self.delete('all');self.geometry_cells()
        self.configure(scrollregion=(0,0,self.edges[-1]+1,self.winfo_height()))
        headings=['STT']+[field['name'] for field in self.fields]+['+']
        for column,heading in enumerate(headings):
            left,right=self.edges[column:column+2]
            self.create_rectangle(left,1,right,self.header_height,fill='#e7dfce',outline='#b9b0a1')
            self.create_text((left+right)/2,self.header_height/2,text=self.fit_text(heading,right-left-8,self.header_font),font=self.header_font,fill='#3e3a35')
        for offset in range(self.page_rows):
            row=self.start+offset;top=self.header_height+offset*self.row_height
            values=[str(row+1)]+[self.rows[row].get(field['id'],'') if row<len(self.rows) else '' for field in self.fields]+['']
            for column,value in enumerate(values):
                left,right=self.edges[column:column+2]
                field=self.fields[column-1]['id'] if 1<=column<=len(self.fields) else None
                selected=field is not None and (self.selected==(row,field) or self.selection is not None and self.selection[0]<=row<=self.selection[2] and self.selection[1]<=column-1<=self.selection[3])
                color='#dfeef6' if selected else '#f5f1e5' if column==0 or row>=self.max_rows else '#fffdf8'
                if field and (row,field) in self.processed:color='#dfedd6'
                if field and self.current_copy==(row,field):color='#ffe2a0'
                self.create_rectangle(left,top,right,top+self.row_height,fill=color,outline='#d7d0c1')
                if row<self.max_rows:
                    self.create_text(left+6,top+self.row_height/2,anchor='w',text=self.fit_text(value,right-left-10,self.font),font=self.font,fill='#3e3a35')
        if self.selected:
            box=self.bbox(str(self.selected[0]),self.selected[1])
            if box:
                x,y,w,h=box;x+=self.canvasx(0)
                self.create_rectangle(x+1,y+1,x+w-1,y+h-1,outline='#4682a2',width=2)
        if self.on_yview_change:self.on_yview_change(*self.yview())
