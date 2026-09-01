"""Cadastro central de empresas e resolução da empresa do documento.

Hierarquia de identificação (docs/06): CNPJ > razão social > nome fantasia >
pasta de origem. Sem identificação segura, o documento NÃO é arquivado na
pasta de nenhuma empresa.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from .normalize import normalizar, so_digitos

COLUNAS = [
    "ID_EMPRESA", "CODIGO_DOMINIO", "RAZAO_SOCIAL", "NOME_FANTASIA",
    "NOME_CURTO", "CNPJ", "REGIME_TRIBUTARIO", "CAMINHO_BASE",
    "SETOR_PADRAO", "ATIVA", "APELIDOS",
]


@dataclass
class Empresa:
    id: str
    razao_social: str
    cnpj: str                      # 14 dígitos
    nome_fantasia: str = ""
    nome_curto: str = ""
    codigo_dominio: str = ""
    regime: str = ""
    caminho_base: str = ""
    setor_padrao: str = "FISCAL"
    ativa: bool = True
    apelidos: list[str] = field(default_factory=list)

    @property
    def pasta(self) -> str:
        """Nome da pasta da empresa: 'ID - RAZAO SOCIAL' (estável e ordenável)."""
        return f"{self.id} - {self.razao_social}".strip()

    @property
    def curto(self) -> str:
        return (self.nome_curto or self.nome_fantasia or self.razao_social).upper()


@dataclass
class ResolucaoEmpresa:
    empresa: Empresa | None = None
    nivel: str = "NAO_IDENTIFICADA"   # CNPJ | RAZAO_SOCIAL | NOME_FANTASIA | PASTA_ORIGEM
    similaridade: float = 0.0
    motivo: str = ""
    sugestoes: list[str] = field(default_factory=list)


class Cadastro:
    def __init__(self, empresas: list[Empresa]):
        self.empresas = empresas
        self.por_cnpj = {e.cnpj: e for e in empresas if e.cnpj}

    @classmethod
    def carregar(cls, arquivo: str | Path) -> "Cadastro":
        caminho = Path(arquivo)
        bruto = caminho.read_text(encoding="utf-8-sig")
        delim = ";" if bruto.splitlines()[0].count(";") >= bruto.splitlines()[0].count(",") else ","
        empresas: list[Empresa] = []
        for linha in csv.DictReader(bruto.splitlines(), delimiter=delim):
            linha = { (k or "").strip().upper(): (v or "").strip() for k, v in linha.items() }
            if not linha.get("ID_EMPRESA"):
                continue
            empresas.append(Empresa(
                id=linha["ID_EMPRESA"],
                razao_social=linha.get("RAZAO_SOCIAL", ""),
                cnpj=so_digitos(linha.get("CNPJ", "")),
                nome_fantasia=linha.get("NOME_FANTASIA", ""),
                nome_curto=linha.get("NOME_CURTO", ""),
                codigo_dominio=linha.get("CODIGO_DOMINIO", ""),
                regime=linha.get("REGIME_TRIBUTARIO", ""),
                caminho_base=linha.get("CAMINHO_BASE", ""),
                setor_padrao=linha.get("SETOR_PADRAO", "FISCAL") or "FISCAL",
                ativa=linha.get("ATIVA", "SIM").upper() in ("SIM", "S", "1", "TRUE"),
                apelidos=[a.strip() for a in linha.get("APELIDOS", "").split("|") if a.strip()],
            ))
        return cls(empresas)

    def validar(self) -> list[str]:
        """Problemas que impedem operação segura. Rodar antes de ligar o fluxo."""
        from .normalize import cnpj_valido
        erros: list[str] = []
        vistos: dict[str, str] = {}
        for e in self.empresas:
            if not e.cnpj:
                erros.append(f"{e.id}: CNPJ vazio")
            elif not cnpj_valido(e.cnpj):
                erros.append(f"{e.id}: CNPJ inválido ({e.cnpj})")
            elif e.cnpj in vistos:
                erros.append(f"{e.id}: CNPJ duplicado com {vistos[e.cnpj]}")
            else:
                vistos[e.cnpj] = e.id
            if not e.razao_social:
                erros.append(f"{e.id}: razão social vazia")
        return erros

    # ------------------------------------------------------------------ #

    def _nomes(self, e: Empresa) -> list[str]:
        return [normalizar(n) for n in
                [e.razao_social, e.nome_fantasia, e.nome_curto, *e.apelidos] if n]

    def resolver(self, ex, pasta_origem: str = "", limiar_forte: float = 0.90,
                 limiar_fraco: float = 0.82) -> ResolucaoEmpresa:
        # Nível 1 — CNPJ (já validado por dígito verificador na extração).
        for cnpj in ex.cnpjs:
            empresa = self.por_cnpj.get(cnpj)
            if empresa:
                if not empresa.ativa:
                    return ResolucaoEmpresa(None, "NAO_IDENTIFICADA", 0.0,
                                            f"CNPJ {cnpj} pertence a empresa INATIVA ({empresa.id})")
                return ResolucaoEmpresa(empresa, "CNPJ", 1.0, f"CNPJ {cnpj} no cadastro")
        if ex.cnpjs:
            return ResolucaoEmpresa(
                None, "NAO_IDENTIFICADA", 0.0,
                f"CNPJ(s) válido(s) {ex.cnpjs} não encontrado(s) no cadastro")

        # Níveis 2 e 3 — razão social / nome fantasia, por similaridade.
        melhor, melhor_sim, melhor_nivel = None, 0.0, ""
        sugestoes: list[tuple[float, str]] = []
        for candidato in ex.razoes:
            alvo = normalizar(candidato)
            for e in self.empresas:
                if not e.ativa:
                    continue
                for i, nome in enumerate(self._nomes(e)):
                    sim = SequenceMatcher(None, alvo, nome).ratio()
                    if sim > melhor_sim:
                        melhor, melhor_sim = e, sim
                        melhor_nivel = "RAZAO_SOCIAL" if i == 0 else "NOME_FANTASIA"
                    if sim >= limiar_fraco:
                        sugestoes.append((sim, f"{e.id} - {e.razao_social}"))

        if melhor and melhor_sim >= limiar_forte:
            return ResolucaoEmpresa(melhor, melhor_nivel, melhor_sim,
                                    f"nome similar a '{melhor.razao_social}' ({melhor_sim:.0%})")
        if melhor and melhor_sim >= limiar_fraco:
            return ResolucaoEmpresa(
                melhor, melhor_nivel, melhor_sim,
                f"similaridade fraca com '{melhor.razao_social}' ({melhor_sim:.0%}) — confirmar",
                sugestoes=[s for _, s in sorted(sugestoes, reverse=True)[:3]])

        # Nível 4 — pasta de origem (documento colocado à mão na pasta da empresa).
        if pasta_origem:
            alvo = normalizar(pasta_origem)
            for e in self.empresas:
                if e.ativa and (normalizar(e.pasta) in alvo or
                                (e.nome_curto and normalizar(e.nome_curto) in alvo)):
                    return ResolucaoEmpresa(e, "PASTA_ORIGEM", 0.5,
                                            f"pasta de origem indica {e.id}")

        if getattr(ex, "cnpjs_invalidos", None):
            return ResolucaoEmpresa(
                None, "NAO_IDENTIFICADA", 0.0,
                f"CNPJ ilegível/inválido no documento ({ex.cnpjs_invalidos[0]}) "
                "— provável erro de leitura/OCR")
        return ResolucaoEmpresa(None, "NAO_IDENTIFICADA", melhor_sim,
                                "nenhum CNPJ ou nome reconhecido no cadastro",
                                sugestoes=[s for _, s in sorted(sugestoes, reverse=True)[:3]])
