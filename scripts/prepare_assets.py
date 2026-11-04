"""Prepare immutable CDN files before deploying the Flask application."""
from pathlib import Path
import runpy
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    version = runpy.run_path(str(ROOT / 'app/assets.py'))['asset_version'](str(ROOT / 'static'))
    assets = ROOT / 'public/assets'
    if assets.exists():
        shutil.rmtree(assets)
    output = assets / version
    shutil.copytree(ROOT / 'static', output, ignore=shutil.ignore_patterns('uploads', '.DS_Store'))
    for png in output.rglob('*.png'):
        if png.with_suffix('.webp').exists():
            png.unlink()
    (ROOT / 'asset-version.txt').write_text(version + '\n')
    print(f'Prepared CDN assets: /assets/{version}/')


if __name__ == '__main__':
    main()
