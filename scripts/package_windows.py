from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
root=Path(__file__).resolve().parents[1]
base=root/'dist/PhotoForge3D-PC'
archive=root/'artifacts/PhotoForge3D-PC-v1.1.0-build-2-windows-x64.zip'
with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=6) as z:
    for p in base.rglob('*'):
        rel=p.relative_to(base)
        if not p.is_file() or rel.parts[0] in ('jobs','artifacts') or p.name=='.pairing-token':continue
        if p.suffix in ('.log','.cfg') or p.name.lower().endswith('_test.exe') or p.name=='RUN_TESTS.bat':continue
        z.write(p,Path('PhotoForge3D-PC')/rel)
with ZipFile(archive) as z:
    assert z.testzip() is None
    for needed in ['PhotoForge3D-PC/PhotoForge3D-PC.exe','PhotoForge3D-PC/tools/colmap/bin/colmap.exe','PhotoForge3D-PC/tools/openmvs/vc17/x64/Release/DensifyPointCloud.exe']:
        assert needed in z.namelist()
print(archive.name,archive.stat().st_size)
