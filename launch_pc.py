import sys

if __name__ == '__main__':
    if '--self-test' in sys.argv:
        from photoforge.desktop import Desktop
        import json
        import trimesh
        import numpy as np
        from photoforge.engine import ROOT, COLMAP, MVS, NO_WINDOW
        from photoforge.mesh import prepare, preview
        import subprocess
        path=ROOT/'artifacts'
        path.mkdir(exist_ok=True)
        try:
            raw=path/'self-test.ply'
            source=trimesh.creation.icosphere(subdivisions=4)
            source.update_faces(source.triangles_center[:,2]<.4)
            source.export(raw)
            report=prepare(raw,path/'self-test.stl',80,solidify=True,resolution=64)
            gui=Desktop()
            gui.triangles=np.array(preview(raw)['triangles'])
            gui.root.update();gui.draw();gui.root.update()
            import socket, threading, time, requests, uvicorn
            from photoforge.server import create_app
            listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(16)
            port=listener.getsockname()[1]
            backend=uvicorn.Server(uvicorn.Config(create_app(gui.jobs,'self-test-token'),log_config=None,access_log=False))
            thread=threading.Thread(target=lambda:backend.run(sockets=[listener]),daemon=True);thread.start()
            for _ in range(100):
                if backend.started:break
                time.sleep(.05)
            response=requests.get(f'http://127.0.0.1:{port}/jobs',headers={'X-Pairing-Token':'self-test-token'},timeout=5)
            response.raise_for_status()
            backend.should_exit=True;thread.join(timeout=5);listener.close()
            gui.root.destroy()
            for exe in [COLMAP,MVS/'DensifyPointCloud.exe',MVS/'ReconstructMesh.exe']:
                completed=subprocess.run([str(exe),'--help'],cwd=path,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=NO_WINDOW)
                if completed.returncode not in (0,1):raise RuntimeError(f'Engine failed to launch: {exe.name}')
            (path/'self-test.json').write_text(json.dumps(dict(status='pass',mesh=report),indent=2))
        except Exception as e:
            (path/'self-test.json').write_text(json.dumps(dict(status='fail',error=str(e))))
            raise
    else:
        from photoforge.startup import launch
        launch(check='--startup-check' in sys.argv)
