"""Em que ordem configurar os próximos templates, a partir da carteira real.

A lista de prioridade do plano original (DAS, PIS, COFINS, IR, CSLL) assume uma
carteira de Lucro Presumido/Real. Num escritório com carteira majoritariamente
Simples Nacional, PIS e COFINS podem ter volume quase zero — e configurá-los
primeiro é gastar um dia num template que quase nunca vai rodar.

Aqui o volume estimado sai do REGIME de cada empresa cadastrada. Quando existe
exportação de tarefas do Onvio, ela manda: obrigação cadastrada é fato,
estimativa por regime é só aproximação.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .normalize import normalizar

# Documentos por empresa por mês, por regime. Aproximações declaradas —
# servem para ordenar, não para prometer número.
FREQUENCIA = {
    "SIMPLES": {"DAS": 1.0},
    "PRESUMIDO": {"PIS": 1.0, "COFINS": 1.0, "IR": 0.34, "CSLL": 0.34},
    "REAL": {"PIS": 1.0, "COFINS": 1.0, "IR": 1.0, "CSLL": 1.0},
    "MEI": {"DAS": 1.0},
}


def classificar_regime(texto: str) -> str | None:
    t = normalizar(texto)
    if "MEI" == t or "MICROEMPREENDEDOR" in t:
        return "MEI"
    if "SIMPLES" in t:
        return "SIMPLES"
    if "PRESUMIDO" in t:
        return "PRESUMIDO"
    if "REAL" in t:
        return "REAL"
    return None


@dataclass
class Linha:
    tipo: str
    empresas: int = 0
    docs_mes: float = 0.0
    tarefas_onvio: int | None = None
    tem_template: bool = False
    trava: bool = False          # existe para separar, não para ter volume
    nota: str = ""


@dataclass
class Prioridade:
    total_empresas: int = 0
    por_regime: dict[str, int] = field(default_factory=dict)
    sem_regime: list[str] = field(default_factory=list)
    linhas: list[Linha] = field(default_factory=list)
    usou_tarefas: bool = False


def calcular(cadastro, templates, tarefas=None) -> Prioridade:
    """`tarefas` é o resultado de onvio.conferir_tarefas, quando houver."""
    p = Prioridade()
    empresas_por_tipo: dict[str, int] = {}
    docs_por_tipo: dict[str, float] = {}

    for empresa in cadastro.empresas:
        if not empresa.ativa:
            continue
        p.total_empresas += 1
        regime = classificar_regime(empresa.regime)
        if not regime:
            p.sem_regime.append(f"{empresa.id} - {empresa.razao_social}")
            continue
        p.por_regime[regime] = p.por_regime.get(regime, 0) + 1
        for tipo, freq in FREQUENCIA[regime].items():
            empresas_por_tipo[tipo] = empresas_por_tipo.get(tipo, 0) + 1
            docs_por_tipo[tipo] = docs_por_tipo.get(tipo, 0) + freq

    tipos = set(empresas_por_tipo) | set(templates)
    if tarefas:
        p.usou_tarefas = True
        tipos |= set(tarefas.por_template)

    for tipo in tipos:
        linha = Linha(
            tipo=tipo,
            empresas=empresas_por_tipo.get(tipo, 0),
            docs_mes=round(docs_por_tipo.get(tipo, 0.0), 1),
            tem_template=tipo in templates,
            tarefas_onvio=(tarefas.por_template.get(tipo, 0) if tarefas else None),
            trava=bool(getattr(templates.get(tipo), "sempre_validar", False)),
        )
        if linha.trava:
            linha.nota = ("trava de segurança: nunca é arquivado sozinho e não "
                          "precisa de volume — deixe como está")
        elif linha.tarefas_onvio == 0:
            linha.nota = "nenhuma obrigação cadastrada no Onvio — Express devolverá 'não encontrada'"
        elif linha.empresas == 0 and linha.tarefas_onvio:
            linha.nota = "há obrigação no Onvio mas nenhuma empresa do cadastro se enquadra — conferir regimes"
        elif linha.empresas == 0:
            linha.nota = "nenhuma empresa ativa se enquadra — configurar depois"
        elif not linha.tem_template:
            linha.nota = "template ainda não existe"
        p.linhas.append(linha)

    # Obrigação real pesa mais que estimativa por regime.
    # Travas vão para o fim: não disputam prioridade com tributo de volume.
    p.linhas.sort(key=lambda l: (not l.trava, l.tarefas_onvio or 0, l.docs_mes,
                                 l.empresas), reverse=True)
    return p


def novos_candidatos(tarefas, limite: int = 10) -> list[str]:
    """Obrigações do Onvio que nenhum template cobre — candidatas a template novo."""
    return list(tarefas.sem_template[:limite]) if tarefas else []
