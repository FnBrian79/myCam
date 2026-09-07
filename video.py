import os
import glob
import subprocess
from PIL import Image

def compile_frames_to_animation(event_folder, output_format="gif", fps=10):
    """
    Compiles PNG frames in an event folder into an animated GIF or MP4.
    Tries ffmpeg first for optimal H.264 compression; falls back to pure PIL for zero-dependency GIF.
    """
    if not os.path.exists(event_folder):
        print(f"[video] Folder does not exist: {event_folder}")
        return None
        
    frames = sorted(glob.glob(os.path.join(event_folder, "frame_*.png")))
    if not frames:
        print(f"[video] No frame PNGs found in: {event_folder}")
        return None
        
    print(f"[video] Compiling {len(frames)} frames from {event_folder}...")
    
    # 1. Try ffmpeg for MP4 encoding
    mp4_path = os.path.join(event_folder, "recording.mp4")
    try:
        cmd = [
            "ffmpeg", "-y", "-framerate", str(fps),
            "-i", os.path.join(event_folder, "frame_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            mp4_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0 and os.path.exists(mp4_path):
            print(f"[video] Successfully created MP4 clip: {mp4_path}")
            return mp4_path
    except Exception:
        pass
        
    # 2. Native PIL Animated GIF Fallback (Zero external dependencies)
    anim_filename = f"clip.{output_format.lower()}"
    anim_path = os.path.join(event_folder, anim_filename)
    
    try:
        images = [Image.open(f) for f in frames]
        duration_ms = int(1000 / max(1, fps))
        
        images[0].save(
            anim_path,
            save_all=True,
            append_images=images[1:],
            optimize=True,
            duration=duration_ms,
            loop=0
        )
        print(f"[video] Successfully compiled animation: {anim_path}")
        return anim_path
    except Exception as e:
        print(f"[video ERROR] Failed to compile animation: {e}")
        return None
