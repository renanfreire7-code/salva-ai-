import sys
from pathlib import Path

# O aplicativo é distribuído como uma pasta de scripts soltos (sem pacote),
# então os testes importam os módulos diretamente de salva_ai_headshop/.
APP_DIR = Path(__file__).resolve().parent.parent / 'salva_ai_headshop'
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
