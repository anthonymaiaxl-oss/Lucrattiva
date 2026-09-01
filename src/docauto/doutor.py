"""Verificação de ambiente: diz o que falta para o fluxo funcionar no servidor.

Existe porque a maior parte dos problemas de implantação não é de código —
é caminho que não existe, pasta sem permissão de escrita, leitor de PDF
ausente, conta do agendador sem acesso à rede. Tudo isso é detectável antes
de perder um dia procurando.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

OK, AVISO, ERRO = "OK", "AVISO", "ERRO"


@dataclass
class Checagem:
    nivel: str
    item: str
    detalhe: str = ""
    acao: str = ""


def _gravavel(pasta: Path, criar: bool = True) -> tuple[bool, str]:
    """Testa escrita de verdade. Permissão de leitura não garante escrita."""
    if not criar and not pasta.exists():
        return False, "não existe"
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=pasta, prefix=".docauto-", delete=True):
            pass
        return True, ""
    except OSError as erro:
        return False, str(erro)


def _espaco_livre(pasta: Path) -> str:
    try:
        livre = shutil.disk_usage(pasta).free / (1024 ** 3)
        return f"{livre:.0f} GB livres"
    except OSError:
        return "espaço não verificado"


def _leitor_pdf() -> tuple[str | None, str]:
    for modulo, nome in (("pypdf", "pypdf"), ("pdfplumber", "pdfplumber")):
        try:
            __import__(modulo)
            return nome, ""
        except ImportError:
            continue
    if shutil.which("pdftotext"):
        return "pdftotext (poppler)", ""
    return None, "pip install pypdf"


def _ocr_disponivel() -> tuple[bool, str]:
    try:
        __import__("pytesseract")
        __import__("pdf2image")
    except ImportError:
        return False, "pip install pytesseract pdf2image"
    if not shutil.which("tesseract"):
        return False, "binário tesseract não encontrado no PATH"
    return True, ""


def verificar(cfg: dict, processador=None) -> list[Checagem]:
    from .config import destinos, entradas

    saida: list[Checagem] = []
    saida.append(Checagem(OK, "config", cfg.get("_arquivo", "?")))

    # ---------------- cadastro, templates, códigos ----------------
    if processador is not None:
        erros = processador.cadastro.validar()
        ativas = [e for e in processador.cadastro.empresas if e.ativa]
        saida.append(Checagem(
            ERRO if erros else OK, "cadastro de empresas",
            f"{len(processador.cadastro.empresas)} empresa(s), {len(ativas)} ativa(s), "
            f"{len(erros)} erro(s)",
            "; ".join(erros[:3]) if erros else ""))

        saida.append(Checagem(OK, "templates",
                              ", ".join(sorted(processador.templates))))
        saida.append(Checagem(
            OK if processador.tabela.conferida else AVISO, "tabela de códigos",
            "CONFERIDA" if processador.tabela.conferida else "NAO_CONFERIDA",
            "" if processador.tabela.conferida
            else "conferir contra a tabela oficial da RFB antes de produção (docs/03)"))

    # ---------------- leitura de arquivos ----------------
    leitor, dica = _leitor_pdf()
    saida.append(Checagem(OK if leitor else ERRO, "leitor de PDF",
                          leitor or "nenhum instalado",
                          "" if leitor else f"{dica} — sem ele nenhum PDF é lido"))
    try:
        __import__("openpyxl")
        saida.append(Checagem(OK, "leitor de planilha", "openpyxl"))
    except ImportError:
        saida.append(Checagem(AVISO, "leitor de planilha", "openpyxl ausente",
                              "pip install openpyxl (só se receber .xlsx)"))

    ocr_ligado = cfg["processamento"].get("ocr_habilitado", False)
    ocr_ok, dica_ocr = _ocr_disponivel()
    if ocr_ligado:
        saida.append(Checagem(OK if ocr_ok else ERRO, "OCR",
                              "disponível" if ocr_ok else "ligado no config mas indisponível",
                              dica_ocr))
    else:
        saida.append(Checagem(OK, "OCR", "desligado (Fase 2)"))

    # ---------------- pastas de trabalho ----------------
    for pasta in entradas(cfg):
        p = Path(pasta)
        if not p.exists():
            saida.append(Checagem(ERRO, "entrada", pasta, "pasta não existe"))
            continue
        pode, erro = _gravavel(p)
        saida.append(Checagem(OK if pode else ERRO, "entrada", pasta,
                              "" if pode else f"sem permissão de escrita: {erro}"))

    for chave in ("processados", "pendentes"):
        caminho = cfg["pastas"].get(chave)
        if not caminho:
            continue
        pode, erro = _gravavel(Path(caminho))
        saida.append(Checagem(OK if pode else ERRO, chave, caminho,
                              "" if pode else erro))

    # ---------------- destinos ----------------
    try:
        lista = destinos(cfg)
    except (KeyError, ValueError) as erro:
        saida.append(Checagem(ERRO, "destinos", str(erro)))
        lista = []
    for destino in lista:
        p = Path(destino["raiz"])
        marca = " (principal)" if destino["principal"] else ""
        detalhe = f"{destino['raiz']}{marca}"

        # A raiz pode ainda não existir (é criada no primeiro arquivo), mas a
        # pasta que a contém tem de existir. Sem essa checagem, um caminho de
        # Dropbox errado vira uma pasta local comum: os arquivos empilham e
        # NUNCA sincronizam, e tudo parece estar funcionando.
        if not p.exists() and not p.parent.exists():
            saida.append(Checagem(
                ERRO if destino["principal"] else AVISO,
                f"destino {destino['nome']}", detalhe,
                f"nem a pasta que o contém existe ({p.parent}) — confira o caminho; "
                "criar aqui produziria uma pasta local que não sincroniza"))
            continue

        pode, erro = _gravavel(p)
        nivel = OK if pode else (ERRO if destino["principal"] else AVISO)
        acao = _espaco_livre(p) if pode else f"indisponível: {erro}"
        if not pode and not destino["principal"]:
            acao += " — cópias vão para a fila de espelho"
        saida.append(Checagem(nivel, f"destino {destino['nome']}", detalhe, acao))

    # ---------------- limite de caminho do Windows ----------------
    if processador is not None and processador.cadastro.empresas and lista:
        saida.append(_checar_caminho_longo(cfg, processador, lista))

    # ---------------- envio ----------------
    envio = cfg.get("envio", {})
    if not envio.get("habilitado"):
        saida.append(Checagem(AVISO, "envio ao Express", "desligado",
                              "ligar em envio.habilitado quando for a hora (docs/11)"))
    else:
        modo = envio.get("modo", "lote_manual")
        alvo = envio.get("pasta_monitorada") if modo == "pasta_monitorada" \
            else envio.get("pasta_lote")
        if not alvo:
            saida.append(Checagem(ERRO, "envio ao Express",
                                  f"modo {modo} sem pasta configurada"))
        else:
            pode, erro = _gravavel(Path(alvo))
            saida.append(Checagem(OK if pode else ERRO, "envio ao Express",
                                  f"modo {modo} -> {alvo}", "" if pode else erro))
        piloto = envio.get("empresas_piloto") or []
        saida.append(Checagem(OK, "alcance do envio",
                              f"piloto: {piloto}" if piloto else "TODAS as empresas",
                              "" if piloto else "comece com uma empresa (docs/11)"))

    return saida


def _checar_caminho_longo(cfg, processador, lista) -> Checagem:
    """Simula o pior caso real: empresa de nome mais longo, destino mais fundo."""
    from . import routing

    empresa = max(processador.cadastro.empresas, key=lambda e: len(e.pasta))
    template = processador.templates.get("COFINS") or next(iter(processador.templates.values()))

    class _Cls:
        tipo, subtipo = "COFINS", None

    pior_pasta, pior_nome, pior_tamanho = "", "", 0
    for destino in lista:
        pasta = routing.montar_caminho(empresa, _Cls(), "2026-12", cfg, destino["raiz"],
                                       setor=template.setor, grupo=template.grupo)
        nome = routing.montar_nome(empresa, _Cls(), "2026-12", ".pdf", cfg)
        tamanho = len(str(Path(pasta) / nome))
        if tamanho > pior_tamanho:
            pior_pasta, pior_nome, pior_tamanho = pasta, nome, tamanho

    limite = cfg["estrutura"]["limite_caminho"]
    folga = limite - pior_tamanho
    if folga < 0:
        return Checagem(ERRO, "limite de caminho",
                        f"{pior_tamanho} caracteres (limite {limite})",
                        f"encurtar a raiz do destino ou o nome de '{empresa.razao_social}'")
    if folga < 30:
        return Checagem(AVISO, "limite de caminho",
                        f"pior caso {pior_tamanho} de {limite}",
                        "pouca folga — evite raiz de destino mais profunda")
    return Checagem(OK, "limite de caminho",
                    f"pior caso {pior_tamanho} de {limite} ({folga} de folga)")


def resumo(checagens: list[Checagem]) -> tuple[int, int]:
    erros = sum(1 for c in checagens if c.nivel == ERRO)
    avisos = sum(1 for c in checagens if c.nivel == AVISO)
    return erros, avisos
