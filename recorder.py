import os
import time
from datetime import datetime
from PIL import Image, ImageGrab
from storage import get_storage_dir, log_event

def grab_screen_gdi():
    """Windows native GDI screen capture - ultra fast & low overhead."""
    import ctypes
    from ctypes import windll, wintypes
    
    user32 = windll.user32
    gdi32 = windll.gdi32
    
    width = user32.GetSystemMetrics(78) or user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(79) or user32.GetSystemMetrics(1)
    x = user32.GetSystemMetrics(76)
    y = user32.GetSystemMetrics(77)
    
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid screen metrics: {width}x{height}")
        
    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
    
    gdi32.SelectObject(hdc_mem, hbmp)
    gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, x, y, 0x00CC0020)
    
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ('biSize', wintypes.DWORD),
            ('biWidth', wintypes.LONG),
            ('biHeight', wintypes.LONG),
            ('biPlanes', wintypes.WORD),
            ('biBitCount', wintypes.WORD),
            ('biCompression', wintypes.DWORD),
            ('biSizeImage', wintypes.DWORD),
            ('biXPelsPerMeter', wintypes.LONG),
            ('biYPelsPerMeter', wintypes.LONG),
            ('biClrUsed', wintypes.DWORD),
            ('biClrImportant', wintypes.DWORD)
        ]

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = width
    bmi.biHeight = -height
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0

    buffer = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(hdc_mem, hbmp, 0, height, buffer, ctypes.byref(bmi), 0)
    
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)
    
    img = Image.frombytes('RGBA', (width, height), buffer.raw, 'raw', 'BGRA')
    return img.convert('RGB')

def grab_screen():
    """Captures screen using Windows GDI first, falling back to PIL.ImageGrab on Linux/macOS."""
    if os.name == 'nt':
        try:
            return grab_screen_gdi()
        except Exception:
            pass
    return ImageGrab.grab()

def capture_screenshot(config, title="Manual Trigger"):
    storage_dir = get_storage_dir(config)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    filename = f"snap_{timestamp}.png"
    filepath = os.path.join(storage_dir, filename)
    
    try:
        img = grab_screen()
        img.save(filepath, "PNG")
        print(f"[myCam] Instant snapshot saved -> {filepath}")
        return filepath
    except Exception as e:
        print(f"[myCam ERROR] Snapshot failed: {e}")
        return None

def capture_sequence(config, duration_sec=5, fps=10, title="Motion Trigger"):
    storage_dir = get_storage_dir(config)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    event_folder = os.path.join(storage_dir, f"event_{timestamp}")
    os.makedirs(event_folder, exist_ok=True)
    
    total_frames = int(duration_sec * fps)
    interval = 1.0 / max(1, fps)
    captured_files = []
    
    print(f"[myCam] Recording sequence: {duration_sec}s @ {fps}fps ({total_frames} frames)...")
    
    start_time = time.time()
    for i in range(total_frames):
        frame_start = time.time()
        try:
            img = grab_screen()
            filename = f"frame_{i:04d}.png"
            filepath = os.path.join(event_folder, filename)
            img.save(filepath, "PNG")
            captured_files.append(filepath)
        except Exception as e:
            print(f"[myCam ERROR] Frame {i} capture failed: {e}")
            
        elapsed = time.time() - frame_start
        to_sleep = interval - elapsed
        if to_sleep > 0:
            time.sleep(to_sleep)
            
    print(f"[myCam] Sequence finished. Captured {len(captured_files)} frames in {time.time() - start_time:.2f}s")
    log_event(config, "gdi_sequence_capture", title, captured_files)
    
    # Auto-compile into animation or MP4
    try:
        from video import compile_frames_to_animation
        anim_path = compile_frames_to_animation(event_folder, output_format="gif", fps=fps)
        if anim_path:
            captured_files.append(anim_path)
    except Exception as e:
        print(f"[myCam Video Warning] Auto-compile failed: {e}")
        
    return captured_files
