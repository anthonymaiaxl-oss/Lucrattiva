"""Orquestração: entrada -> leitura -> extração -> classificação -> empresa ->
confiança -> arquivamento (ou fila de pendências) -> registro."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from . import archive, envio, routing, textio
from .classify import classificar
from .confidence import AUTOMATICO, PENDENTE, REVISAO, avaliar
from .config import caminho_projeto, carregar_config, destinos, entradas
from .empresas import Cadastro
from .envio import FilaEnvio, Item
from .espelho import Espelho, FilaEspelho
from .ledger import Registro
from .normalize import extrair_campos, formatar_cnpj
from .templates import carregar_codigos, carregar_templates


@dataclass
class Resultado:
    data_hora: str = ""
    arquivo_origem: str = ""
    empresa_id: str = ""
    empresa: str = ""
    cnpj: str = ""
    tipo: str = ""
    subtipo: str = ""
    competencia: str = ""
    score: int = 0
    decisao: str = PENDENTE
    status_arquivo: str = ""
    destino: str = ""
    hash_documento: str = ""
    envio: str = ""
    copias: list[str] = field(default_factory=list)
    travas: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    motivos_classificacao: list[str] = field(default_factory=list)
    candidatos: list[str] = field(default_factory=list)
    sugestoes_empresa: list[str] = field(default_factory=list)
    origem_texto: str = ""


class Processador:
    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or carregar_config()
        raiz = self.cfg["_raiz"]
        self.templates = carregar_templates(Path(raiz) / "config" / "templates")
        self.tabela = carregar_codigos(Path(raiz) / "config" / "codigos_receita.yaml")
        self.cadastro = Cadastro.carregar(
            caminho_projeto(self.cfg, self.cfg["cadastro"]["arquivo"]))
        self.registro = Registro(
            caminho_projeto(self.cfg, self.cfg["registro"]["csv"]),
            caminho_projeto(self.cfg, self.cfg["registro"]["jsonl"]))
        self.fila = FilaEnvio(caminho_projeto(
            self.cfg, self.cfg.get("envio", {}).get("fila", "data/registro/envio.csv")))
        self.destinos = destinos(self.cfg)
        self.espelho = FilaEspelho(caminho_projeto(
            self.cfg, self.cfg.get("espelho", "data/registro/espelho.csv")))

    # ------------------------------------------------------------------ #

    def processar_pasta(self, entrada: str | None = None, dry_run: bool = False,
                        hoje: date | None = None) -> list[Resultado]:
        pastas = [entrada] if entrada else entradas(self.cfg)
        ignorar = {Path(self.cfg["pastas"]["processados"]).name,
                   "_PENDENTES", "_LOGS", "_ENVIADOS"}
        resultados = []
        for caminho_pasta in pastas:
            pasta = Path(caminho_pasta)
            if not pasta.exists():
                continue
            for arquivo in sorted(pasta.rglob("*")):
                if not arquivo.is_file() or set(arquivo.parts) & ignorar:
                    continue
                resultados.append(self.processar_arquivo(arquivo, dry_run=dry_run, hoje=hoje))
        return resultados

    def processar_arquivo(self, caminho: str | Path, dry_run: bool = False,
                          hoje: date | None = None) -> Resultado:
        caminho = Path(caminho)
        proc = self.cfg["processamento"]
        r = Resultado(data_hora=datetime.now().isoformat(timespec="seconds"),
                      arquivo_origem=str(caminho))
        ext = caminho.suffix.lower()

        if ext in proc.get("extensoes_avisar", []):
            r.decisao = PENDENTE
            r.travas = ["FORMATO_NAO_ACEITO_PELO_EXPRESS: converter .doc/.docx em PDF"]
            return self._finalizar(r, caminho, None, dry_run)
        if ext not in proc["extensoes"]:
            r.decisao = PENDENTE
            r.travas = [f"EXTENSAO_NAO_SUPORTADA: {ext}"]
            return self._finalizar(r, caminho, None, dry_run)

        texto, origem = textio.ler(caminho, proc.get("ocr_habilitado", False),
                                   proc.get("ocr_idioma", "por"))
        ex = extrair_campos(texto, origem)
        r.origem_texto = ex.origem_texto

        cls = classificar(ex, self.templates, self.tabela,
                          self.cfg["classificacao"]["score_minimo_tipo"],
                          self.cfg["classificacao"]["margem_desempate"])
        cls.campos_faltando = self._campos_faltando(cls, ex)

        resolucao = self.cadastro.resolver(
            ex, pasta_origem=str(caminho.parent),
            limiar_forte=self.cfg["empresas"]["similaridade_forte"],
            limiar_fraco=self.cfg["empresas"]["similaridade_fraca"])

        av = avaliar(ex, resolucao, cls, self.cfg, hoje=hoje)

        r.tipo = cls.tipo
        r.subtipo = cls.subtipo or ""
        r.competencia = ex.competencia.valor or ""
        r.score = av.score
        r.decisao = av.decisao
        r.travas = av.travas
        r.avisos = cls.avisos + av.detalhe
        r.motivos_classificacao = cls.motivos
        r.candidatos = [f"{c.tipo}:{c.score}" for c in cls.candidatos]
        r.sugestoes_empresa = resolucao.sugestoes
        r.cnpj = formatar_cnpj(ex.cnpj) if ex.cnpj else ""
        if resolucao.empresa:
            r.empresa_id = resolucao.empresa.id
            r.empresa = resolucao.empresa.razao_social

        if av.decisao in (AUTOMATICO, REVISAO) and resolucao.empresa:
            template = self.templates.get(cls.tipo)
            nome = routing.montar_nome(resolucao.empresa, cls, ex.competencia.valor,
                                       caminho.suffix, self.cfg)
            r.hash_documento = archive.sha256(caminho)
            self._arquivar_em_todos(r, caminho, resolucao.empresa, cls,
                                    ex.competencia.valor, template, nome, dry_run)
            if r.destino and not dry_run:
                r.envio = self._enfileirar_envio(r, resolucao.empresa, nome)

        return self._finalizar(r, caminho, ex, dry_run)

    # ------------------------------------------------------------------ #

    def _arquivar_em_todos(self, r: Resultado, caminho: Path, empresa, cls,
                           competencia: str, template, nome: str, dry_run: bool) -> None:
        """Arquiva no destino principal e espelha nos demais.

        Falha em destino secundário (Dropbox fora do ar, rede caída) não derruba
        o documento: ele já está no principal, e a cópia que faltou entra na
        fila de espelho para ser refeita por `docauto espelhar`.
        """
        for destino_cfg in self.destinos:
            pasta = routing.montar_caminho(
                empresa, cls, competencia, self.cfg, destino_cfg["raiz"],
                setor=(template.setor if template else "FISCAL"),
                grupo=(template.grupo if template else "GUIAS"))

            if routing.caminho_muito_longo(pasta, nome,
                                           self.cfg["estrutura"]["limite_caminho"]):
                if destino_cfg["principal"]:
                    r.decisao = PENDENTE
                    r.travas.append(
                        "CAMINHO_MUITO_LONGO: encurtar nome da pasta da empresa")
                    return
                r.avisos.append(f"CAMINHO_MUITO_LONGO em {destino_cfg['nome']}")
                continue

            try:
                status, final = archive.arquivar(caminho, pasta, nome, dry_run)
            except OSError as erro:
                if destino_cfg["principal"]:
                    r.decisao = PENDENTE
                    r.travas.append(f"DESTINO_INDISPONIVEL: {destino_cfg['nome']} ({erro})")
                    return
                r.avisos.append(f"ESPELHO_PENDENTE: {destino_cfg['nome']} ({erro})")
                if not dry_run:
                    self.espelho.registrar(Espelho(
                        hash=r.hash_documento, origem=r.destino or str(caminho),
                        destino_nome=destino_cfg["nome"], pasta_destino=pasta,
                        nome=nome, erro=str(erro)))
                continue

            if destino_cfg["principal"]:
                r.status_arquivo, r.destino = status, final
            else:
                r.copias.append(f"{destino_cfg['nome']}={final}")

    def _enfileirar_envio(self, r: Resultado, empresa, nome: str) -> str:
        """Coloca o documento arquivado na fila do Express.

        Só entra o que foi efetivamente arquivado. Documento em pendência nunca
        é enviado — o Express receberia um documento que o próprio escritório
        ainda não confirmou de quem é.
        """
        cfg_envio = self.cfg.get("envio", {})
        if not cfg_envio.get("habilitado"):
            return ""
        if r.decisao == REVISAO and not cfg_envio.get("incluir_revisao", True):
            return "NAO_ENVIADO:apenas_automatico"
        piloto = [str(e) for e in cfg_envio.get("empresas_piloto", []) if str(e).strip()]
        if piloto and r.empresa_id not in piloto:
            return "NAO_ENVIADO:fora_do_piloto"
        return self.fila.enfileirar(Item(
            hash=r.hash_documento, arquivo=r.destino, nome=nome,
            empresa_id=r.empresa_id, empresa=r.empresa, cnpj=r.cnpj,
            tipo=r.tipo, competencia=r.competencia, decisao=r.decisao))

    def _campos_faltando(self, cls, ex) -> list[str]:
        template = self.templates.get(cls.tipo)
        if not template:
            return []
        presente = {
            "cnpj": bool(ex.cnpjs),
            "competencia": bool(ex.competencia.valor),
            "valor": ex.valor is not None,
            "vencimento": bool(ex.vencimento),
            "codigo_receita": bool(ex.codigos_receita),
            "razao_social": bool(ex.razoes),
        }
        return [c for c in template.campos_obrigatorios if not presente.get(c, True)]

    def _finalizar(self, r: Resultado, caminho: Path, ex, dry_run: bool) -> Resultado:
        if r.decisao == PENDENTE:
            r.status_arquivo, r.destino = self._para_pendencias(r, caminho, dry_run)
        elif self.cfg["processamento"]["modo_original"] == "mover" and not dry_run:
            archive.mover_original(caminho, self.cfg["pastas"]["processados"])
        self.registro.gravar(r)
        return r

    def _para_pendencias(self, r: Resultado, caminho: Path, dry_run: bool):
        motivo = (r.travas[0].split(":")[0] if r.travas else "SEM_MOTIVO")
        pasta = Path(self.cfg["pastas"]["pendentes"]) / motivo
        status, destino = archive.arquivar(caminho, pasta, caminho.name, dry_run)
        if not dry_run:
            laudo = Path(destino).with_suffix(Path(destino).suffix + ".laudo.json")
            laudo.write_text(json.dumps({
                "arquivo": str(caminho), "motivo_principal": motivo,
                "travas": r.travas, "tipo_provavel": r.tipo,
                "candidatos": r.candidatos, "competencia": r.competencia,
                "cnpj": r.cnpj, "empresa": r.empresa,
                "sugestoes_empresa": r.sugestoes_empresa,
                "motivos_classificacao": r.motivos_classificacao,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        return status, destino
