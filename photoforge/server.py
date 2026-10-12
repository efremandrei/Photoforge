import secrets
import tempfile
import threading
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from .engine import Jobs, ROOT
from .mesh import prepare, preview
from . import __version__, BUILD


class ExportOptions(BaseModel):
    longest_mm: float = Field(default=100, ge=1, le=2000, allow_inf_nan=False)
    crop: list[list[float]] | None = None
    solidify: bool = False


def pairing_token():
    path = ROOT / '.pairing-token'
    if not path.exists():
        path.write_text(secrets.token_urlsafe(24), encoding='utf-8')
    return path.read_text('utf-8').strip()


def create_app(jobs=None, token=None):
    jobs = jobs or Jobs()
    token = token or pairing_token()
    app = FastAPI(title='PhotoForge3D PC processor', docs_url=None, redoc_url=None, openapi_url=None)
    export_lock = threading.Lock()

    @app.middleware('http')
    async def authenticate(request, call_next):
        if request.url.path != '/health' and not secrets.compare_digest(request.headers.get('X-Pairing-Token', ''), token):
            return JSONResponse({'detail': 'Pairing code is missing or incorrect.'}, status_code=401)
        return await call_next(request)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=400)

    @app.get('/health')
    def health():
        return {'app': 'PhotoForge3D', 'version': __version__, 'build': BUILD}

    @app.get('/jobs')
    def listing():
        return sorted([jobs.get(p.parent.name) for p in jobs.base.glob('*/job.json')], key=lambda j: j['created'], reverse=True)

    @app.post('/jobs')
    async def new(images: list[UploadFile] = File(...), name: str = Form('My object')):
        if not 8 <= len(images) <= 240:
            raise ValueError('Choose 8–240 distinct photos. Aim for 30–80 photos around all sides.')
        with tempfile.TemporaryDirectory(prefix='photoforge-') as tmp:
            paths = []
            total = 0
            for i, upload in enumerate(images):
                target = Path(tmp) / f'{i}.photo'
                size = 0
                with target.open('wb') as out:
                    while chunk := await upload.read(1_048_576):
                        size += len(chunk)
                        total += len(chunk)
                        if size > 20_000_000 or total > 500_000_000:
                            raise ValueError('Photo set is too large (20 MB per photo, 500 MB total).')
                        out.write(chunk)
                paths.append(target)
            try:
                return jobs.create(paths, name)
            except (OSError, ImageError) as ex:
                raise ValueError('One of the files could not be read as a photo.') from ex

    @app.get('/jobs/{job_id}')
    def status(job_id: str):
        return jobs.get(job_id)

    @app.post('/jobs/{job_id}/cancel')
    def cancel(job_id: str):
        jobs.cancel(job_id)
        return jobs.get(job_id)

    @app.get('/jobs/{job_id}/preview')
    def mesh_preview(job_id: str):
        if jobs.get(job_id)['status'] != 'complete':
            raise HTTPException(409, 'Surface is not ready yet.')
        return preview(jobs.path(job_id) / 'surface.ply')

    @app.post('/jobs/{job_id}/export')
    def export(job_id: str, options: ExportOptions):
        if jobs.get(job_id)['status'] != 'complete':
            raise HTTPException(409, 'Surface is not ready yet.')
        with export_lock:
            path = jobs.path(job_id)
            report = prepare(path / 'surface.ply', path / 'model.stl', options.longest_mm, options.crop, options.solidify)
            jobs.update(job_id, export=report)
            return report

    @app.get('/jobs/{job_id}/model.stl')
    def download(job_id: str):
        p = jobs.path(job_id)
        if not (p / 'model.stl').exists():
            raise HTTPException(409, 'Prepare the STL before downloading it.')
        return FileResponse(p / 'model.stl', media_type='model/stl', filename='PhotoForge3D-model.stl')
    return app


# Pillow decompression failures inherit from Exception, not OSError.
from PIL.Image import DecompressionBombError as ImageError
