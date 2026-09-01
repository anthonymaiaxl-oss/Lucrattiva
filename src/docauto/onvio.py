"""Leitura de exportações do Onvio para conferir contra o que a automação sabe.

Ninguém precisa entregar senha do Onvio: basta exportar as listas que o próprio
sistema já gera (empresas e tarefas/obrigações) e apontar os arquivos aqui.
O que este módulo faz é o cruzamento — que é o trabalho de verdade:

  empresa no Onvio que falta no cadastro   -> documento vira pendência
  empresa no cadastro que falta no Onvio   -> Express nunca acha a tarefa
  CNPJ divergente entre os dois            -> documento na empresa errada
  obrigação sem template correspondente    -> documento sem classificação
  template sem obrigação no Onvio          -> Express sempre devolve "não encontrada"

As colunas são reconhecidas pelo cabeçalho, em qualquer ordem e com nomes
variados — exportação de sistema muda de versão para versão.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from .classify import _contem
from .normalize import cnpj_valido, formatar_cnpj, normalizar, so_digitos

# Sinônimos aceitos por campo, do mais específico para o mais genérico.
COLUNAS = {
    "cnpj": ["CNPJ", "CPF/CNPJ", "CPF CNPJ", "INSCRICAO"],
    "razao_social": ["RAZAO SOCIAL", "RAZAO", "NOME EMPRESARIAL", "NOME DA EMPRESA",
                     "EMPRESA", "CLIENTE", "NOME"],
    "nome_fantasia": ["NOME FANTASIA", "FANTASIA", "APELIDO"],
    "codigo": ["CODIGO EMPRESA", "COD EMPRESA", "CODIGO", "COD."],
    "regime": ["REGIME TRIBUTARIO", "REGIME", "TRIBUTACAO", "ENQUADRAMENTO"],
    "situacao": ["SITUACAO", "STATUS", "ATIVA", "ATIVO"],
    "tarefa": ["OBRIGACAO", "TAREFA", "SERVICO", "ATIVIDADE", "PROCESSO",
               "DESCRICAO"],
    "competencia": ["COMPETENCIA", "PERIODO", "REFERENCIA"],
    "setor": ["SETOR", "DEPARTAMENTO", "AREA", "EQUIPE"],
}


def ler_planilha(caminho: str | Path) -> list[dict[str, str]]:
    """Lê CSV (; ou ,) ou XLSX. Devolve linhas como dicionário."""
    p = Path(caminho)
    if not p.exists():
        raise FileNotFoundError(f"arquivo não encontrado: {p}")
    if p.suffix.lower() in (".xlsx", ".xlsm"):
        return _ler_xlsx(p)
    bruto = p.read_text(encoding="utf-8-sig", errors="ignore")
    primeira = next((l for l in bruto.splitlines() if l.strip()), "")
    delim = ";" if primeira.count(";") >= primeira.count(",") else ","
    return [{(k or "").strip(): (v or "").strip()
             for k, v in linha.items() if k is not None}
            for linha in csv.DictReader(bruto.splitlines(), delimiter=delim)]


def _ler_xlsx(p: Path) -> list[dict[str, str]]:
    try:
        import openpyxl
    except ImportError as erro:
        raise RuntimeError(
            "para ler .xlsx instale openpyxl (pip install openpyxl), "
            "ou exporte a planilha como CSV") from erro
    wb = openpyxl.load_workbook(str(p), data_only=True, read_only=True)
    aba = wb.worksheets[0]
    linhas = aba.iter_rows(values_only=True)
    cabecalho = [str(c).strip() if c is not None else "" for c in next(linhas, [])]
    saida = []
    for linha in linhas:
        valores = ["" if c is None else str(c).strip() for c in linha]
        if any(valores):
            saida.append(dict(zip(cabecalho, valores)))
    return saida


def mapear_colunas(cabecalhos: list[str]) -> dict[str, str]:
    """Liga campo lógico -> nome real da coluna, tolerando variações."""
    normalizados = {normalizar(c): c for c in cabecalhos if c}
    mapa: dict[str, str] = {}
    for campo, sinonimos in COLUNAS.items():
        for sinonimo in sinonimos:
            achado = next((real for norm, real in normalizados.items()
                           if norm == sinonimo), None)
            if achado is None:
                achado = next((real for norm, real in normalizados.items()
                               if sinonimo in norm), None)
            if achado and achado not in mapa.values():
                mapa[campo] = achado
                break
    return mapa


def valor(linha: dict, mapa: dict, campo: str) -> str:
    coluna = mapa.get(campo)
    return (linha.get(coluna) or "").strip() if coluna else ""


@dataclass
class Divergencia:
    tipo: str
    chave: str
    detalhe: str
    acao: str = ""


@dataclass
class ConferenciaEmpresas:
    no_onvio: int = 0
    no_cadastro: int = 0
    coincidentes: int = 0
    divergencias: list[Divergencia] = field(default_factory=list)


def conferir_empresas(linhas: list[dict], cadastro) -> ConferenciaEmpresas:
    mapa = mapear_colunas(list(linhas[0].keys()) if linhas else [])
    if "cnpj" not in mapa:
        raise ValueError(
            "a exportação não tem coluna de CNPJ reconhecível. "
            f"colunas encontradas: {list(linhas[0].keys()) if linhas else []}")

    resultado = ConferenciaEmpresas(no_cadastro=len(cadastro.empresas))
    vistos: set[str] = set()

    for linha in linhas:
        cnpj = so_digitos(valor(linha, mapa, "cnpj"))
        razao = valor(linha, mapa, "razao_social")
        if not cnpj:
            continue
        resultado.no_onvio += 1
        vistos.add(cnpj)

        if not cnpj_valido(cnpj):
            resultado.divergencias.append(Divergencia(
                "CNPJ_INVALIDO_NO_ONVIO", formatar_cnpj(cnpj), razao,
                "conferir o cadastro dentro do Onvio"))
            continue

        empresa = cadastro.por_cnpj.get(cnpj)
        if not empresa:
            resultado.divergencias.append(Divergencia(
                "FALTA_NO_CADASTRO", formatar_cnpj(cnpj), razao,
                "acrescentar em data/empresas.csv — sem isso todo documento "
                "dessa empresa vira pendência"))
            continue

        resultado.coincidentes += 1
        if razao and normalizar(razao) != normalizar(empresa.razao_social):
            resultado.divergencias.append(Divergencia(
                "RAZAO_DIFERENTE", formatar_cnpj(cnpj),
                f"Onvio: {razao} | cadastro: {empresa.razao_social}",
                "alinhar a razão social ou usar APELIDOS no cadastro"))
        codigo = valor(linha, mapa, "codigo")
        if codigo and empresa.codigo_dominio and codigo != empresa.codigo_dominio:
            resultado.divergencias.append(Divergencia(
                "CODIGO_DOMINIO_DIFERENTE", formatar_cnpj(cnpj),
                f"Onvio: {codigo} | cadastro: {empresa.codigo_dominio}",
                "corrigir CODIGO_DOMINIO em data/empresas.csv"))

    for empresa in cadastro.empresas:
        if empresa.ativa and empresa.cnpj and empresa.cnpj not in vistos:
            resultado.divergencias.append(Divergencia(
                "FALTA_NO_ONVIO", formatar_cnpj(empresa.cnpj), empresa.razao_social,
                "empresa ativa no cadastro e ausente da exportação — o Express "
                "nunca vai achar tarefa para ela"))
    return resultado


@dataclass
class ConferenciaTarefas:
    total: int = 0
    por_template: dict[str, int] = field(default_factory=dict)
    sem_template: list[str] = field(default_factory=list)
    templates_sem_tarefa: list[str] = field(default_factory=list)


def casar_tarefa(nome: str, templates) -> str | None:
    """Descobre a que template uma obrigação do Onvio corresponde.

    Usa as mesmas palavras-chave da classificação de documento: se o template
    reconhece o documento, deve reconhecer o nome da obrigação.
    """
    alvo = normalizar(nome)
    caixa = nome.upper()
    melhor, melhor_peso = None, 0
    for t in templates.values():
        for termo in t.principais:
            if termo.encontrado(alvo, caixa) and termo.peso > melhor_peso:
                melhor, melhor_peso = t.id, termo.peso
        for secundaria in t.secundarias:
            if _contem(alvo, secundaria) and melhor is None:
                melhor, melhor_peso = t.id, 1
    return melhor


def conferir_tarefas(linhas: list[dict], templates) -> ConferenciaTarefas:
    mapa = mapear_colunas(list(linhas[0].keys()) if linhas else [])
    if "tarefa" not in mapa:
        raise ValueError(
            "a exportação não tem coluna de obrigação/tarefa reconhecível. "
            f"colunas encontradas: {list(linhas[0].keys()) if linhas else []}")

    resultado = ConferenciaTarefas()
    nomes_sem_template: set[str] = set()
    for linha in linhas:
        nome = valor(linha, mapa, "tarefa")
        if not nome:
            continue
        resultado.total += 1
        tipo = casar_tarefa(nome, templates)
        if tipo:
            resultado.por_template[tipo] = resultado.por_template.get(tipo, 0) + 1
        else:
            nomes_sem_template.add(nome)

    resultado.sem_template = sorted(nomes_sem_template)
    resultado.templates_sem_tarefa = sorted(
        t for t in templates if t not in resultado.por_template)
    return resultado


def gerar_cadastro(linhas: list[dict]) -> list[dict[str, str]]:
    """Monta as linhas de data/empresas.csv a partir da exportação do Onvio."""
    from .empresas import COLUNAS as COLUNAS_CADASTRO

    mapa = mapear_colunas(list(linhas[0].keys()) if linhas else [])
    if "cnpj" not in mapa:
        raise ValueError("a exportação não tem coluna de CNPJ reconhecível")

    saida: list[dict[str, str]] = []
    vistos: set[str] = set()
    for linha in linhas:
        cnpj = so_digitos(valor(linha, mapa, "cnpj"))
        if not cnpj or cnpj in vistos or not cnpj_valido(cnpj):
            continue
        vistos.add(cnpj)
        razao = valor(linha, mapa, "razao_social")
        situacao = normalizar(valor(linha, mapa, "situacao"))
        registro = {c: "" for c in COLUNAS_CADASTRO}
        registro.update({
            "ID_EMPRESA": f"{len(saida) + 1:04d}",
            "CODIGO_DOMINIO": valor(linha, mapa, "codigo"),
            "RAZAO_SOCIAL": razao.upper(),
            "NOME_FANTASIA": valor(linha, mapa, "nome_fantasia"),
            "NOME_CURTO": _nome_curto(razao),
            "CNPJ": formatar_cnpj(cnpj),
            "REGIME_TRIBUTARIO": valor(linha, mapa, "regime").upper(),
            "SETOR_PADRAO": "FISCAL",
            "ATIVA": "NAO" if situacao.startswith(("INAT", "BAIX", "NAO")) else "SIM",
        })
        saida.append(registro)
    return saida


def _nome_curto(razao: str) -> str:
    """Primeiras palavras úteis da razão social, sem sufixo societário."""
    descartar = {"LTDA", "ME", "EPP", "EIRELI", "SA", "S.A", "S/A", "MEI",
                 "SOCIEDADE", "SIMPLES", "LIMITADA", "COMERCIO", "DE", "DA",
                 "DO", "E", "SERVICOS", "INDUSTRIA"}
    palavras = [p for p in normalizar(razao).replace("/", " ").split()
                if p not in descartar and not p.isdigit()]
    return "-".join(palavras[:2])[:24].strip("-")


def escrever_cadastro(registros: list[dict], destino: str | Path) -> Path:
    from .empresas import COLUNAS as COLUNAS_CADASTRO

    alvo = Path(destino)
    alvo.parent.mkdir(parents=True, exist_ok=True)
    with alvo.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_CADASTRO, delimiter=";")
        w.writeheader()
        w.writerows(registros)
    return alvo
