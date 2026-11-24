"""Lê a configuração do projeto: .env (ou .env.example) na raiz, sobrescrito por variáveis de ambiente."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _ler(arquivo):
    valores = {}
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                valores[k.strip()] = v.strip().strip('"').strip("'")
    return valores


def carregar():
    cfg = _ler(ROOT / ".env.example")
    cfg.update(_ler(ROOT / ".env"))
    cfg.update({k: v for k, v in os.environ.items() if k in cfg})
    return cfg


CFG = carregar()
