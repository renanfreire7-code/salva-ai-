"""Ponte executada ocultamente pelo Windows Script Host; não exige dependências extras."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
try:
    from salva_ai_v2.desktop import launch
except Exception:
    import ctypes
    ctypes.windll.user32.MessageBoxW(None,'Extraia todo o pacote Bar Simples. Nao mova a pasta scripts separadamente.','Bar Simples',0x10)
    raise SystemExit(42)

if __name__=='__main__':
    result=launch(ROOT,check_only=sys.argv[1:]==['--check'])
    raise SystemExit(0 if result==0 else 42)
