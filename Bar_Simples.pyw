"""Entrada sem console usada pelo atalho do Windows."""
import sys
try:
    from salva_ai_v2.desktop import run_program
except Exception:
    import ctypes
    ctypes.windll.user32.MessageBoxW(None,'Extraia todo o pacote Bar Simples em uma pasta antes de abrir o programa.','Bar Simples',0x10)
    raise SystemExit(1)
sys.exit(run_program())
