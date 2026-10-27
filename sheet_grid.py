"""Bảng ô có đường kẻ, chọn từng ô và sửa bằng Entry của giao diện."""
import tkinter as tk
from tkinter import font as tkfont


class SheetGrid(tk.Canvas):
    def __init__(self,parent,page_rows=12,max_rows=10000):
        super().__init__(parent,bg='#fffdf8',highlightthickness=1,highlightbackground='#c9c1b1',takefocus=True)
        self.page_rows=page_rows;self.max_rows=max_rows
        self.fields=[];self.rows=[];self.start=0;self.selected=None
        self.font=tkfont.Font(family='Segoe UI',size=10)
        self.header_font=tkfont.Font(family='Segoe UI',size=9,weight='bold')
        self.bind('<Configure>',lambda event:self.draw())

    def set_data(self,fields,rows,start,selected):
        self.fields=fields;self.rows=rows;self.start=start;self.selected=selected;self.draw()

    def geometry_cells(self):
        scale=self.winfo_fpixels('1i')/96
        self.row_height=self.font.metrics('linespace')+12
        self.header_height=self.header_font.metrics('linespace')+12
        width=max(200,self.winfo_width()-2)
        fixed=round(55*scale);plus=round(36*scale)
        field_width=max(50,(width-fixed-plus)/max(1,len(self.fields)))
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
        for index,(left,right) in enumerate(zip(self.edges,self.edges[1:])):
            if left<=x<right:return f'#{index+1}'
        return ''

    def bbox(self,row,field):
        self.geometry_cells();offset=int(row)-self.start
        ids=[item['id'] for item in self.fields]
        if field not in ids or not 0<=offset<self.page_rows:return ()
        index=ids.index(field)+1
        return (self.edges[index],self.header_height+offset*self.row_height,
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
                selected=field is not None and self.selected==(row,field)
                color='#dfeef6' if selected else '#f5f1e5' if column==0 or row>=self.max_rows else '#fffdf8'
                self.create_rectangle(left,top,right,top+self.row_height,fill=color,outline='#d7d0c1')
                if row<self.max_rows:
                    self.create_text(left+6,top+self.row_height/2,anchor='w',text=self.fit_text(value,right-left-10,self.font),font=self.font,fill='#3e3a35')
        if self.selected:
            box=self.bbox(str(self.selected[0]),self.selected[1])
            if box:
                x,y,w,h=box;self.create_rectangle(x+1,y+1,x+w-1,y+h-1,outline='#4682a2',width=2)
