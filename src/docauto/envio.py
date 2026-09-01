"""Fila de envio ao Domínio Processos Express.

Dois modos, mesma fila e as mesmas travas:

  pasta_monitorada — a automação copia para a pasta que o Express varre e
                     o upload acontece sozinho;
  lote_manual      — a automação monta um lote pronto por competência e a
                     pessoa arrasta para o Express uma vez por dia.

O modo é uma linha do config. Trocar de um para o outro não muda mais nada —
é isso que permite começar a operar antes de a Thomson Reuters confirmar qual
mecanismo existe.

Estados de um item:
  PENDENTE   enfileirado pelo processamento, ainda não saiu
  ENVIADO    copiado para a pasta monitorada (ou para o lote)
  CONSUMIDO  sumiu da pasta monitorada => o Express pegou
  PARADO     continua na pasta monitorada além do prazo => alguém precisa olhar
  BLOQUEADO  não pode ser enviado (só via reenfileiramento manual)
"""
from __future__ import annotations

import csv
import shutil
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timedelta
from pathlib import Path

PENDENTE = "PENDENTE"
ENVIADO = "ENVIADO"
CONSUMIDO = "CONSUMIDO"
PARADO = "PARADO"
BLOQUEADO = "BLOQUEADO"


@dataclass
class Item:
    hash: str = ""                 # SHA-256 do documento: chave de idempotência
    arquivo: str = ""              # caminho do arquivo já arquivado no servidor
    nome: str = ""                 # nome padronizado
    empresa_id: str = ""
    empresa: str = ""
    cnpj: str = ""
    tipo: str = ""
    competencia: str = ""
    decisao: str = ""
    estado: str = PENDENTE
    enfileirado_em: str = ""
    enviado_em: str = ""
    confirmado_em: str = ""
    destino_envio: str = ""
    resultado_express: str = ""    # VINCULADA | MULTIPLA | NAO_ENCONTRADA
    observacao: str = ""


CABECALHO = [f.name for f in fields(Item)]


