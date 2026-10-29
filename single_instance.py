"""Một phiên Học Vẹt trong mỗi phiên đăng nhập Windows, kể cả chạy từ thư mục khác."""
import ctypes
from ctypes import wintypes


class SingleInstance:
    def __init__(self,name='HocVet.Desktop'):
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype=wintypes.HANDLE
        self.kernel.CreateEventW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.BOOL,wintypes.LPCWSTR]
        self.kernel.CreateEventW.restype=wintypes.HANDLE
        for method in ('CloseHandle','SetEvent'):
            getattr(self.kernel,method).argtypes=[wintypes.HANDLE]
        self.kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        self.mutex=self.kernel.CreateMutexW(None,False,'Local\\'+name+'.Instance')
        if not self.mutex:raise ctypes.WinError(ctypes.get_last_error())
        self.primary=ctypes.get_last_error()!=183
        self.event=self.kernel.CreateEventW(None,False,False,'Local\\'+name+'.Show')
        if not self.event:
            error=ctypes.WinError(ctypes.get_last_error());self.kernel.CloseHandle(self.mutex);raise error
        if not self.primary:self.kernel.SetEvent(self.event)

    def requested(self):
        return self.kernel.WaitForSingleObject(self.event,0)==0

    def close(self):
        for name in ('event','mutex'):
            handle=getattr(self,name,None)
            if handle:self.kernel.CloseHandle(handle);setattr(self,name,None)
