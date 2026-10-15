"""Build app branding from its shared vector geometry."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('brand_assets.py')),run_name='__main__')
