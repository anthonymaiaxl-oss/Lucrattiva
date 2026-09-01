"""Normalização de texto e extração de campos primitivos (CNPJ, datas, valores).

Regra de ouro deste módulo: ele NUNCA adivinha. Quando um campo não aparece de
forma reconhecível, devolve None — quem decide o que fazer é o pipeline.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

MESES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARCO": 3, "ABRIL": 4, "MAIO": 5,
    "JUNHO": 6, "JULHO": 7, "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
    "NOVEMBRO": 11, "DEZEMBRO": 12,
}
MES_EXTENSO = {v: k for k, v in MESES.items()}

# Rótulos aceitos para competência, em ordem de prioridade (ver docs/06).
ROTULOS_COMPETENCIA = [
    "COMPETENCIA", "MES/ANO", "MES DE REFERENCIA", "MES REFERENCIA",
    "REFERENCIA", "MES DE COMPETENCIA",
]
ROTULOS_APURACAO = [
    "PERIODO DE APURACAO", "PERIODO APURACAO", "PERIODO-DE-APURACAO",
    "APURACAO", "P.A.", "PA",
]
ROTULOS_VENCIMENTO = [
    "VENCIMENTO", "DATA DE VENCIMENTO", "PAGAR ATE", "DATA DE PAGAMENTO",
    "VALIDO ATE",
]

_RE_CNPJ = re.compile(r"\b(\d{2})[.\s]?(\d{3})[.\s]?(\d{3})[/\s]?(\d{4})[-\s]?(\d{2})\b")
_RE_VALOR = re.compile(r"(?<![\d,.])(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})(?![\d])")


def remover_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar(texto: str) -> str:
    """Maiúsculas, sem acento, espaços colapsados. Preserva quebras de linha."""
    texto = remover_acentos(texto or "").upper()
    texto = texto.replace("\u00a0", " ")
    linhas = [re.sub(r"[ \t]+", " ", l).strip() for l in texto.splitlines()]
    return "\n".join(linhas)


def preservar_caixa(texto: str) -> str:
    """Sem acento, mas mantendo maiúsculas/minúsculas originais.

    Usado por termos como "DAS" e "PIS", que em caixa baixa são preposição ou
    ruído. Sem esta visão, todo documento em português "contém DAS".
    """
    texto = remover_acentos(texto or "").replace("\u00a0", " ")
    linhas = [re.sub(r"[ \t]+", " ", l).strip() for l in texto.splitlines()]
    return "\n".join(linhas)


def so_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def cnpj_valido(cnpj: str) -> bool:
    """Validação dos dois dígitos verificadores (módulo 11)."""
    n = so_digitos(cnpj)
    if len(n) != 14 or n == n[0] * 14:
        return False
    for tamanho in (12, 13):
        pesos = list(range(tamanho - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(int(d) * p for d, p in zip(n[:tamanho], pesos))
        resto = soma % 11
        dv = 0 if resto < 2 else 11 - resto
        if int(n[tamanho]) != dv:
            return False
    return True


def formatar_cnpj(cnpj: str) -> str:
    n = so_digitos(cnpj)
    if len(n) != 14:
        return cnpj
    return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"


def extrair_cnpjs(texto: str) -> tuple[list[str], list[str]]:
    """(válidos, inválidos) na ordem em que aparecem, sem repetição.

    CNPJs com dígito verificador inválido não são usados para identificar a
    empresa — quase sempre são erro de OCR, e um CNPJ errado leva o documento
    para a empresa errada. Mas são registrados, porque são a explicação certa
    para o operador na fila de pendências.
    """
    validos: list[str] = []
    invalidos: list[str] = []
    for m in _RE_CNPJ.finditer(texto):
        n = "".join(m.groups())
        destino = validos if cnpj_valido(n) else invalidos
        if n not in destino:
            destino.append(n)
    return validos, invalidos


def _janela_apos(texto: str, rotulo: str, tamanho: int = 80) -> list[str]:
    """Trechos de texto logo após cada ocorrência de um rótulo.

    A fronteira de palavra é obrigatória: sem ela o rótulo "PA" casaria dentro
    de "PIS/PASEP" e a automação leria a data de vencimento como competência.
    """
    padrao = re.compile(r"(?<![A-Z0-9])" + re.escape(rotulo) + r"(?![A-Z0-9])")
    return [texto[m.end(): m.end() + tamanho] for m in padrao.finditer(texto)]


def _competencia_no_trecho(trecho: str) -> str | None:
    """Procura MM/AAAA, AAAA-MM, DD/MM/AAAA ou MES/AAAA por extenso.

    O trecho é cortado antes de qualquer rótulo de vencimento: a janela de
    leitura pode atravessar linhas, e a data de vencimento não é competência.
    """
    for rotulo in ROTULOS_VENCIMENTO:
        pos = trecho.find(rotulo)
        if pos >= 0:
            trecho = trecho[:pos]
    m = re.search(r"\b(0[1-9]|1[0-2])[/\-.](\d{4})\b", trecho)
    if m:
        return f"{m.group(2)}-{m.group(1)}"
    m = re.search(r"\b(\d{4})[/\-](0[1-9]|1[0-2])\b", trecho)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"\b\d{1,2}[/\-.](0[1-9]|1[0-2])[/\-.](\d{4})\b", trecho)
    if m:
        return f"{m.group(2)}-{m.group(1)}"
    m = re.search(r"\b(" + "|".join(MESES) + r")\s*(?:DE\s*)?[/\-]?\s*(\d{4})\b", trecho)
    if m:
        return f"{m.group(2)}-{MESES[m.group(1)]:02d}"
    return None


@dataclass
class Competencia:
    valor: str | None = None           # "AAAA-MM"
    fonte: str = "NAO_ENCONTRADA"      # EXPLICITA | APURACAO | INFERIDA | NAO_ENCONTRADA
    trecho: str = ""


def extrair_competencia(texto_norm: str) -> Competencia:
    """Prioridade: campo explícito > período de apuração > inferência.

    A data de VENCIMENTO nunca vira competência aqui. Guia de agosto vence em
    setembro/outubro; usar o vencimento erraria o mês em praticamente todo
    documento e o erro só apareceria meses depois, na conferência.
    """
    for rotulo in ROTULOS_COMPETENCIA:
        for trecho in _janela_apos(texto_norm, rotulo):
            comp = _competencia_no_trecho(trecho)
            if comp:
                return Competencia(comp, "EXPLICITA", trecho.strip()[:60])

    for rotulo in ROTULOS_APURACAO:
        for trecho in _janela_apos(texto_norm, rotulo):
            comp = _competencia_no_trecho(trecho)
            if comp:
                return Competencia(comp, "APURACAO", trecho.strip()[:60])

    # Último recurso: MM/AAAA isolado que NÃO esteja colado a rótulo de
    # vencimento. Fonte INFERIDA vale menos pontos e costuma cair em revisão.
    proibidos = []
    for rotulo in ROTULOS_VENCIMENTO:
        for m in re.finditer(re.escape(rotulo), texto_norm):
            proibidos.append((m.start(), m.end() + 40))
    for m in re.finditer(r"\b(0[1-9]|1[0-2])/(\d{4})\b", texto_norm):
        if any(ini <= m.start() <= fim for ini, fim in proibidos):
            continue
        return Competencia(f"{m.group(2)}-{m.group(1)}", "INFERIDA",
                           texto_norm[max(0, m.start() - 30): m.end() + 10].strip())
    return Competencia()


def competencia_plausivel(comp: str, hoje: date, meses_passado: int,
                          meses_futuro: int) -> bool:
    try:
        ano, mes = int(comp[:4]), int(comp[5:7])
    except (ValueError, IndexError):
        return False
    if not 1 <= mes <= 12:
        return False
    delta = (hoje.year - ano) * 12 + (hoje.month - mes)
    return -meses_futuro <= delta <= meses_passado


def extrair_valor(texto_norm: str) -> float | None:
    """Valor total do documento. Preferimos rótulos explícitos de total."""
    rotulos = [
        "VALOR TOTAL DO DOCUMENTO", "TOTAL DO DOCUMENTO", "VALOR TOTAL",
        "TOTAL A PAGAR", "VALOR DO DOCUMENTO", "VALOR PRINCIPAL",
    ]
    for rotulo in rotulos:
        for trecho in _janela_apos(texto_norm, rotulo, 40):
            m = _RE_VALOR.search(trecho)
            if m:
                return _para_float(m.group(1))
    return None


def _para_float(valor: str) -> float:
    return float(valor.replace(".", "").replace(",", "."))


def extrair_vencimento(texto_norm: str) -> str | None:
    for rotulo in ROTULOS_VENCIMENTO:
        for trecho in _janela_apos(texto_norm, rotulo, 40):
            m = re.search(r"\b(\d{2})[/\-.](\d{2})[/\-.](\d{4})\b", trecho)
            if m:
                return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def extrair_codigos_receita(texto_norm: str) -> list[str]:
    """Códigos de 4 dígitos ancorados em rótulo. Sem rótulo, não vale.

    Um PDF tem dezenas de números de 4 dígitos (ano, CEP, agência, nº do
    documento). Sem a âncora, o classificador viraria gerador de coincidências.
    """
    rotulos = [
        "CODIGO DA RECEITA", "COD. RECEITA", "COD RECEITA", "CODIGO RECEITA",
        "CODIGO DE RECEITA", "RECEITA/DENOMINACAO",
    ]
    achados: list[str] = []
    for rotulo in rotulos:
        for trecho in _janela_apos(texto_norm, rotulo, 30):
            for m in re.finditer(r"\b(\d{4})(?:-\d{2})?\b", trecho):
                cod = m.group(1)
                if cod not in achados:
                    achados.append(cod)
    return achados


_RE_RAZAO = re.compile(
    r"[A-Z0-9&.,'\- ]{6,120}?\s(LTDA|S\.?A\.?|ME|EPP|EIRELI|MEI|SOCIEDADE"
    r"|SIMPLES|LIMITADA)\b\.?")


def extrair_razoes_sociais(texto_norm: str) -> list[str]:
    """Candidatos a razão social: trechos com sufixo societário.

    O rótulo é removido antes da busca. No DARF a linha vem como
    "01 NOME / TELEFONE: EMPRESA EXEMPLO LTDA" — sem tirar o rótulo, o nome
    não é reconhecido e a identificação de nível 2 deixa de funcionar
    justamente nos documentos em que ela mais importa.
    """
    candidatos: list[str] = []
    for linha in texto_norm.splitlines():
        trecho = linha.rsplit(":", 1)[-1] if ":" in linha else linha
        m = _RE_RAZAO.search(trecho.strip())
        if not m:
            continue
        nome = re.sub(r"\s+", " ", m.group(0)).strip(" .,-")
        # descarta sobras de numeração de campo ("01 EMPRESA X LTDA")
        nome = re.sub(r"^\d{1,2}\s+", "", nome)
        if len(nome) >= 6 and nome not in candidatos:
            candidatos.append(nome)
    return candidatos


@dataclass
class Extracao:
    """Tudo que foi lido do documento, sem nenhuma interpretação de negócio."""
    texto_norm: str = ""
    texto_caixa: str = ""
    origem_texto: str = "NATIVO"          # NATIVO | OCR | PLANILHA | VAZIO
    cnpjs: list[str] = field(default_factory=list)
    cnpjs_invalidos: list[str] = field(default_factory=list)
    razoes: list[str] = field(default_factory=list)
    codigos_receita: list[str] = field(default_factory=list)
    competencia: Competencia = field(default_factory=Competencia)
    valor: float | None = None
    vencimento: str | None = None

    @property
    def cnpj(self) -> str | None:
        return self.cnpjs[0] if self.cnpjs else None


def extrair_campos(texto_bruto: str, origem_texto: str = "NATIVO") -> Extracao:
    norm = normalizar(texto_bruto)
    validos, invalidos = extrair_cnpjs(norm)
    return Extracao(
        texto_norm=norm,
        texto_caixa=preservar_caixa(texto_bruto),
        origem_texto=origem_texto if norm.strip() else "VAZIO",
        cnpjs=validos,
        cnpjs_invalidos=invalidos,
        razoes=extrair_razoes_sociais(norm),
        codigos_receita=extrair_codigos_receita(norm),
        competencia=extrair_competencia(norm),
        valor=extrair_valor(norm),
        vencimento=extrair_vencimento(norm),
    )
