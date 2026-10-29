"""So sánh ô đang nhận bàn phím bằng Windows UI Automation, không đọc nội dung ô."""
import ctypes
import uuid


class FocusedInput:
    def __init__(self):
        self.client=ctypes.c_void_p();self.elements=[];self.initialized=False
        self.ole=ctypes.OleDLL('ole32')
        self.ole.CoInitializeEx.argtypes=[ctypes.c_void_p,ctypes.c_uint]
        self.ole.CoInitializeEx.restype=ctypes.c_long
        self.ole.CoUninitialize.argtypes=[]
        self.ole.CoUninitialize.restype=None
        result=self.ole.CoInitializeEx(None,0)
        self.initialized=result in (0,1)
        self.ole.CoCreateInstance.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p)]
        self.ole.CoCreateInstance.restype=ctypes.c_long
        clsid=(ctypes.c_byte*16).from_buffer_copy(uuid.UUID('ff48dba4-60ef-4201-aa87-54103eef594e').bytes_le)
        iid=(ctypes.c_byte*16).from_buffer_copy(uuid.UUID('30cbe57d-d9d0-452a-ab13-7ac5ac4825ee').bytes_le)
        result=self.ole.CoCreateInstance(clsid,None,1,iid,ctypes.byref(self.client))
        if result<0 or not self.client.value:
            self.close();raise RuntimeError('Không mở được bộ nhận diện ô nhập của Windows.') from None

    @staticmethod
    def call(pointer,index,result_type,arg_types,*args):
        table=ctypes.cast(pointer,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        method=ctypes.WINFUNCTYPE(result_type,ctypes.c_void_p,*arg_types)(table[index])
        return method(pointer,*args)

    def current(self):
        element=ctypes.c_void_p()
        result=self.call(self.client,8,ctypes.c_long,[ctypes.POINTER(ctypes.c_void_p)],ctypes.byref(element))
        if result<0 or not element.value:raise RuntimeError('Không xác định được ô HIS đang nhập. Đã dừng trước khi chuyển ô.')
        self.elements.append(element)
        return element

    def same(self,first,second):
        same=ctypes.c_int()
        result=self.call(self.client,3,ctypes.c_long,[ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_int)],first,second,ctypes.byref(same))
        if result<0:raise RuntimeError('Không so sánh được ô HIS đang nhập. Đã dừng trước khi chuyển ô.')
        return bool(same.value)

    def close(self):
        for element in self.elements:self.call(element,2,ctypes.c_ulong,[])
        self.elements=[]
        if self.client.value:
            self.call(self.client,2,ctypes.c_ulong,[]);self.client=ctypes.c_void_p()
        if self.initialized:self.ole.CoUninitialize();self.initialized=False