class FilaEnvio:
    """Fila persistida em CSV. Pequena, legível no Excel, sem banco de dados."""

    def __init__(self, arquivo: str | Path):
        self.arquivo = Path(arquivo)
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        self.itens: list[Item] = []
        self._carregar()

    def _carregar(self) -> None:
        if not self.arquivo.exists():
            return
        texto = self.arquivo.read_text(encoding="utf-8-sig")
        for linha in csv.DictReader(texto.splitlines(), delimiter=";"):
            self.itens.append(Item(**{c: (linha.get(c) or "") for c in CABECALHO}))

    def salvar(self) -> None:
        with self.arquivo.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=CABECALHO, delimiter=";")
            w.writeheader()
            for item in self.itens:
                w.writerow(asdict(item))

    # ------------------------------------------------------------------ #

    def por_hash(self, hash_doc: str) -> Item | None:
        return next((i for i in self.itens if i.hash == hash_doc), None)

    def enfileirar(self, item: Item) -> str:
        """Idempotente: o mesmo documento nunca entra duas vezes na fila.

        É esta linha que impede o Express de receber a mesma guia cinco vezes
        porque alguém reprocessou a pasta de entrada.
        """
        existente = self.por_hash(item.hash)
        if existente:
            return f"JA_NA_FILA:{existente.estado}"
        item.enfileirado_em = datetime.now().isoformat(timespec="seconds")
        self.itens.append(item)
        self.salvar()
        return "ENFILEIRADO"

    def pendentes(self, empresas: list[str] | None = None,
                  limite: int | None = None) -> list[Item]:
        fila = [i for i in self.itens if i.estado == PENDENTE]
        if empresas:
            fila = [i for i in fila if i.empresa_id in empresas]
        fila.sort(key=lambda i: (i.competencia, i.empresa_id, i.nome))
        return fila[:limite] if limite else fila

    # ------------------------------------------------------------------ #

    def enviar(self, cfg_envio: dict, dry_run: bool = False) -> list[tuple[Item, str]]:
        """Copia os pendentes para o destino do modo configurado."""
        modo = cfg_envio.get("modo", "lote_manual")
        empresas = [str(e) for e in cfg_envio.get("empresas_piloto", []) if str(e).strip()]
        limite = cfg_envio.get("limite_por_rodada") or None
        fila = self.pendentes(empresas, limite)
        resultados: list[tuple[Item, str]] = []

        for item in fila:
            origem = Path(item.arquivo)
            if not origem.exists():
                item.estado = BLOQUEADO
                item.observacao = "arquivo arquivado não encontrado no servidor"
                resultados.append((item, "BLOQUEADO"))
                continue

            destino_dir = self._destino(modo, cfg_envio, item)
            alvo = destino_dir / item.nome
            if alvo.exists():
                item.observacao = "já existe arquivo com este nome no destino"
                resultados.append((item, "JA_NO_DESTINO"))
                continue

            if not dry_run:
                destino_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origem, alvo)
                item.estado = ENVIADO
                item.enviado_em = datetime.now().isoformat(timespec="seconds")
                item.destino_envio = str(alvo)
            resultados.append((item, "ENVIADO" if not dry_run else "SIMULADO"))

        if not dry_run and resultados:
            self.salvar()
        return resultados

    def _destino(self, modo: str, cfg_envio: dict, item: Item) -> Path:
        if modo == "pasta_monitorada":
            return Path(cfg_envio["pasta_monitorada"])
        # lote_manual: uma pasta por competência, pronta para arrastar
        return Path(cfg_envio["pasta_lote"]) / (item.competencia or "SEM_COMPETENCIA")

    # ------------------------------------------------------------------ #

    def conciliar(self, cfg_envio: dict) -> dict[str, int]:
        """Confere o que o Express já consumiu.

        Regra: no modo pasta_monitorada, arquivo que sumiu da pasta = consumido
        pelo Express. Arquivo que continua lá além do prazo vira PARADO e
        aparece no status — é assim que se descobre que o Express parou de
        varrer sem ninguém perceber.
        """
        modo = cfg_envio.get("modo", "lote_manual")
        horas = int(cfg_envio.get("horas_para_alerta", 4))
        limite = datetime.now() - timedelta(hours=horas)
        mudou = False

        for item in self.itens:
            if item.estado not in (ENVIADO, PARADO) or not item.destino_envio:
                continue
            if modo != "pasta_monitorada":
                continue
            if not Path(item.destino_envio).exists():
                item.estado = CONSUMIDO
                item.confirmado_em = datetime.now().isoformat(timespec="seconds")
                item.observacao = "arquivo removido da pasta monitorada pelo Express"
                mudou = True
            elif item.enviado_em and datetime.fromisoformat(item.enviado_em) < limite:
                if item.estado != PARADO:
                    item.estado = PARADO
                    item.observacao = f"parado na pasta monitorada há mais de {horas}h"
                    mudou = True
        if mudou:
            self.salvar()
        return self.resumo()

    def resumo(self) -> dict[str, int]:
        contagem: dict[str, int] = {}
        for item in self.itens:
            contagem[item.estado] = contagem.get(item.estado, 0) + 1
        return contagem

    # ------------------------------------------------------------------ #

    RESULTADOS = {
        "SIM": "VINCULADA", "S": "VINCULADA", "VINCULADA": "VINCULADA",
        "OK": "VINCULADA", "1": "VINCULADA",
        "MULTIPLA": "MULTIPLA", "MULTIPLAS": "MULTIPLA", "ESCOLHI": "MULTIPLA",
        "VARIAS": "MULTIPLA", "M": "MULTIPLA",
        "NAO": "NAO_ENCONTRADA", "N": "NAO_ENCONTRADA",
        "NAO ENCONTRADA": "NAO_ENCONTRADA", "PENDENTE": "NAO_ENCONTRADA",
        "0": "NAO_ENCONTRADA",
    }

    def confirmar_lote(self, pasta: str | Path, dry_run: bool = False,
                       mover: bool = True) -> list[tuple[Item, str]]:
        """Fecha o ciclo do modo lote a partir da planilha preenchida.

        Em produto web não existe pasta para observar: quem diz se o Express
        vinculou é a pessoa que subiu o lote. A planilha _CONFERIR.csv é esse
        retorno, e sem ela a fila ficaria em ENVIADO para sempre — ou seja,
        ninguém saberia o que realmente entrou no Onvio.
        """
        pasta = Path(pasta)
        planilha = pasta / "_CONFERIR.csv"
        if not planilha.exists():
            raise FileNotFoundError(f"planilha de conferência não encontrada: {planilha}")

        linhas = list(csv.DictReader(
            planilha.read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))
        por_nome = {i.nome: i for i in self.itens}
        agora = datetime.now().isoformat(timespec="seconds")
        resultados: list[tuple[Item, str]] = []
        enviados_dir = pasta / "_ENVIADOS"

        for linha in linhas:
            nome = (linha.get("arquivo") or "").strip()
            item = por_nome.get(nome)
            if not item:
                continue
            bruto = (linha.get("tarefa_vinculada") or "").strip().upper()
            if not bruto:
                resultados.append((item, "SEM_RESPOSTA"))
                continue
            resultado = self.RESULTADOS.get(bruto)
            if not resultado:
                resultados.append((item, f"RESPOSTA_NAO_RECONHECIDA:{bruto}"))
                continue

            item.resultado_express = resultado
            item.observacao = (linha.get("observacao") or "").strip()
            if resultado == "NAO_ENCONTRADA":
                item.estado = PARADO
                if not item.observacao:
                    item.observacao = "Express não encontrou tarefa — tratar dentro do Onvio"
            else:
                item.estado = CONSUMIDO
                item.confirmado_em = agora
                if resultado == "MULTIPLA" and not item.observacao:
                    item.observacao = "exigiu escolha manual da tarefa"
                if mover and not dry_run:
                    origem = pasta / nome
                    if origem.exists():
                        enviados_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(origem), str(enviados_dir / nome))
            resultados.append((item, resultado))

        if not dry_run:
            self.salvar()
        return resultados

    def metricas_express(self) -> dict[str, int]:
        """Números que decidem o próximo passo do projeto."""
        contagem = {"VINCULADA": 0, "MULTIPLA": 0, "NAO_ENCONTRADA": 0, "SEM_RESPOSTA": 0}
        for item in self.itens:
            chave = item.resultado_express or "SEM_RESPOSTA"
            contagem[chave] = contagem.get(chave, 0) + 1
        return contagem

    def reenfileirar(self, hash_doc: str) -> bool:
        """Devolve um item para PENDENTE (uso manual, após corrigir o problema)."""
        item = self.por_hash(hash_doc)
        if not item:
            return False
        item.estado = PENDENTE
        item.enviado_em = ""
        item.destino_envio = ""
        item.observacao = "reenfileirado manualmente"
        self.salvar()
        return True


def escrever_conferencia(itens: list[Item], pasta: Path) -> Path:
    """Planilha de conferência que acompanha o lote manual."""
    pasta.mkdir(parents=True, exist_ok=True)
    alvo = pasta / "_CONFERIR.csv"
    with alvo.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["arquivo", "empresa", "cnpj", "tipo", "competencia",
                    "conferido", "tarefa_vinculada", "observacao"])
        for i in itens:
            w.writerow([i.nome, i.empresa, i.cnpj, i.tipo, i.competencia, "", "", ""])
    return alvo
