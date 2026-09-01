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


def entradas(cfg: dict) -> list[str]:
    """pastas.entrada aceita um caminho ou uma lista deles.

    Uma lista permite vigiar, além da pasta de entrada do escritório, a pasta
    que o Express usa — ver docs/14.
    """
    valor = cfg["pastas"]["entrada"]
    return [str(v) for v in (valor if isinstance(valor, list) else [valor]) if str(v).strip()]


def destinos(cfg: dict) -> list[dict]:
    """Destinos de arquivamento: servidor, Dropbox, o que mais houver.

    Sem a seção `destinos`, monta um único destino a partir de
    pastas.base_clientes — configuração antiga continua valendo.
    """
    lista = cfg.get("destinos")
    if not lista:
        return [{"nome": "SERVIDOR", "raiz": cfg["pastas"]["base_clientes"],
                 "habilitado": True, "principal": True}]
    resolvidos = []
    for item in lista:
        if not item.get("habilitado", True):
            continue
        resolvidos.append({"nome": item.get("nome", "DESTINO"),
                           "raiz": item["raiz"],
                           "habilitado": True,
                           "principal": bool(item.get("principal", False))})
    if not resolvidos:
        raise ValueError("nenhum destino de arquivamento habilitado no config")
    if not any(d["principal"] for d in resolvidos):
        resolvidos[0]["principal"] = True
    return resolvidos
