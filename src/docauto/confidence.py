"""Score de confiança e travas de segurança.

Duas camadas independentes:

1. SCORE (0-100): soma de evidências. Serve para priorizar a fila e medir a
   maturidade do fluxo.
2. TRAVAS: condições absolutas. Uma trava ativa manda o documento para
   validação manual mesmo com score 100. Score alto nunca compra o direito de
   arquivar com dúvida.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .normalize import competencia_plausivel

AUTOMATICO = "AUTOMATICO"
REVISAO = "ARQUIVADO_COM_REVISAO"
PENDENTE = "PENDENTE_VALIDACAO"


@dataclass
class Avaliacao:
    score: int = 0
    decisao: str = PENDENTE
    travas: list[str] = field(default_factory=list)
    detalhe: list[str] = field(default_factory=list)


def avaliar(ex, resolucao, classificacao, cfg, hoje: date | None = None) -> Avaliacao:
    hoje = hoje or date.today()
    p = cfg["confianca"]["pontos"]
    pen = cfg["confianca"]["penalidades"]
    faixas = cfg["confianca"]["faixas"]
    av = Avaliacao()
    pontos = 0.0

    # ---------------- empresa ----------------
    if resolucao.nivel == "CNPJ":
        pontos += p["cnpj_valido_cadastrado"]
        av.detalhe.append(f"empresa por CNPJ (+{p['cnpj_valido_cadastrado']})")
    elif resolucao.nivel == "RAZAO_SOCIAL":
        chave = ("razao_social_forte"
                 if resolucao.similaridade >= cfg["empresas"]["similaridade_forte"]
                 else "razao_social_fraca")
        pontos += p[chave]
        av.detalhe.append(f"empresa por razão social {resolucao.similaridade:.0%} (+{p[chave]})")
    elif resolucao.nivel == "NOME_FANTASIA":
        pontos += p["nome_fantasia"]
        av.detalhe.append(f"empresa por nome fantasia (+{p['nome_fantasia']})")
    elif resolucao.nivel == "PASTA_ORIGEM":
        pontos += p["pasta_origem"]
        av.detalhe.append(f"empresa por pasta de origem (+{p['pasta_origem']})")
    elif ex.cnpjs:
        pontos += p["cnpj_valido_nao_cadastrado"]

    # ---------------- tipo de documento ----------------
    if classificacao.tipo not in ("DOCUMENTO_DESCONHECIDO", "NECESSITA_VALIDACAO",
                                  "SEM_TEXTO", "RETENCAO_CONJUNTA"):
        relativo = getattr(classificacao, "score_relativo", classificacao.score)
        parcela = round(p["tipo_documento_max"] * relativo / 100)
        pontos += parcela
        av.detalhe.append(f"tipo {classificacao.tipo} score {relativo}% (+{parcela})")

    # ---------------- competência ----------------
    chave_comp = {"EXPLICITA": "competencia_explicita",
                  "APURACAO": "competencia_apuracao",
                  "INFERIDA": "competencia_inferida"}.get(ex.competencia.fonte)
    if chave_comp:
        pontos += p[chave_comp]
        av.detalhe.append(f"competência {ex.competencia.valor} "
                          f"({ex.competencia.fonte.lower()}) (+{p[chave_comp]})")

    # ---------------- coerência ----------------
    if ex.valor:
        pontos += p["valor_encontrado"]
    if ex.vencimento:
        pontos += p["vencimento_coerente"]

    # ---------------- qualidade do texto ----------------
    if ex.origem_texto == "OCR":
        pontos *= pen["texto_por_ocr"]
        av.detalhe.append(f"texto obtido por OCR (x{pen['texto_por_ocr']})")
    if len(ex.texto_norm) < 200:
        pontos *= pen["texto_curto"]
        av.detalhe.append(f"texto muito curto (x{pen['texto_curto']})")

    av.score = max(0, min(100, round(pontos)))

    # ---------------- travas ----------------
    if resolucao.empresa is None:
        av.travas.append(f"EMPRESA_NAO_IDENTIFICADA: {resolucao.motivo}")
    elif resolucao.nivel in ("RAZAO_SOCIAL", "NOME_FANTASIA") and \
            resolucao.similaridade < cfg["empresas"]["similaridade_forte"]:
        av.travas.append(f"EMPRESA_POR_SEMELHANCA_FRACA: {resolucao.motivo}")
    elif resolucao.nivel == "PASTA_ORIGEM":
        av.travas.append("EMPRESA_APENAS_PELA_PASTA: confirmar antes de arquivar")

    if classificacao.tipo == "SEM_TEXTO":
        av.travas.append("SEM_TEXTO: PDF provavelmente é imagem — habilitar OCR (Fase 2)")
    elif classificacao.tipo == "DOCUMENTO_DESCONHECIDO":
        av.travas.append("DOCUMENTO_DESCONHECIDO: nenhum template atingiu o score mínimo")
    elif classificacao.ambiguo:
        av.travas.append("CLASSIFICACAO_AMBIGUA: " + "; ".join(classificacao.motivos[-2:]))

    if not ex.competencia.valor:
        av.travas.append("COMPETENCIA_NAO_IDENTIFICADA")
    elif not competencia_plausivel(ex.competencia.valor, hoje,
                                   cfg["competencia"]["meses_passado_max"],
                                   cfg["competencia"]["meses_futuro_max"]):
        av.travas.append(f"COMPETENCIA_FORA_DA_JANELA: {ex.competencia.valor}")
    elif ex.competencia.fonte == "INFERIDA":
        av.travas.append("COMPETENCIA_INFERIDA: nenhum rótulo explícito no documento")

    if classificacao.tipo == "RETENCAO_CONJUNTA":
        av.travas.append("RETENCAO_CONJUNTA: guia cobre mais de um tributo")

    faltando = [c for c in getattr(classificacao, "campos_faltando", [])]
    if faltando:
        av.travas.append(f"CAMPOS_OBRIGATORIOS_AUSENTES: {', '.join(faltando)}")

    if av.travas:
        av.decisao = PENDENTE
    elif av.score >= faixas["automatico"]:
        av.decisao = AUTOMATICO
    elif av.score >= faixas["revisao"]:
        av.decisao = REVISAO
    else:
        av.decisao = PENDENTE
        av.travas.append(f"SCORE_BAIXO: {av.score} < {faixas['revisao']}")
    return av
