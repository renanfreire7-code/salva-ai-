import argparse
from pathlib import Path
from .bootstrap import build_application


def main():
    parser = argparse.ArgumentParser(description="Salva AI — PDV offline")
    parser.add_argument("--data-dir", type=Path, help="Diretório exclusivo dos dados desta instalação")
    args = parser.parse_args()
    app = build_application(args.data_dir)
    try:
        app.run()
    finally:
        app.close()


if __name__ == "__main__":
    main()
