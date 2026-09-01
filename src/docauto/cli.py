"""Linha de comando da automação.

    python -m docauto init
    python -m docauto validar
    python -m docauto processar --dry-run
    python -m docauto processar
    python -m docauto estrutura --ano 2026
    python -m docauto relatorio
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from collections import Counter
from pathlib import Path

from .config import caminho_projeto, carregar_config
from .confidence import AUTOMATICO, PENDENTE, REVISAO
from .empresas import Cadastro
from .pipeline import Processador
from .routing import pasta_empresa

SETORES_PADRAO = ["01 FISCAL", "02 CONTABIL", "03 DEPARTAMENTO PESSOAL",
                  "04 SOCIETARIO", "05 FINANCEIRO", "_PERMANENTE"]


def cmd_init(args) -> int:
    cfg = carregar_config(args.config)
    raiz = Path(cfg["_raiz"])
    origem_cfg = raiz / "config" / "config.example.yaml"
    destino_cfg = raiz / "config" / "config.yaml"
    if not destino_cfg.exists():
        shutil.copy2(origem_cfg, destino_cfg)
        print(f"criado {destino_cfg} — edite os caminhos antes de rodar")
    destino_csv = Path(caminho_projeto(cfg, cfg["cadastro"]["arquivo"]))
    if not destino_csv.exists():
        shutil.copy2(raiz / "data" / "empresas.exemplo.csv", destino_csv)
        print(f"criado {destino_csv} — substitua pelos seus clientes")
    for chave in ("entrada", "processados", "pendentes", "base_clientes"):
        caminho = cfg["pastas"].get(chave)
        if caminho:
            Path(caminho).mkdir(parents=True, exist_ok=True)
            print(f"pasta pronta: {caminho}")
    return 0


def cmd_validar(args) -> int:
    cfg = carregar_config(args.config)
    cadastro = Cadastro.carregar(caminho_projeto(cfg, cfg["cadastro"]["arquivo"]))
    erros = cadastro.validar()
    print(f"{len(cadastro.empresas)} empresa(s) no cadastro")
    for e in erros:
        print("  ERRO:", e)
    proc = Processador(cfg)
    if not proc.tabela.conferida:
        print("  AVISO: config/codigos_receita.yaml ainda está NAO_CONFERIDA "
              "(ver docs/03) — confira antes de ligar o arquivamento automático")
    print("cadastro OK" if not erros else f"{len(erros)} problema(s) a corrigir")
    return 1 if erros else 0


def cmd_estrutura(args) -> int:
    cfg = carregar_config(args.config)
    cadastro = Cadastro.carregar(caminho_projeto(cfg, cfg["cadastro"]["arquivo"]))
    base = cfg["pastas"]["base_clientes"]
    criadas = 0
    for e in cadastro.empresas:
        if not e.ativa:
            continue
        raiz_empresa = Path(pasta_empresa(e, base))
        for setor in SETORES_PADRAO:
            alvo = raiz_empresa / setor
            if setor != "_PERMANENTE" and args.ano:
                alvo = alvo / str(args.ano)
            if not args.dry_run:
                alvo.mkdir(parents=True, exist_ok=True)
            criadas += 1
        print(("[simulação] " if args.dry_run else "") + str(raiz_empresa))
    print(f"{criadas} pasta(s) garantida(s)")
    return 0


def cmd_processar(args) -> int:
    cfg = carregar_config(args.config)
    proc = Processador(cfg)
    resultados = proc.processar_pasta(args.entrada, dry_run=args.dry_run)
    if not resultados:
        print("nenhum arquivo na pasta de entrada")
        return 0
    for r in resultados:
        marca = {AUTOMATICO: "OK ", REVISAO: "REV", PENDENTE: "PEN"}.get(r.decisao, "???")
        print(f"[{marca}] {Path(r.arquivo_origem).name} -> {r.tipo} "
              f"{r.competencia} {r.empresa or '(empresa não identificada)'} "
              f"score={r.score}")
        for t in r.travas:
            print(f"        ! {t}")
        if r.destino:
            print(f"        -> {r.destino}")
    contagem = Counter(r.decisao for r in resultados)
    print("\nresumo:", dict(contagem),
          "\n(simulação — nada foi copiado)" if args.dry_run else "")
    return 0


def cmd_relatorio(args) -> int:
    cfg = carregar_config(args.config)
    caminho = Path(caminho_projeto(cfg, cfg["registro"]["csv"]))
    if not caminho.exists():
        print("nenhum registro ainda")
        return 0
    linhas = list(csv.DictReader(caminho.read_text(encoding="utf-8-sig").splitlines(),
                                 delimiter=";"))
    total = len(linhas)
    decisoes = Counter(l["decisao"] for l in linhas)
    tipos = Counter(l["tipo"] for l in linhas)
    motivos = Counter(t.split(":")[0].strip()
                      for l in linhas if l["travas"]
                      for t in l["travas"].split("|") if t.strip())
    print(f"documentos processados: {total}")
    for chave, qtd in decisoes.most_common():
        print(f"  {chave:24} {qtd:5}  {qtd/total:6.1%}")
    print("\npor tipo:")
    for chave, qtd in tipos.most_common():
        print(f"  {chave:24} {qtd:5}")
    if motivos:
        print("\nmotivos de pendência (atacar de cima para baixo):")
        for chave, qtd in motivos.most_common():
            print(f"  {chave:34} {qtd:5}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser("docauto", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", help="caminho do config.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="cria config, cadastro e pastas").set_defaults(func=cmd_init)
    sub.add_parser("validar", help="confere o cadastro de empresas").set_defaults(func=cmd_validar)

    s = sub.add_parser("estrutura", help="cria a árvore de pastas dos clientes")
    s.add_argument("--ano", type=int)
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_estrutura)

    s = sub.add_parser("processar", help="processa a pasta de entrada")
    s.add_argument("--entrada")
    s.add_argument("--dry-run", action="store_true", help="não copia nada, só mostra")
    s.set_defaults(func=cmd_processar)

    sub.add_parser("relatorio", help="resumo do que já foi processado").set_defaults(
        func=cmd_relatorio)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
