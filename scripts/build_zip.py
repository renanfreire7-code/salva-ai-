"""Gera o zip de distribuição para Windows a partir da pasta salva_ai_headshop/.

Mesmo layout dos zips anteriores: uma pasta salva_ai_headshop/ com os scripts,
os .bat, os .txt e o xlsxwriter incluído. Caches do Python ficam de fora.

Uso: python3 scripts/build_zip.py   ->  dist/salva_ai_headshop_prototipo_<versão>.zip
"""
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / 'salva_ai_headshop'
EXCLUDED_DIRS = {'__pycache__'}
EXCLUDED_SUFFIXES = {'.pyc', '.sqlite3', '.sqlite3-shm', '.sqlite3-wal'}


def version():
    """Lê a versão de VERSAO.txt (ex.: '0.3.4-beta' -> '0_3_4_beta')."""
    match = re.search(r'(\d+\.\d+\.\d+(?:-\w+)?)', (APP / 'VERSAO.txt').read_text(encoding='utf-8'))
    if not match:
        sys.exit('Versão não encontrada em VERSAO.txt')
    return re.sub(r'[.-]', '_', match.group(1))


def entries():
    for path in sorted(APP.rglob('*')):
        rel = path.relative_to(APP)
        if EXCLUDED_DIRS.intersection(rel.parts) or path.suffix in EXCLUDED_SUFFIXES:
            continue
        yield path


def main():
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    target = dist / f'salva_ai_headshop_prototipo_{version()}.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('salva_ai_headshop/', '')
        for path in entries():
            zf.write(path, Path('salva_ai_headshop') / path.relative_to(APP))
    print(target)


if __name__ == '__main__':
    main()
