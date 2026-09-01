"""Classificação do tipo de documento por múltiplos critérios.

Nunca por nome de arquivo. A ordem de força das evidências é:
código de receita ancorado > termo principal do tributo > termos secundários.
Empate dentro da margem configurada => NECESSITA_VALIDACAO, nunca "chute".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .normalize import Extracao
from .templates import TabelaCodigos, Template

PONTOS_SECUNDARIA = 5
TETO_SECUNDARIAS = 15
PONTOS_CODIGO_COMPATIVEL = 30
PENALIDADE_CODIGO_DE_OUTRO = 35
PENALIDADE_ANTI_TERMO = 12
TETO_ANTI_TERMOS = 30
PENALIDADE_SUPRESSAO = 60
LIMIAR_SUPRESSAO = 50


@dataclass
class Candidato:
    tipo: str
    score: int
    maximo: int = 100
    motivos: list[str] = field(default_factory=list)

    @property
    def relativo(self) -> int:
        """Score em % do máximo que ESTE template consegue atingir.

        Sem isso, um DAS perfeito (que não tem código de receita para somar)
        nunca passaria de ~60 e cairia eternamente em revisão manual.
        """
        return round(100 * self.score / self.maximo) if self.maximo else 0


@dataclass
class Classificacao:
    tipo: str = "DOCUMENTO_DESCONHECIDO"
    subtipo: str | None = None
    score: int = 0
    score_relativo: int = 0
    ambiguo: bool = False
    candidatos: list[Candidato] = field(default_factory=list)
    motivos: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def template_id(self) -> str:
        return self.tipo


def _contem(texto_norm: str, termo: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(termo) +
                     r"(?![A-Za-z0-9])", texto_norm) is not None


def _pontuar(t: Template, ex: Extracao, tabela: TabelaCodigos) -> Candidato:
    motivos: list[str] = []
    score = 0

    melhor = 0
    for termo in t.principais:
        if termo.encontrado(ex.texto_norm, ex.texto_caixa) and termo.peso > melhor:
            melhor = termo.peso
            motivos.append(f"termo principal '{termo.termo}' (+{termo.peso})")
    score += melhor

    achadas = [s for s in t.secundarias if _contem(ex.texto_norm, s)]
    if achadas:
        bonus = min(len(achadas) * PONTOS_SECUNDARIA, TETO_SECUNDARIAS)
        score += bonus
        motivos.append(f"{len(achadas)} termo(s) secundário(s) (+{bonus})")

    for cod in ex.codigos_receita:
        tributo = tabela.tributo(cod)
        if tributo == t.id:
            score += PONTOS_CODIGO_COMPATIVEL
            motivos.append(f"código de receita {cod} = {t.id} (+{PONTOS_CODIGO_COMPATIVEL})")
        elif tributo and tributo != "RETENCAO_CONJUNTA":
            score -= PENALIDADE_CODIGO_DE_OUTRO
            motivos.append(f"código {cod} pertence a {tributo} (-{PENALIDADE_CODIGO_DE_OUTRO})")

    anti = [a for a in t.anti_termos if _contem(ex.texto_norm, a)]
    if anti:
        castigo = min(len(anti) * PENALIDADE_ANTI_TERMO, TETO_ANTI_TERMOS)
        score -= castigo
        motivos.append(f"termo(s) de outro tributo {anti} (-{castigo})")

    maximo = max((k.peso for k in t.principais), default=0) + TETO_SECUNDARIAS
    if any(v.get("tributo") == t.id for v in tabela.codigos.values()):
        maximo += PONTOS_CODIGO_COMPATIVEL
    return Candidato(tipo=t.id, score=max(0, min(100, score)),
                     maximo=max(maximo, 1), motivos=motivos)


def classificar(ex: Extracao, templates: dict[str, Template], tabela: TabelaCodigos,
                score_minimo: int = 35, margem: int = 15) -> Classificacao:
    if not ex.texto_norm.strip():
        return Classificacao(tipo="SEM_TEXTO", motivos=["nenhum texto extraído do arquivo"])

    candidatos = {t.id: _pontuar(t, ex, tabela) for t in templates.values()}

    # Documento composto (DAS) suprime os tributos que ele já engloba.
    for t in templates.values():
        if t.suprime and candidatos[t.id].score >= LIMIAR_SUPRESSAO:
            for alvo in t.suprime:
                if alvo in candidatos:
                    candidatos[alvo].score = max(0, candidatos[alvo].score - PENALIDADE_SUPRESSAO)
                    candidatos[alvo].motivos.append(
                        f"suprimido por {t.id} (documento composto, -{PENALIDADE_SUPRESSAO})")

    ordenados = sorted(candidatos.values(),
                       key=lambda c: (c.score, templates[c.tipo].precedencia), reverse=True)
    top = ordenados[0]
    segundo = ordenados[1] if len(ordenados) > 1 else Candidato("-", 0)

    cls = Classificacao(candidatos=ordenados[:4], score=top.score,
                        score_relativo=top.relativo, motivos=list(top.motivos))

    # Retenção conjunta (ex.: DARF 5952) é ambígua por natureza, não por dúvida.
    for cod in ex.codigos_receita:
        if tabela.tributo(cod) == "RETENCAO_CONJUNTA":
            cls.tipo = "RETENCAO_CONJUNTA"
            cls.subtipo = tabela.subtipo(cod)
            cls.ambiguo = True
            cls.motivos.append(f"código {cod}: guia cobre mais de um tributo")
            return cls

    if top.score < score_minimo:
        cls.tipo = "DOCUMENTO_DESCONHECIDO"
        cls.ambiguo = True
        cls.motivos.append(f"melhor score {top.score} abaixo do mínimo {score_minimo}")
        return cls

    if top.score - segundo.score < margem:
        cls.tipo = "NECESSITA_VALIDACAO"
        cls.ambiguo = True
        cls.motivos.append(
            f"empate entre {top.tipo} ({top.score}) e {segundo.tipo} ({segundo.score})")
        return cls

    cls.tipo = top.tipo

    codigos_do_tipo = [c for c in ex.codigos_receita if tabela.tributo(c) == top.tipo]
    if codigos_do_tipo:
        cls.subtipo = tabela.subtipo(codigos_do_tipo[0])
        if not tabela.conferida:
            cls.avisos.append("TABELA_CODIGOS_NAO_CONFERIDA")

    if templates[top.tipo].exige_subtipo and not cls.subtipo:
        cls.ambiguo = True
        cls.motivos.append(
            f"{top.tipo} exige subtipo e nenhum código de receita foi reconhecido")

    if ex.codigos_receita and not any(tabela.tributo(c) for c in ex.codigos_receita):
        cls.avisos.append("CODIGO_RECEITA_FORA_DA_TABELA")

    return cls
