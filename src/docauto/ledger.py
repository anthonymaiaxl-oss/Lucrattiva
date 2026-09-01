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
    "travas", "avisos",
]


class Registro:
    def __init__(self, csv_path: str | Path, jsonl_path: str | Path):
        self.csv_path = Path(csv_path)
        self.jsonl_path = Path(jsonl_path)
        for p in (self.csv_path, self.jsonl_path):
            p.parent.mkdir(parents=True, exist_ok=True)
        if not self.csv_path.exists():
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
