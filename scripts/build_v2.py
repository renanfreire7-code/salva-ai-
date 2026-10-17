"""Gera pacote fonte Windows da reconstrução; não publica uma release."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def build_v2(output_dir):
    from salva_ai_v2 import __version__
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    target=output_dir/f"Salva_AI_novo_{__version__}.zip"
    files={}
    for path in sorted((ROOT/"salva_ai_v2").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix in (".py",".sql",".txt"):
            files[path.relative_to(ROOT).as_posix()]=path.read_bytes()
    files["INICIAR_V2.bat"]=(ROOT/"INICIAR_V2.bat").read_text(encoding="utf-8").replace("\r\n","\n").replace("\n","\r\n").encode("utf-8")
    files["LEIA-ME.md"]=(ROOT/"docs/manual-v2.md").read_bytes()
    files["VERSAO.txt"]=f"Salva AI novo {__version__}\nReconstrução em validação; teste com dados fictícios.\n".encode("utf-8")
    manifest={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
    files["MANIFEST-SHA256.json"]=json.dumps(manifest,indent=2,ensure_ascii=False).encode("utf-8")
    with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():
            archive.writestr(name,data)
    return target


if __name__=="__main__":
    import sys
    sys.path.insert(0,str(ROOT))
    print(build_v2(ROOT/"dist"))
