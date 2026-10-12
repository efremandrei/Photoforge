"""Show the branded window before importing the reconstruction workspace."""
import json
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

ROOT = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]


def launch(check=False):
    started = time.monotonic()
    root = tk.Tk()
    root.withdraw()
    root.title('PhotoForge3D')
    settings = ROOT / 'jobs/settings.json'
    try:
        dark = json.loads(settings.read_text()).get('dark', True)
    except (OSError, ValueError):
        dark = True
    bg, fg = ('#101722', '#ecf4fa') if dark else ('#edf3fa', '#192433')
    root.configure(bg=bg)
    root.overrideredirect(True)
    root.geometry(f'520x360+{(root.winfo_screenwidth()-520)//2}+{(root.winfo_screenheight()-360)//2}')
    if (ROOT / 'assets/icon.ico').exists():
        root.iconbitmap(str(ROOT / 'assets/icon.ico'))
    logo = tk.PhotoImage(file=str(ROOT / 'assets/icon.png')).subsample(3)
    root.startup_logo = logo
    tk.Label(root, image=logo, bg=bg).pack(pady=(28, 2))
    tk.Label(root, text='PhotoForge3D', bg=bg, fg=fg, font=('Segoe UI', 26, 'bold')).pack()
    tk.Label(root, text='PHOTOS  →  GEOMETRY  →  PRINT', bg=bg, fg='#36c8b2', font=('Segoe UI', 10)).pack(pady=9)
    tk.Label(root, text='Preparing your workspace…', bg=bg, fg=fg, font=('Segoe UI', 11)).pack(pady=12)
    root.deiconify()
    root.update()
    observations = {'splash_shown': True, 'theme': 'dark' if dark else 'light'}
    if check:
        from PIL import ImageGrab
        folder = ROOT / 'artifacts'
        folder.mkdir(exist_ok=True)
        ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx()+520, root.winfo_rooty()+360)).save(folder/'windows-splash.png')
    loaded = queue.Queue()

    def load():
        try:
            from .desktop import Desktop
            loaded.put((Desktop, None))
        except Exception as error:
            loaded.put((None, error))

    def ready():
        try:
            desktop, error = loaded.get_nowait()
        except queue.Empty:
            root.after(20, ready)
            return
        if error:
            from tkinter import messagebox
            messagebox.showerror('PhotoForge3D startup', str(error), parent=root)
            root.destroy()
            return
        root.overrideredirect(False)
        app = desktop(root=root)
        root.update_idletasks()
        width, height = root.winfo_width(), root.winfo_height()
        root.geometry(f'{width}x{height}+{max(0,(root.winfo_screenwidth()-width)//2)}+{max(0,(root.winfo_screenheight()-height)//2)}')
        observations.update(workspace_ready=True, startup_seconds=round(time.monotonic()-started, 3), splash_removed=True)
        if check:
            (ROOT/'artifacts/startup-check.json').write_text(json.dumps(observations, indent=2))
            root.after(100, root.destroy)

    threading.Thread(target=load, daemon=True).start()
    root.after(0, ready)
    root.mainloop()
