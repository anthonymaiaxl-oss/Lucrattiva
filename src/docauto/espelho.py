"""Cópias secundárias que falharam (Dropbox fora do ar, rede caída).

O documento já está arquivado no destino principal — a cópia que faltou não é
motivo para mandar nada para pendência. Ela vira uma linha aqui e é refeita
depois com `docauto espelhar`. É a diferença entre "não copiou" e "ninguém
nunca soube que não copiou".
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path

from .archive import arquivar

PENDENTE = "PENDENTE"
COPIADO = "COPIADO"


@dataclass
class Espelho:
    hash: str = ""
    origem: str = ""          # arquivo já arquivado no destino principal
    destino_nome: str = ""
    pasta_destino: str = ""
    nome: str = ""
    estado: str = PENDENTE
    erro: str = ""
    registrado_em: str = ""
    copiado_em: str = ""


CABECALHO = [f.name for f in fields(Espelho)]


class FilaEspelho:
    def __init__(self, arquivo: str | Path):
        self.arquivo = Path(arquivo)
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        self.itens: list[Espelho] = []
        if self.arquivo.exists():
            texto = self.arquivo.read_text(encoding="utf-8-sig")
            for linha in csv.DictReader(texto.splitlines(), delimiter=";"):
                self.itens.append(Espelho(**{c: (linha.get(c) or "") for c in CABECALHO}))

    def salvar(self) -> None:
        with self.arquivo.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=CABECALHO, delimiter=";")
            w.writeheader()
            for item in self.itens:
                w.writerow(asdict(item))

    def registrar(self, item: Espelho) -> None:
        ja = next((i for i in self.itens
                   if i.hash == item.hash and i.destino_nome == item.destino_nome
                   and i.estado == PENDENTE), None)
        if ja:
            return
        item.registrado_em = datetime.now().isoformat(timespec="seconds")
        self.itens.append(item)
        self.salvar()

    def refazer(self, dry_run: bool = False) -> list[tuple[Espelho, str]]:
        resultados: list[tuple[Espelho, str]] = []
        for item in [i for i in self.itens if i.estado == PENDENTE]:
            origem = Path(item.origem)
            if not origem.exists():
                resultados.append((item, "ORIGEM_SUMIU"))
                continue
            try:
                status, _ = arquivar(origem, item.pasta_destino, item.nome, dry_run)
            except OSError as erro:
                item.erro = str(erro)
                resultados.append((item, "AINDA_INDISPONIVEL"))
                continue
            if not dry_run:
                item.estado = COPIADO
                item.copiado_em = datetime.now().isoformat(timespec="seconds")
                item.erro = ""
            resultados.append((item, status))
        if not dry_run and resultados:
            self.salvar()
        return resultados

    def pendentes(self) -> list[Espelho]:
        return [i for i in self.itens if i.estado == PENDENTE]
