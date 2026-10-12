import json
import math
import shutil
import socket
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import numpy as np
import uvicorn
from .engine import Jobs, ROOT
from .mesh import prepare, preview
from .server import create_app, pairing_token


GUIDE = '''1. Keep the object stationary and walk the camera around it. Avoid a turntable unless you mask the background.
2. Take 30–80 sharp photos with 70–80% overlap in 2–3 rings: level, above, and low down. Capture every surface you need.
3. Use diffuse light. Matte, textured surfaces work best; shiny, transparent, plain and moving objects often fail.
4. Import the photos. Processing can take minutes to hours on the CPU.
5. Rotate the preview and crop away the table/background. Enter the desired longest dimension in millimetres.
6. If there are holes, retake missing angles. Seal gaps is optional and can thicken/change the reconstructed geometry.
7. Inspect the STL in a slicer; choose orientation, supports, wall thickness and printer settings before printing.
Photos cannot measure an absolute size on their own. The size field scales the finished model; it is not a calibration guarantee.'''


class Desktop:
    def __init__(self, root=None):
        self.root = root if root is not None else tk.Tk()
        self.root.title('PhotoForge3D · photos to printable geometry')
        if (ROOT/'assets/icon.ico').exists():
            self.root.iconbitmap(str(ROOT/'assets/icon.ico'))
        self.root.geometry('1160x780')
        self.jobs = Jobs()
        self.job_id = None
        self.triangles = None
        self.yaw, self.pitch, self.zoom = .6, -.3, 1.0
        self.server = None
        settings = ROOT / 'jobs/settings.json'
        self.dark = json.loads(settings.read_text()).get('dark', True) if settings.exists() else True
        self.build()
        self.root.after(1200, self.poll)
        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def build(self):
        for w in self.root.winfo_children():
            w.destroy()
        bg, fg, panel = ('#101722', '#ecf4fa', '#1c2838') if self.dark else ('#edf3fa', '#192433', '#ffffff')
        self.bg, self.fg, self.panel = bg, fg, panel
        self.root.configure(bg=bg)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background=bg, foreground=fg, fieldbackground=panel, font=('Segoe UI', 10))
        style.configure('TButton', padding=9, background=panel)
        style.configure('TCheckbutton', background=panel)
        style.configure('Horizontal.TProgressbar', background='#36c8b2')
        top = tk.Frame(self.root, bg=bg)
        top.pack(fill='x', padx=24, pady=(20, 12))
        tk.Label(top, text='◈  PhotoForge3D', bg=bg, fg=fg, font=('Segoe UI', 23, 'bold')).pack(side='left')
        ttk.Button(top, text='☀ / ☾', command=self.theme).pack(side='right', padx=4)
        ttk.Button(top, text='About', command=self.about).pack(side='right', padx=4)
        ttk.Button(top, text='Photo guide', command=lambda: messagebox.showinfo('Capture guide', GUIDE)).pack(side='right', padx=4)
        body = tk.Frame(self.root, bg=bg)
        body.pack(fill='both', expand=True, padx=24)
        side = tk.Frame(body, bg=panel, width=325)
        side.pack(side='left', fill='y', padx=(0, 16))
        side.pack_propagate(False)
        tk.Label(side, text='01   CAPTURE & RECONSTRUCT', bg=panel, fg='#36c8b2', font=('Segoe UI', 10, 'bold')).pack(anchor='w', padx=14, pady=(15, 8))
        ttk.Button(side, text='Import photos →', command=self.import_photos).pack(fill='x', padx=14, pady=5)
        ttk.Button(side, text='Cancel selected scan', command=self.cancel).pack(fill='x', padx=14, pady=5)
        self.scans = tk.Listbox(side, bg=bg, fg=fg, selectbackground='#277c79', borderwidth=0, height=7, exportselection=False)
        self.scans.pack(fill='x', padx=14, pady=8)
        self.scans.bind('<<ListboxSelect>>', self.select)
        self.ids = []
        self.reload_scans()
        tk.Label(side, text='02   CROP & PRINT SIZE', bg=panel, fg='#36c8b2', font=('Segoe UI', 10, 'bold')).pack(anchor='w', padx=14, pady=(12, 8))
        tk.Label(side, text='Crop ranges in model axes (0–100%)', bg=panel, fg=fg).pack(anchor='w', padx=14)
        self.crop_entries = []
        for axis in 'XYZ':
            row = tk.Frame(side, bg=panel)
            row.pack(fill='x', padx=14, pady=3)
            tk.Label(row, text=axis, bg=panel, fg=fg, width=3).pack(side='left')
            a, b = ttk.Entry(row, width=10), ttk.Entry(row, width=10)
            a.insert(0, '0'); b.insert(0, '100')
            a.pack(side='left', padx=3); b.pack(side='left', padx=3)
            self.crop_entries.append((a,b))
        tk.Label(side, text='Longest dimension (mm)', bg=panel, fg=fg).pack(anchor='w', padx=14, pady=(8, 2))
        self.size = ttk.Entry(side)
        self.size.insert(0, '100')
        self.size.pack(fill='x', padx=14)
        self.seal = tk.BooleanVar(value=False)
        ttk.Checkbutton(side, text='Seal gaps (may change geometry)', variable=self.seal).pack(anchor='w', padx=14, pady=10)
        ttk.Button(side, text='Prepare & save STL →', command=self.export).pack(fill='x', padx=14, pady=5)
        ttk.Button(side, text='Show processing folder', command=self.folder).pack(fill='x', padx=14, pady=5)
        ttk.Button(side, text='Connect Android phone', command=self.pair).pack(fill='x', padx=14, pady=(10, 5))
        center = tk.Frame(body, bg=bg)
        center.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(center, bg=panel, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda e:self.draw())
        self.canvas.bind('<ButtonPress-1>', lambda e:setattr(self, 'drag', (e.x,e.y)))
        self.canvas.bind('<B1-Motion>', self.rotate)
        self.canvas.bind('<MouseWheel>', self.wheel)
        tk.Label(center, text='Drag to orbit • scroll to zoom • reconstructed axes shown below', bg=bg, fg=fg).pack(pady=8)
        self.status = tk.Label(self.root, text='Import 30–80 overlapping photos to begin. All processing stays on this PC.', bg=bg, fg=fg, anchor='w', wraplength=1090)
        self.status.pack(fill='x', padx=24, pady=(8, 4))
        self.progress = ttk.Progressbar(self.root, maximum=100)
        self.progress.pack(fill='x', padx=24, pady=(4, 18))
        self.draw()

    def theme(self):
        self.dark = not self.dark
        (ROOT / 'jobs/settings.json').write_text(json.dumps({'dark':self.dark}))
        self.build()

    def about(self):
        messagebox.showinfo('About PhotoForge3D', 'PhotoForge3D 1.1.0 · build 2\nAndrei Efremuahkin\nandrei.efr@gmail.com\nhttps://github.com/efremandrei/Photoforge\nCOLMAP (BSD) + OpenMVS (AGPL-3.0)\nLocal photogrammetry and verified STL export.')

    def reload_scans(self):
        jobs = sorted([json.loads(p.read_text()) for p in self.jobs.base.glob('*/job.json')], key=lambda d:d['created'], reverse=True)
        self.ids = [d['id'] for d in jobs]
        self.scans.delete(0, 'end')
        for d in jobs:self.scans.insert('end', d['name'])

    def import_photos(self):
        paths = filedialog.askopenfilenames(title='Choose distinct overlapping photos', filetypes=[('Photos', '*.jpg *.jpeg *.png *.webp'), ('All files', '*.*')])
        if not paths:return
        self.status.configure(text='Checking and importing photos…')
        def work():
            try:
                job = self.jobs.create(paths, Path(paths[0]).parent.name)
                self.root.after(0, lambda:self.imported(job))
            except Exception as e:self.error(e)
        threading.Thread(target=work, daemon=True).start()

    def imported(self, job):
        self.job_id = job['id']; self.triangles = None; self.reload_scans(); self.draw()

    def select(self, event):
        s = self.scans.curselection()
        if not s:return
        self.job_id = self.ids[s[0]]
        self.triangles = None
        self.draw()
        self.poll(schedule=False)

    def poll(self, schedule=True):
        try:
            if self.job_id:
                d = self.jobs.get(self.job_id)
                self.status.configure(text=f"{d['name']} · {d['message']}")
                self.progress['value'] = d['progress']
                if d['status']=='complete' and self.triangles is None:
                    self.triangles = np.array(preview(self.jobs.path(self.job_id)/'surface.ply')['triangles'])
                    self.draw()
        except Exception as e:self.status.configure(text=str(e))
        if schedule:self.root.after(1200, self.poll)

    def rotate(self, event):
        x,y = self.drag
        self.yaw += (event.x-x)*.01; self.pitch += (event.y-y)*.01
        self.drag = event.x,event.y
        self.draw()

    def wheel(self, event):
        self.zoom = min(5, max(.2, self.zoom*(1.12 if event.delta>0 else .89))); self.draw()

    def draw(self):
        self.canvas.delete('all')
        w,h = max(1,self.canvas.winfo_width()), max(1,self.canvas.winfo_height())
        if self.triangles is None:
            self.canvas.create_text(w/2,h/2,text='Your object, in three dimensions.\n\nImport photos to reconstruct a real surface.',fill=self.fg,font=('Segoe UI',17),justify='center')
            return
        cy,sy,cp,sp = math.cos(self.yaw),math.sin(self.yaw),math.cos(self.pitch),math.sin(self.pitch)
        rotation = np.array([[cy,0,sy],[sy*sp,cp,-cy*sp],[-sy*cp,sp,cy*cp]])
        tri = self.triangles @ rotation.T
        scale = min(w,h)*.85*self.zoom
        projected = tri[:,:,:2]*scale + [w/2,h/2]
        for i in np.argsort(tri[:,:,2].mean(axis=1)):
            self.canvas.create_polygon(*projected[i].flatten(),fill='#258f89',outline='#50c4b0',width=.35)
        origin = np.array([65,h-65])
        for i,(label,color) in enumerate(zip('XYZ',['#f68a86','#80dca9','#83b8ff'])):
            dest = origin+rotation[:2,i]*45
            self.canvas.create_line(*origin,*dest,fill=color,width=2)
            self.canvas.create_text(*dest,text=label,fill=color,anchor='s')

    def cancel(self):
        if self.job_id and self.jobs.get(self.job_id)['status'] in ('queued','running'):self.jobs.cancel(self.job_id)

    def export(self):
        if not self.job_id or self.jobs.get(self.job_id)['status']!='complete':
            messagebox.showinfo('Surface needed', 'Select a completed scan first.');return
        target = filedialog.asksaveasfilename(defaultextension='.stl', initialfile='PhotoForge3D-model.stl', filetypes=[('STL model','*.stl')])
        if not target:return
        try:
            crop = [[float(a.get())/100,float(b.get())/100] for a,b in self.crop_entries]
            size = float(self.size.get()); seal = self.seal.get(); job_id = self.job_id
        except ValueError:self.error('Enter numeric size and crop values.');return
        self.status.configure(text='Preparing and verifying STL…')
        def work():
            try:
                p = self.jobs.path(job_id)
                report = prepare(p/'surface.ply',p/'model.stl',size,crop,seal)
                shutil.copy2(p/'model.stl',target)
                self.jobs.update(job_id, export=report)
                detail = f"Saved: {target}\nClosed solid: yes\nDimensions (mm): " + ' × '.join(f'{x:.2f}' for x in report['dimensions']) + '\n'+report['warning']
                self.root.after(0,lambda:messagebox.showinfo('STL verified',detail))
            except Exception as e:self.error(e)
        threading.Thread(target=work,daemon=True).start()

    def error(self, error):
        text = str(error)
        self.root.after(0,lambda:messagebox.showerror('PhotoForge3D',text))

    def folder(self):
        import os
        os.startfile(str(self.jobs.path(self.job_id) if self.job_id else self.jobs.base))

    def pair(self):
        token = pairing_token()
        if self.server is None:
            self.server = uvicorn.Server(uvicorn.Config(create_app(self.jobs,token), host='0.0.0.0', port=8765, log_level='warning', log_config=None, access_log=False))
            threading.Thread(target=self.server.run,daemon=True).start()
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
                s.connect(('192.0.2.1',1)); ip=s.getsockname()[0]
        except OSError:ip=socket.gethostbyname(socket.gethostname())
        messagebox.showinfo('Pair Android phone',f'Keep this PC app open. Use the same trusted Wi-Fi.\n\nPC address: http://{ip}:8765\nPairing code: {token}\n\nIn the Android app, enter both values and tap Connect.\nIf Windows asks, allow access on private networks.\nLocal HTTP is unencrypted; use a trusted home network.')

    def close(self):
        active=[j for j in self.ids if self.jobs.get(j)['status'] in ('queued','running')]
        if active and not messagebox.askyesno('Processing in progress','Closing cancels active scans. Close now?'):return
        for job_id in active:self.jobs.cancel(job_id)
        if self.server:self.server.should_exit=True
        self.root.destroy()

    def run(self):self.root.mainloop()

