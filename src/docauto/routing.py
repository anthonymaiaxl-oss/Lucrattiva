"""Montagem do caminho de destino e do nome padronizado do arquivo."""
from __future__ import annotations

import re
import unicodedata
from pathlib import PurePath, PureWindowsPath

from .normalize import MES_EXTENSO

PROIBIDOS_WINDOWS = r'<>:"/\|?*'
RESERVADOS_WINDOWS = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitizar(nome: str, limite: int = 60) -> str:
    """Deixa o texto seguro para nome de pasta/arquivo no Windows."""
    nome = unicodedata.normalize("NFKD", nome or "")
    nome = "".join(c for c in nome if not unicodedata.combining(c))
    nome = "".join("-" if c in PROIBIDOS_WINDOWS else c for c in nome)
    nome = "".join(c for c in nome if c.isprintable() and ord(c) > 31)
    nome = re.sub(r"\s+", " ", nome).strip(" .")
    nome = re.sub(r"-{2,}", "-", nome)
    if nome.upper().split(".")[0] in RESERVADOS_WINDOWS:
        nome = f"_{nome}"
    return nome[:limite].strip(" .-") or "SEM_NOME"


def slug(nome: str, limite: int = 24) -> str:
    """Versão curta e sem espaços para compor nome de arquivo."""
    base = sanitizar(nome, limite * 3).upper()
    base = re.sub(r"[^A-Z0-9]+", "-", base).strip("-")
    return base[:limite].strip("-") or "EMPRESA"


def pasta_empresa(empresa, base_clientes: str) -> str:
    """CAMINHO_BASE do cadastro tem prioridade; senão, base + 'ID - RAZAO'."""
    if empresa.caminho_base:
        return empresa.caminho_base.rstrip("/\\")
    return f"{base_clientes.rstrip('/')}/{sanitizar(empresa.pasta, 80)}"


def montar_caminho(empresa, classificacao, competencia: str, cfg: dict,
                   base_clientes: str, setor: str | None = None,
                   grupo: str | None = None) -> str:
    ano, mes = competencia[:4], competencia[5:7]
    partes = {
        "base_empresa": pasta_empresa(empresa, base_clientes),
        "id": empresa.id,
        "empresa": sanitizar(empresa.razao_social, 80),
        "setor": setor or "FISCAL",
        "ano": ano,
        "mes": mes,
        "mes_extenso": MES_EXTENSO.get(int(mes), mes),
        "competencia": f"{ano}-{mes}",
        "grupo": grupo or "GUIAS",
        "tipo": classificacao.tipo,
    }
    caminho = cfg["estrutura"]["caminho"].format(**partes)
    if cfg["estrutura"].get("subpasta_por_tributo"):
        caminho = f"{caminho}/{sanitizar(classificacao.tipo, 30)}"
    return re.sub(r"/{2,}", "/", caminho).rstrip("/")


def montar_nome(empresa, classificacao, competencia: str, extensao: str,
                cfg: dict, seq: int = 1) -> str:
    modelo = cfg["estrutura"]["nome_arquivo"]
    nome = modelo.format(
        competencia=competencia,
        tipo=sanitizar(classificacao.tipo, 20).replace(" ", "-"),
        subtipo=sanitizar(classificacao.subtipo or "", 24).replace(" ", "-"),
        empresa_curta=slug(empresa.curto),
        id=empresa.id,
        seq=f"{seq:02d}",
    )
    nome = re.sub(r"_{2,}", "_", nome).strip("_-")
    if seq > 1:
        nome = f"{nome}_{seq:02d}"
    return f"{sanitizar(nome, 70)}{extensao.lower()}"


def caminho_muito_longo(caminho: str, nome: str, limite: int = 240) -> bool:
    return len(str(PureWindowsPath(caminho) / nome)) > limite
