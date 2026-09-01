"""Carregamento da configuração."""
from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]


def carregar_config(caminho: str | Path | None = None) -> dict:
    if caminho is None:
        candidatos = [RAIZ / "config" / "config.yaml", RAIZ / "config" / "config.example.yaml"]
        caminho = next(p for p in candidatos if p.exists())
    cfg = yaml.safe_load(Path(caminho).read_text(encoding="utf-8")) or {}
    cfg["_arquivo"] = str(caminho)
    cfg.setdefault("_raiz", str(RAIZ))
    return cfg


def caminho_projeto(cfg: dict, valor: str) -> str:
    """Resolve caminhos relativos em relação à raiz do projeto."""
    p = Path(valor)
    return str(p if p.is_absolute() else Path(cfg["_raiz"]) / p)
