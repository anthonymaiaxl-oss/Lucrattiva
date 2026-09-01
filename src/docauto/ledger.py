"""Registro de tudo que o robô fez. CSV para o escritório, JSONL para auditoria."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path

CABECALHO = [
    "data_hora", "arquivo_origem", "empresa_id", "empresa", "cnpj", "tipo",
    "subtipo", "competencia", "score", "decisao", "status_arquivo", "destino",
    "hash_documento", "envio", "copias", "travas", "avisos",
]


class Registro:
    def __init__(self, csv_path: str | Path, jsonl_path: str | Path):
        self.csv_path = Path(csv_path)
        self.jsonl_path = Path(jsonl_path)
        for p in (self.csv_path, self.jsonl_path):
            p.parent.mkdir(parents=True, exist_ok=True)
        if self.csv_path.exists():
            self._conferir_cabecalho()
        else:
            with self.csv_path.open("w", newline="", encoding="utf-8-sig") as f:
                csv.writer(f, delimiter=";").writerow(CABECALHO)

    def _conferir_cabecalho(self) -> None:
        """Se o registro é de uma versão anterior, preserva e recomeça.

        Nunca reescreve nem descarta o histórico: renomeia com data e hora e
        abre um arquivo novo com o cabeçalho atual.
        """
        with self.csv_path.open(encoding="utf-8-sig") as f:
            atual = next(csv.reader(f, delimiter=";"), [])
        if atual == CABECALHO:
            return
        antigo = self.csv_path.with_name(
            f"{self.csv_path.stem}_ate_{datetime.now():%Y%m%d-%H%M%S}{self.csv_path.suffix}")
        self.csv_path.rename(antigo)
        with self.csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f, delimiter=";").writerow(CABECALHO)

    def gravar(self, resultado) -> None:
        d = asdict(resultado) if is_dataclass(resultado) else dict(resultado)
        d.setdefault("data_hora", datetime.now().isoformat(timespec="seconds"))
        linha = [_texto(d.get(c, "")) for c in CABECALHO]
        with self.csv_path.open("a", newline="", encoding="utf-8-sig") as f:
            csv.writer(f, delimiter=";").writerow(linha)
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(d, ensure_ascii=False, default=str) + "\n")


def _texto(valor) -> str:
    if isinstance(valor, (list, tuple)):
        return " | ".join(str(v) for v in valor)
    return "" if valor is None else str(valor)
