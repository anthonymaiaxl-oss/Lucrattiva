"""Cópia segura para a pasta de destino. Nunca sobrescreve, nunca apaga."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


def sha256(caminho: str | Path, blocos: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(blocos), b""):
            h.update(bloco)
    return h.hexdigest()


def arquivar(origem: str | Path, pasta_destino: str | Path, nome: str,
             dry_run: bool = False) -> tuple[str, str]:
    """Copia origem -> pasta_destino/nome.

    Devolve (status, caminho_final):
      ARQUIVADO  — cópia nova criada
      DUPLICADO  — já existe arquivo idêntico (mesmo hash); nada foi feito
      RENOMEADO  — já existia arquivo diferente com o mesmo nome; salvo com sufixo
    """
    origem = Path(origem)
    destino_dir = Path(pasta_destino)
    alvo = destino_dir / nome
    hash_origem = sha256(origem)

    if alvo.exists():
        if sha256(alvo) == hash_origem:
            return "DUPLICADO", str(alvo)
        base, ext = alvo.stem, alvo.suffix
        for i in range(2, 100):
            candidato = destino_dir / f"{base}_{i:02d}{ext}"
            if not candidato.exists():
                alvo = candidato
                break
            if sha256(candidato) == hash_origem:
                return "DUPLICADO", str(candidato)
        status = "RENOMEADO"
    else:
        status = "ARQUIVADO"

    if dry_run:
        return status, str(alvo)
    destino_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origem, alvo)
    return status, str(alvo)


def mover_original(origem: str | Path, pasta: str | Path, dry_run: bool = False) -> str:
    origem, pasta = Path(origem), Path(pasta)
    alvo = pasta / origem.name
    for i in range(2, 100):
        if not alvo.exists():
            break
        alvo = pasta / f"{origem.stem}_{i:02d}{origem.suffix}"
    if not dry_run:
        pasta.mkdir(parents=True, exist_ok=True)
        shutil.move(str(origem), str(alvo))
    return str(alvo)
