"""Dữ liệu cục bộ của tiện ích Hỗ trợ ĐK KCB HIS và bản chụp dữ liệu cho một lượt chạy."""
import copy
import json
import uuid
from pathlib import Path


class HisEnvironment:
    MAX_ROWS=10000
    MAX_FIELDS=50

    def __init__(self,path):
        self.path=Path(path)
        self.installed=False
        self.fields=[]
        self.rows=[{}]
        self.error=''
        if self.path.exists():
            try:
                if self.path.stat().st_size>30*1024*1024: raise ValueError('Bảng vượt quá 30 MB.')
                data=json.loads(self.path.read_text(encoding='utf-8'))
                self.validate(data)
                self.installed=data['installed'];self.fields=data['fields'];self.rows=data['rows'] or [{}]
            except (OSError,ValueError,KeyError,TypeError) as error:
                self.error=f'Chưa đọc được bảng dữ liệu: {error}. File được giữ nguyên tại {self.path}.'

    @classmethod
    def validate(cls,data):
        if not isinstance(data,dict) or type(data.get('installed')) is not bool: raise ValueError('Trạng thái tiện ích không hợp lệ.')
        fields=data.get('fields');rows=data.get('rows')
        if not isinstance(fields,list) or len(fields)>cls.MAX_FIELDS: raise ValueError('Tối đa 50 trường dữ liệu.')
        ids=set();names=set()
        for field in fields:
            if not isinstance(field,dict) or not isinstance(field.get('id'),str) or not 1<=len(field['id'])<=80:
                raise ValueError('Mã trường không hợp lệ.')
            if field['id'] in ('stt','add') or not all(char.isascii() and (char.isalnum() or char in '_-') for char in field['id']):
                raise ValueError('Mã trường không hợp lệ.')
            name=field.get('name')
            if not isinstance(name,str) or not name.strip() or len(name)>100 or '\0' in name or name.strip().casefold()=='stt' or name.strip().casefold() in names or field['id'] in ids:
                raise ValueError('Tên trường phải khác nhau, dài tối đa 100 ký tự.')
            ids.add(field['id']);names.add(name.strip().casefold())
        if not isinstance(rows,list) or len(rows)>cls.MAX_ROWS: raise ValueError('Tối đa 10.000 hàng dữ liệu.')
        for row in rows:
            if not isinstance(row,dict) or any(key not in ids or not isinstance(value,str) or len(value)>10000 or '\0' in value for key,value in row.items()):
                raise ValueError('Ô dữ liệu không hợp lệ hoặc quá dài.')

    def update(self,*,installed=None,fields=None,rows=None):
        if self.error: raise ValueError(self.error)
        data={'version':1,'installed':self.installed if installed is None else installed,
              'fields':self.fields if fields is None else fields,'rows':self.rows if rows is None else rows}
        self.validate(data)
        from core import MacroStorage
        MacroStorage._atomic_json(data,self.path)
        self.installed=data['installed'];self.fields=data['fields'];self.rows=data['rows']

    def add_field(self,name):
        name=name.strip()
        fields=self.fields+[{'id':uuid.uuid4().hex,'name':name}]
        self.update(fields=fields)
        return fields[-1]['id']

    def set_cell(self,row,field_id,value):
        if type(row) is not int or not 0<=row<self.MAX_ROWS: raise ValueError('Hàng không hợp lệ.')
        rows=copy.deepcopy(self.rows)
        while len(rows)<=row: rows.append({})
        rows[row][field_id]=value
        self.update(rows=rows)

    def paste(self,row,column,table):
        if not table: return
        if row<0 or column<0 or row+len(table)>self.MAX_ROWS or column+max(map(len,table))>len(self.fields):
            raise ValueError('Bảng dán vượt số hàng hoặc trường hiện có. Hãy thêm đủ trường trước khi dán.')
        rows=copy.deepcopy(self.rows)
        while len(rows)<row+len(table):rows.append({})
        for offset,values in enumerate(table):
            for index,value in enumerate(values):rows[row+offset][self.fields[column+index]['id']]=value
        self.update(rows=rows)

    def prepare(self,actions,loop_count):
        copies=[action for action in actions if action.action_type=='copy_field']
        if not copies:return loop_count,None
        if self.error: raise ValueError(self.error)
        if not self.installed: raise ValueError('Hãy cài Hỗ trợ ĐK KCB HIS trước khi chạy kịch bản lấy dữ liệu từ bảng.')
        ids={field['id'] for field in self.fields}
        names={field['name'].strip().casefold():field['id'] for field in self.fields}
        resolved={}
        last_row=max((index+1 for index,row in enumerate(self.rows) if any(value.strip() for value in row.values())),default=0)
        available=last_row
        for action in copies:
            if type(action.data_row) is not int or not 1<=action.data_row<=self.MAX_ROWS:raise ValueError('STT học dữ liệu không hợp lệ.')
            if not isinstance(action.data_field,str) or action.data_label is not None and not isinstance(action.data_label,str):
                raise ValueError('Tham chiếu trường dữ liệu không hợp lệ.')
            target=action.data_field if action.data_field in ids else names.get((action.data_label or '').strip().casefold())
            if not target:raise ValueError(f'Thiếu trường {action.data_label or action.data_field}. Thêm trường cùng tên hoặc học lại trường trên máy này.')
            if action.data_field in resolved and resolved[action.data_field]!=target:
                raise ValueError('Tham chiếu trường trong kịch bản không nhất quán. Hãy học lại bước lấy dữ liệu.')
            resolved[action.data_field]=target
            available=min(available,last_row-action.data_row+1)
        if len({action.data_row for action in copies})!=1:
            raise ValueError('Các trường trong một kịch bản phải được học từ cùng một STT. Hãy học lại để không trộn dữ liệu giữa các hàng.')
        copies=list({(action.data_field,action.data_row):action for action in copies}.values())
        effective=available if loop_count==0 else loop_count
        if effective<1 or effective>available: raise ValueError(f'Bảng chỉ đủ {max(0,available)} hàng cho kịch bản này. Giảm số lần chạy hoặc thêm dữ liệu.')
        snapshot=copy.deepcopy(self.rows)
        for loop in range(effective):
            for action in copies:
                value=snapshot[action.data_row-1+loop].get(resolved[action.data_field],'')
                if not value.strip(): raise ValueError(f'STT {action.data_row+loop}: trường {action.data_label or action.data_field} đang trống. Hãy bổ sung trước khi chạy.')
        def read(field,row):
            return snapshot[row-1][resolved[field]]
        return effective,read
