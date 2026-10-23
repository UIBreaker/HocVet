"""Chọn vùng ảnh trên desktop, hỗ trợ màn hình có tọa độ âm."""
import base64
import ctypes
import io
import tkinter as tk

from PIL import ImageGrab, ImageTk
from ui_theme import VINTAGE_BG, VINTAGE_TEXT_HEAD, BTN_RED_TOP


def capture_region(root, on_complete):
    screenshot = ImageGrab.grab(all_screens=True)
    user32 = ctypes.windll.user32
    left, top = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
    overlay = tk.Toplevel(root)
    overlay.overrideredirect(True)
    overlay.attributes('-topmost', True)
    width, height = screenshot.size
    overlay.geometry(f'{width}x{height}+0+0')
    canvas = tk.Canvas(overlay, highlightthickness=0, cursor='crosshair')
    canvas.pack(fill=tk.BOTH, expand=True)
    photo = ImageTk.PhotoImage(screenshot)
    canvas.create_image(0, 0, image=photo, anchor='nw')
    canvas.create_rectangle(0, 0, width, 58, fill=VINTAGE_BG, outline='')
    canvas.create_text(24, 18, anchor='nw', text='HỌC VẸT  /  Kéo chọn riêng nút hoặc vùng cần chờ. Esc để hủy.',
                       fill=VINTAGE_TEXT_HEAD, font=('Segoe UI', 12, 'bold'))
    selection = None
    start = None

    def finish(result):
        overlay.grab_release()
        overlay.destroy()
        on_complete(result)

    def press(event):
        nonlocal selection, start
        start = (event.x, event.y)
        if selection is not None:
            canvas.delete(selection)
        selection = canvas.create_rectangle(*start, *start, outline=BTN_RED_TOP, width=2)

    def drag(event):
        if start:
            canvas.coords(selection, *start, event.x, event.y)

    def release(event):
        if not start:
            return
        x1, x2 = sorted((max(0, min(width, start[0])), max(0, min(width, event.x))))
        y1, y2 = sorted((max(0, min(height, start[1])), max(0, min(height, event.y))))
        if x2 <= x1 or y2 <= y1 or (x2-x1)*(y2-y1) > 2_000_000:
            return
        output = io.BytesIO()
        screenshot.crop((x1, y1, x2, y2)).save(output, format='PNG')
        finish((left + x1, top + y1, base64.b64encode(output.getvalue()).decode('ascii')))

    canvas.bind('<ButtonPress-1>', press)
    canvas.bind('<B1-Motion>', drag)
    canvas.bind('<ButtonRelease-1>', release)
    overlay.bind('<Escape>', lambda event: finish(None))
    overlay.update_idletasks()
    # Tk hiểu tọa độ âm là khoảng cách tới cạnh phải; đặt vị trí vật lý qua Win32.
    user32.SetWindowPos(ctypes.c_void_p(overlay.winfo_id()), None, left, top, width, height, 0x0040)
    overlay.grab_set()
    overlay.focus_force()
    overlay._capture_photo = photo
