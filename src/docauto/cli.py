"""Linha de comando da automação.

    python -m docauto init
    python -m docauto validar
    python -m docauto processar --dry-run
    python -m docauto processar
    python -m docauto estrutura --ano 2026
    python -m docauto relatorio
    python -m docauto enviar --dry-run
    python -m docauto enviar
    python -m docauto envio-status
    python -m docauto envio-confirmar --lote D:/CONTABIL/LOTE_EXPRESS/2026-08
    python -m docauto diagnosticar --entrada C:/amostras --texto C:/amostras/_texto
    python -m docauto espelhar
    python -m docauto doutor
    python -m docauto onvio-conferir --empresas data/onvio/empresas.csv
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from collections import Counter
from pathlib import Path

from . import textio
from .classify import classificar, pontuar_todos
from .config import caminho_projeto, carregar_config, destinos
from .doutor import ERRO, OK, resumo, verificar
from .espelho import FilaEspelho
from .onvio import (conferir_empresas, conferir_tarefas, escrever_cadastro,
                    gerar_cadastro, ler_planilha)
from .normalize import extrair_campos, formatar_cnpj
from .confidence import AUTOMATICO, PENDENTE, REVISAO
from .empresas import Cadastro
from .envio import PARADO, FilaEnvio, escrever_conferencia
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


MARCAS = {"OK": "OK  ", "AVISO": "!   ", "ERRO": "ERRO"}


def cmd_onvio_conferir(args) -> int:
    """Cruza as exportações do Onvio com o que a automação conhece."""
    cfg = carregar_config(args.config)
    linhas = ler_planilha(args.empresas)
    print(f"exportação de empresas: {len(linhas)} linha(s), "
          f"colunas: {', '.join(list(linhas[0].keys())[:8]) if linhas else '-'}")

    if args.gerar_cadastro:
        registros = gerar_cadastro(linhas)
        alvo = escrever_cadastro(registros, args.gerar_cadastro)
        print(f"\n{len(registros)} empresa(s) escritas em {alvo}")
        print("confira NOME_CURTO e REGIME_TRIBUTARIO antes de usar; "
              "os IDs foram gerados em sequência e não devem mudar depois")
        return 0

    try:
        cadastro = Cadastro.carregar(caminho_projeto(cfg, cfg["cadastro"]["arquivo"]))
    except FileNotFoundError:
        print("\ncadastro ainda não existe — rode com --gerar-cadastro "
              "para criá-lo a partir desta exportação")
        return 1

    conf = conferir_empresas(linhas, cadastro)
    print(f"\nempresas: {conf.no_onvio} no Onvio, {conf.no_cadastro} no cadastro, "
          f"{conf.coincidentes} conferem")
    if conf.divergencias:
        print(f"\n{len(conf.divergencias)} divergência(s):")
        for d in conf.divergencias[:40]:
            print(f"  [{d.tipo:24}] {d.chave}  {d.detalhe}")
            if d.acao:
                print(f"      -> {d.acao}")
        if len(conf.divergencias) > 40:
            print(f"  ... e mais {len(conf.divergencias) - 40}")
    else:
        print("nenhuma divergência de empresa")

    if args.tarefas:
        proc_templates = Processador(cfg).templates
        tarefas = conferir_tarefas(ler_planilha(args.tarefas), proc_templates)
        print(f"\ntarefas/obrigações: {tarefas.total} linha(s)")
        for tipo, qtd in sorted(tarefas.por_template.items(), key=lambda x: -x[1]):
            print(f"  {tipo:10} {qtd:5} obrigação(ões) no Onvio")
        if tarefas.templates_sem_tarefa:
            print("\ntemplates SEM obrigação correspondente no Onvio:")
            for tipo in tarefas.templates_sem_tarefa:
                print(f"  {tipo}")
            print("  -> documento desse tipo vai ser classificado certo, mas o "
                  "Express devolve 'tarefa não encontrada'")
        if tarefas.sem_template:
            print(f"\nobrigações do Onvio SEM template ({len(tarefas.sem_template)}):")
            for nome in tarefas.sem_template[:25]:
                print(f"  {nome}")
            if len(tarefas.sem_template) > 25:
                print(f"  ... e mais {len(tarefas.sem_template) - 25}")
            print("  -> são candidatas a template novo (docs/13), na ordem de volume")

    return 1 if conf.divergencias else 0


def cmd_doutor(args) -> int:
    """Diz o que falta para o fluxo rodar NESTE computador."""
    cfg = carregar_config(args.config)
    try:
        proc = Processador(cfg)
    except FileNotFoundError as erro:
        print(f"[ERRO] {erro}")
        proc = None

    checagens = verificar(cfg, proc)
    for c in checagens:
        linha = f"[{MARCAS.get(c.nivel, c.nivel)}] {c.item:22} {c.detalhe}"
        print(linha)
        if c.acao:
            print(f"         -> {c.acao}")

    erros, avisos = resumo(checagens)
    print()
    if erros:
        print(f"{erros} erro(s) e {avisos} aviso(s). "
              "Corrija os erros antes de processar documentos.")
        return 1
    print(f"ambiente pronto ({avisos} aviso(s)).")
    return 0


def cmd_diagnosticar(args) -> int:
    """Mostra POR QUE cada documento foi classificado assim. É a ferramenta de
    calibração dos templates — ver docs/13."""
    cfg = carregar_config(args.config)
    proc = Processador(cfg)
    pasta = Path(args.entrada)
    arquivos = [a for a in sorted(pasta.rglob("*")) if a.is_file()]
    if not arquivos:
        print(f"nenhum arquivo em {pasta}")
        return 1
    saida_texto = Path(args.texto) if args.texto else None
    if saida_texto:
        saida_texto.mkdir(parents=True, exist_ok=True)

    for arquivo in arquivos:
        texto, origem = textio.ler(arquivo,
                                   cfg["processamento"].get("ocr_habilitado", False),
                                   cfg["processamento"].get("ocr_idioma", "por"))
        ex = extrair_campos(texto, origem)
        print("=" * 78)
        print(f"{arquivo.name}")
        print(f"  texto......: {ex.origem_texto}, {len(ex.texto_norm)} caracteres")
        if not ex.texto_norm.strip():
            print("  SEM TEXTO — PDF é imagem. Ligue o OCR (Fase 2) para calibrar este.")
            continue

        print(f"  cnpj.......: {formatar_cnpj(ex.cnpj) if ex.cnpj else '-'}"
              + (f"   inválidos: {ex.cnpjs_invalidos}" if ex.cnpjs_invalidos else ""))
        print(f"  competência: {ex.competencia.valor or '-'} ({ex.competencia.fonte})")
        print(f"  valor......: {ex.valor if ex.valor is not None else '-'}"
              f"   vencimento: {ex.vencimento or '-'}")
        print(f"  códigos....: {ex.codigos_receita or '-'}"
              + (f"  -> {[proc.tabela.tributo(c) for c in ex.codigos_receita]}"
                 if ex.codigos_receita else ""))
        print(f"  razões.....: {ex.razoes[:2] or '-'}")

        print("  templates:")
        for cand in pontuar_todos(ex, proc.templates, proc.tabela)[:args.top]:
            t = proc.templates[cand.tipo]
            ausentes = [k.termo for k in t.principais
                        if not k.encontrado(ex.texto_norm, ex.texto_caixa)]
            print(f"    {cand.tipo:8} {cand.score:3}/{cand.maximo:3} ({cand.relativo:3}%)")
            for motivo in cand.motivos:
                print(f"       . {motivo}")
            if ausentes:
                print(f"       - principais ausentes: {', '.join(ausentes[:5])}")

        cls = classificar(ex, proc.templates, proc.tabela,
                          cfg["classificacao"]["score_minimo_tipo"],
                          cfg["classificacao"]["margem_desempate"])
        resolucao = proc.cadastro.resolver(ex, pasta_origem=str(arquivo.parent))
        print(f"  => tipo {cls.tipo}"
              + (f"/{cls.subtipo}" if cls.subtipo else "")
              + f"   empresa: {resolucao.empresa.id if resolucao.empresa else '-'}"
              f" ({resolucao.nivel})")
        if cls.motivos:
            print(f"     {cls.motivos[-1]}")

        if saida_texto:
            alvo = saida_texto / f"{arquivo.stem}.txt"
            alvo.write_text(ex.texto_norm, encoding="utf-8")
        if args.linhas:
            print("  primeiras linhas do texto lido:")
            for linha in ex.texto_norm.splitlines()[:args.linhas]:
                if linha.strip():
                    print(f"    | {linha[:100]}")

    if saida_texto:
        print("=" * 78)
        print(f"texto normalizado de cada documento salvo em {saida_texto}")
        print("é dele que saem as palavras-chave dos templates — ver docs/13")
    return 0


def cmd_espelhar(args) -> int:
    cfg = carregar_config(args.config)
    fila = FilaEspelho(caminho_projeto(cfg, cfg.get("espelho", "data/registro/espelho.csv")))
    if not fila.pendentes():
        print("nenhuma cópia pendente")
        return 0
    for item, status in fila.refazer(dry_run=args.dry_run):
        print(f"[{status:18}] {item.destino_nome}  {item.nome}"
              + (f"  ({item.erro})" if item.erro else ""))
    restantes = len(fila.pendentes())
    print(f"\n{restantes} cópia(s) ainda pendente(s)"
          + ("  (simulação)" if args.dry_run else ""))
    return 0


def _fila(cfg) -> FilaEnvio:
    return FilaEnvio(caminho_projeto(cfg, cfg.get("envio", {}).get(
        "fila", "data/registro/envio.csv")))


def cmd_enviar(args) -> int:
    cfg = carregar_config(args.config)
    envio = cfg.get("envio", {})
    if not envio.get("habilitado"):
        print("envio desligado (envio.habilitado: false no config) — ver docs/11")
        return 1
    modo = envio.get("modo", "lote_manual")
    if modo == "pasta_monitorada" and not envio.get("pasta_monitorada"):
        print("ERRO: modo pasta_monitorada exige envio.pasta_monitorada preenchido")
        return 1

    fila = _fila(cfg)
    resultados = fila.enviar(envio, dry_run=args.dry_run)
    if not resultados:
        print("nada pendente para enviar")
        return 0

    enviados = []
    for item, status in resultados:
        print(f"[{status:12}] {item.nome}  {item.empresa} {item.competencia}"
              + (f"  ({item.observacao})" if item.observacao else ""))
        if status in ("ENVIADO", "SIMULADO"):
            enviados.append(item)

    if modo == "lote_manual" and enviados and not args.dry_run:
        por_competencia: dict[str, list] = {}
        for item in enviados:
            por_competencia.setdefault(item.competencia or "SEM_COMPETENCIA", []).append(item)
        for competencia, itens in por_competencia.items():
            planilha = escrever_conferencia(
                itens, Path(envio["pasta_lote"]) / competencia)
            print(f"planilha de conferência: {planilha}")

    print(f"\n{len(enviados)} documento(s) "
          + ("simulados" if args.dry_run else f"prontos em modo {modo}"))
    if modo == "lote_manual" and not args.dry_run:
        print("próximo passo: abrir o Express e subir a pasta do lote")
    return 0


def cmd_envio_confirmar(args) -> int:
    cfg = carregar_config(args.config)
    fila = _fila(cfg)
    try:
        resultados = fila.confirmar_lote(args.lote, dry_run=args.dry_run,
                                         mover=not args.manter)
    except FileNotFoundError as erro:
        print(f"ERRO: {erro}")
        print("dica: a planilha é criada por 'docauto enviar' no modo lote_manual")
        return 1
    if not resultados:
        print("nenhuma linha da planilha corresponde a documento da fila")
        return 0

    for item, resultado in resultados:
        print(f"[{resultado:24}] {item.nome}  {item.empresa}")
    sem_resposta = sum(1 for _, r in resultados if r == "SEM_RESPOSTA")
    nao_reconhecidas = [r for _, r in resultados if r.startswith("RESPOSTA_NAO_RECONHECIDA")]
    if sem_resposta:
        print(f"\n{sem_resposta} linha(s) sem resposta em 'tarefa_vinculada' — "
              "preencha SIM, MULTIPLA ou NAO e rode de novo")
    if nao_reconhecidas:
        print(f"{len(nao_reconhecidas)} resposta(s) não reconhecida(s): "
              "use SIM, MULTIPLA ou NAO")
    if args.dry_run:
        print("\n(simulação — a fila não foi alterada)")
    return 0


def cmd_envio_status(args) -> int:
    cfg = carregar_config(args.config)
    fila = _fila(cfg)
    resumo = fila.conciliar(cfg.get("envio", {}))
    if not fila.itens:
        print("fila de envio vazia")
        return 0
    total = len(fila.itens)
    print(f"fila de envio: {total} documento(s)")
    for estado, qtd in sorted(resumo.items(), key=lambda x: -x[1]):
        print(f"  {estado:12} {qtd:5}  {qtd/total:6.1%}")
    metricas = fila.metricas_express()
    respondidos = sum(v for k, v in metricas.items() if k != "SEM_RESPOSTA")
    if respondidos:
        print("\nresultado no Express (dos que voltaram conferidos):")
        for chave in ("VINCULADA", "MULTIPLA", "NAO_ENCONTRADA"):
            qtd = metricas.get(chave, 0)
            print(f"  {chave:16} {qtd:5}  {qtd/respondidos:6.1%}")
        print("  (MULTIPLA alto = o gargalo é escolher a tarefa, não subir o arquivo)")

    parados = [i for i in fila.itens if i.estado == PARADO]
    if parados:
        print("\nPARADOS — exigem ação dentro do Onvio:")
        for item in parados[:20]:
            motivo = item.observacao or "sem confirmação após o prazo"
            print(f"  {item.nome}  ({motivo})")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser("docauto", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", help="caminho do config.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="cria config, cadastro e pastas").set_defaults(func=cmd_init)
    sub.add_parser("validar", help="confere o cadastro de empresas").set_defaults(func=cmd_validar)
    s = sub.add_parser("onvio-conferir",
                       help="cruza a exportação do Onvio com o cadastro e os templates")
    s.add_argument("--empresas", required=True, help="exportação de empresas (CSV/XLSX)")
    s.add_argument("--tarefas", help="exportação de tarefas/obrigações (CSV/XLSX)")
    s.add_argument("--gerar-cadastro", metavar="DESTINO",
                   help="cria data/empresas.csv a partir da exportação")
    s.set_defaults(func=cmd_onvio_conferir)

    sub.add_parser("doutor",
                   help="verifica pastas, permissões, leitores e destinos").set_defaults(
        func=cmd_doutor)

    s = sub.add_parser("estrutura", help="cria a árvore de pastas dos clientes")
    s.add_argument("--ano", type=int)
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_estrutura)

    s = sub.add_parser("diagnosticar",
                       help="mostra por que cada documento foi classificado assim")
    s.add_argument("--entrada", required=True, help="pasta com documentos de amostra")
    s.add_argument("--texto", help="pasta onde salvar o texto lido de cada documento")
    s.add_argument("--top", type=int, default=3, help="quantos templates detalhar")
    s.add_argument("--linhas", type=int, default=0,
                   help="mostrar as N primeiras linhas do texto lido")
    s.set_defaults(func=cmd_diagnosticar)

    s = sub.add_parser("espelhar", help="refaz as cópias secundárias que falharam")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_espelhar)

    s = sub.add_parser("processar", help="processa a pasta de entrada")
    s.add_argument("--entrada")
    s.add_argument("--dry-run", action="store_true", help="não copia nada, só mostra")
    s.set_defaults(func=cmd_processar)

    sub.add_parser("relatorio", help="resumo do que já foi processado").set_defaults(
        func=cmd_relatorio)

    s = sub.add_parser("enviar", help="envia a fila ao Express (lote ou pasta monitorada)")
    s.add_argument("--dry-run", action="store_true", help="não copia nada, só mostra")
    s.set_defaults(func=cmd_enviar)

    s = sub.add_parser("envio-confirmar",
                       help="fecha o ciclo do lote a partir da planilha _CONFERIR.csv")
    s.add_argument("--lote", required=True, help="pasta do lote (ex.: .../LOTE_EXPRESS/2026-08)")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--manter", action="store_true",
                   help="não mover os confirmados para _ENVIADOS")
    s.set_defaults(func=cmd_envio_confirmar)

    sub.add_parser("envio-status",
                   help="o que já foi consumido pelo Express e o que travou").set_defaults(
        func=cmd_envio_status)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as erro:
        print(f"ERRO: {erro}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
