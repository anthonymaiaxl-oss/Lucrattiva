"""Carregamento dos templates de documento e da tabela de códigos de receita."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TermoChave:
    termo: str
    peso: int = 30
    caixa_alta: bool = False

    def encontrado(self, texto_norm: str, texto_caixa: str) -> bool:
        alvo = texto_caixa if self.caixa_alta else texto_norm
        return re.search(r"(?<![A-Za-z0-9])" + re.escape(self.termo) +
                         r"(?![A-Za-z0-9])", alvo) is not None


@dataclass
class Template:
    id: str
    nome: str
    setor: str = "FISCAL"
    grupo: str = "GUIAS"
    precedencia: int = 50
    exige_subtipo: bool = False
    suprime: list[str] = field(default_factory=list)
    principais: list[TermoChave] = field(default_factory=list)
    secundarias: list[str] = field(default_factory=list)
    anti_termos: list[str] = field(default_factory=list)
    campos_obrigatorios: list[str] = field(default_factory=list)
    campos_opcionais: list[str] = field(default_factory=list)
    criterios_confiavel: str = ""
    criterios_validacao_manual: str = ""


def _termo(item) -> TermoChave:
    if isinstance(item, str):
        return TermoChave(termo=item)
    return TermoChave(termo=item["termo"], peso=int(item.get("peso", 30)),
                      caixa_alta=bool(item.get("caixa_alta", False)))


def carregar_templates(pasta: str | Path) -> dict[str, Template]:
    templates: dict[str, Template] = {}
    for arquivo in sorted(Path(pasta).glob("*.yaml")):
        d = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
        t = Template(
            id=d["id"],
            nome=d.get("nome", d["id"]),
            setor=d.get("setor", "FISCAL"),
            grupo=d.get("grupo", "GUIAS"),
            precedencia=int(d.get("precedencia", 50)),
            exige_subtipo=bool(d.get("exige_subtipo", False)),
            suprime=list(d.get("suprime", [])),
            principais=[_termo(i) for i in d.get("palavras_chave_principais", [])],
            secundarias=[str(i) for i in d.get("palavras_chave_secundarias", [])],
            anti_termos=[str(i) for i in d.get("anti_termos", [])],
            campos_obrigatorios=list(d.get("campos_obrigatorios", [])),
            campos_opcionais=list(d.get("campos_opcionais", [])),
            criterios_confiavel=d.get("criterios_confiavel", ""),
            criterios_validacao_manual=d.get("criterios_validacao_manual", ""),
        )
        templates[t.id] = t
    return templates


@dataclass
class TabelaCodigos:
    codigos: dict[str, dict]
    conferida: bool = False

    def tributo(self, codigo: str) -> str | None:
        item = self.codigos.get(codigo)
        return item.get("tributo") if item else None

    def subtipo(self, codigo: str) -> str | None:
        item = self.codigos.get(codigo)
        return item.get("subtipo") if item else None


def carregar_codigos(arquivo: str | Path) -> TabelaCodigos:
    d = yaml.safe_load(Path(arquivo).read_text(encoding="utf-8")) or {}
    meta = d.get("_meta", {}) or {}
    return TabelaCodigos(codigos=d.get("codigos", {}) or {},
                         conferida=str(meta.get("status", "")).upper() == "CONFERIDA")
