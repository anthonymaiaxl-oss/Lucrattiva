"""Testes do núcleo. Rodar: python -m unittest discover -s tests -t . """
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import yaml  # noqa: E402

from docauto import routing  # noqa: E402
from docauto.archive import arquivar  # noqa: E402
from docauto.classify import classificar  # noqa: E402
from docauto.confidence import AUTOMATICO, PENDENTE, REVISAO  # noqa: E402
from docauto.empresas import Cadastro  # noqa: E402
from docauto.normalize import (cnpj_valido, extrair_campos,  # noqa: E402
                               extrair_competencia, normalizar)
from docauto.pipeline import Processador  # noqa: E402
from docauto.templates import carregar_codigos, carregar_templates  # noqa: E402

FIXTURES = RAIZ / "tests" / "fixtures"
HOJE = date(2026, 9, 15)


def ler(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


class TestNormalize(unittest.TestCase):
    def test_cnpj_dv(self):
        self.assertTrue(cnpj_valido("11.222.333/0001-81"))
        self.assertFalse(cnpj_valido("11.222.333/0001-82"))
        self.assertFalse(cnpj_valido("11.111.111/1111-11"))

    def test_cnpj_invalido_nao_identifica_empresa(self):
        ex = extrair_campos("CNPJ 11.222.333/0001-82")
        self.assertEqual(ex.cnpjs, [])
        self.assertEqual(ex.cnpjs_invalidos, ["11222333000182"])

    def test_competencia_explicita_vence_apuracao(self):
        texto = normalizar("Competencia: 07/2026\nPeriodo de Apuracao: 08/2026")
        comp = extrair_competencia(texto)
        self.assertEqual((comp.valor, comp.fonte), ("2026-07", "EXPLICITA"))

    def test_vencimento_nunca_vira_competencia(self):
        comp = extrair_competencia(normalizar("Data de Vencimento: 25/09/2026"))
        self.assertIsNone(comp.valor)

    def test_competencia_por_apuracao_com_data_completa(self):
        comp = extrair_competencia(normalizar("Periodo de Apuracao: 31/08/2026"))
        self.assertEqual((comp.valor, comp.fonte), ("2026-08", "APURACAO"))

    def test_valor_total(self):
        ex = extrair_campos("VALOR TOTAL DO DOCUMENTO: 1.234,56")
        self.assertEqual(ex.valor, 1234.56)


class TestClassificacao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates = carregar_templates(RAIZ / "config" / "templates")
        cls.codigos = carregar_codigos(RAIZ / "config" / "codigos_receita.yaml")

    def classificar(self, nome: str):
        return classificar(extrair_campos(ler(nome)), self.templates, self.codigos)

    def test_pis(self):
        c = self.classificar("darf_pis.txt")
        self.assertEqual(c.tipo, "PIS")
        self.assertFalse(c.ambiguo)

    def test_cofins_nao_vira_pis(self):
        c = self.classificar("darf_cofins.txt")
        self.assertEqual(c.tipo, "COFINS")

    def test_das_suprime_tributos_internos(self):
        c = self.classificar("das.txt")
        self.assertEqual(c.tipo, "DAS")
        self.assertFalse(c.ambiguo)

    def test_empate_pis_cofins_vai_para_validacao(self):
        c = self.classificar("darf_ambiguo.txt")
        self.assertEqual(c.tipo, "NECESSITA_VALIDACAO")
        self.assertTrue(c.ambiguo)

    def test_preposicao_das_nao_classifica_como_das(self):
        texto = "Relatorio das vendas das lojas das filiais no periodo"
        c = classificar(extrair_campos(texto), self.templates, self.codigos)
        self.assertNotEqual(c.tipo, "DAS")

    def test_ir_sem_codigo_exige_validacao(self):
        texto = ("DARF IMPOSTO SOBRE A RENDA\nPeriodo de Apuracao: 08/2026\n"
                 "CNPJ: 11.222.333/0001-81\nVALOR TOTAL DO DOCUMENTO: 10,00")
        c = classificar(extrair_campos(texto), self.templates, self.codigos)
        self.assertEqual(c.tipo, "IR")
        self.assertTrue(c.ambiguo)

    def test_retencao_conjunta(self):
        texto = "DARF CODIGO DA RECEITA: 5952\nPeriodo de Apuracao: 08/2026"
        c = classificar(extrair_campos(texto), self.templates, self.codigos)
        self.assertEqual(c.tipo, "RETENCAO_CONJUNTA")
        self.assertTrue(c.ambiguo)


class TestCadastro(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cadastro = Cadastro.carregar(RAIZ / "data" / "empresas.exemplo.csv")

    def test_cadastro_exemplo_valido(self):
        self.assertEqual(self.cadastro.validar(), [])

    def test_nivel_cnpj(self):
        r = self.cadastro.resolver(extrair_campos(ler("darf_pis.txt")))
        self.assertEqual(r.nivel, "CNPJ")
        self.assertEqual(r.empresa.id, "0001")

    def test_cnpj_fora_do_cadastro_nao_identifica(self):
        r = self.cadastro.resolver(extrair_campos(ler("darf_empresa_desconhecida.txt")))
        self.assertIsNone(r.empresa)
        self.assertIn("não encontrado", r.motivo)

    def test_razao_social_com_diferenca_de_escrita(self):
        r = self.cadastro.resolver(
            extrair_campos("EMPRESA EXEMPLO COMERCIO DE ALIMENTO LTDA"))
        self.assertEqual(r.empresa.id, "0001")
        self.assertEqual(r.nivel, "RAZAO_SOCIAL")


class TestRouting(unittest.TestCase):
    def test_sanitiza_caracteres_proibidos_do_windows(self):
        self.assertEqual(routing.sanitizar('EMPRESA: A/B "X" <1>'), "EMPRESA- A-B -X- -1")

    def test_nome_reservado(self):
        self.assertTrue(routing.sanitizar("CON").startswith("_"))

    def test_slug(self):
        self.assertEqual(routing.slug("Exemplo Alimentos & Cia"), "EXEMPLO-ALIMENTOS-CIA")


class TestArquivamento(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.origem = self.tmp / "a.txt"
        self.origem.write_text("conteudo", encoding="utf-8")
        self.destino = self.tmp / "destino"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_nao_sobrescreve_arquivo_diferente(self):
        self.destino.mkdir()
        (self.destino / "x.txt").write_text("outro conteudo", encoding="utf-8")
        status, caminho = arquivar(self.origem, self.destino, "x.txt")
        self.assertEqual(status, "RENOMEADO")
        self.assertTrue(caminho.endswith("x_02.txt"))
        self.assertEqual((self.destino / "x.txt").read_text(), "outro conteudo")

    def test_identico_e_duplicado(self):
        arquivar(self.origem, self.destino, "x.txt")
        status, _ = arquivar(self.origem, self.destino, "x.txt")
        self.assertEqual(status, "DUPLICADO")
        self.assertEqual(len(list(self.destino.iterdir())), 1)


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        cfg = yaml.safe_load((RAIZ / "config" / "config.example.yaml").read_text())
        cfg["_raiz"] = str(RAIZ)
        cfg["pastas"] = {
            "entrada": str(self.tmp / "ENTRADA"),
            "processados": str(self.tmp / "ENTRADA" / "_PROCESSADOS"),
            "pendentes": str(self.tmp / "PENDENTES"),
            "base_clientes": str(self.tmp / "CLIENTES"),
        }
        cfg["cadastro"]["arquivo"] = "data/empresas.exemplo.csv"
        cfg["registro"] = {"csv": str(self.tmp / "reg.csv"),
                           "jsonl": str(self.tmp / "reg.jsonl")}
        (self.tmp / "ENTRADA").mkdir(parents=True)
        for f in FIXTURES.glob("*.txt"):
            shutil.copy2(f, self.tmp / "ENTRADA" / f.name)
        self.proc = Processador(cfg)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def resultado(self, nome: str):
        return self.proc.processar_arquivo(self.tmp / "ENTRADA" / nome, hoje=HOJE)

    def test_das_arquivado_no_caminho_correto(self):
        r = self.resultado("das.txt")
        self.assertEqual(r.decisao, AUTOMATICO)
        self.assertEqual(r.tipo, "DAS")
        self.assertEqual(r.competencia, "2026-08")
        destino = Path(r.destino)
        self.assertTrue(destino.exists())
        self.assertEqual(destino.name, "2026-08_DAS_EXEMPLO.txt")
        self.assertIn("0001 - EMPRESA EXEMPLO COMERCIO DE ALIMENTOS LTDA", str(destino))
        self.assertIn("FISCAL/2026/2026-08/GUIAS", destino.as_posix())

    def test_pis_arquivado(self):
        r = self.resultado("darf_pis.txt")
        self.assertIn(r.decisao, (AUTOMATICO, REVISAO))
        self.assertEqual(r.tipo, "PIS")
        self.assertTrue(Path(r.destino).exists())

    def test_ambiguo_vai_para_pendentes_e_gera_laudo(self):
        r = self.resultado("darf_ambiguo.txt")
        self.assertEqual(r.decisao, PENDENTE)
        self.assertIn("CLASSIFICACAO_AMBIGUA", " ".join(r.travas))
        self.assertIn("PENDENTES", r.destino)
        self.assertTrue(Path(r.destino + ".laudo.json").exists())

    def test_empresa_desconhecida_nao_e_arquivada_em_ninguem(self):
        r = self.resultado("darf_empresa_desconhecida.txt")
        self.assertEqual(r.decisao, PENDENTE)
        self.assertIn("EMPRESA_NAO_IDENTIFICADA", " ".join(r.travas))
        self.assertNotIn("CLIENTES", r.destino)

    def test_sem_competencia_nao_arquiva_pelo_vencimento(self):
        r = self.resultado("darf_sem_competencia.txt")
        self.assertEqual(r.decisao, PENDENTE)
        self.assertIn("COMPETENCIA_NAO_IDENTIFICADA", " ".join(r.travas))

    def test_dry_run_nao_escreve_nada(self):
        self.proc.processar_pasta(dry_run=True, hoje=HOJE)
        self.assertFalse((self.tmp / "CLIENTES").exists())

    def test_original_permanece_na_entrada(self):
        self.resultado("das.txt")
        self.assertTrue((self.tmp / "ENTRADA" / "das.txt").exists())

    def test_reprocessar_nao_duplica(self):
        self.resultado("das.txt")
        r = self.resultado("das.txt")
        self.assertEqual(r.status_arquivo, "DUPLICADO")


if __name__ == "__main__":
    unittest.main()


class TestFilaEnvio(unittest.TestCase):
    """Fila de envio ao Express — o ponto onde um erro vira documento duplicado
    dentro do Domínio, então é onde mais vale teste."""

    def setUp(self):
        from docauto.envio import FilaEnvio
        self.tmp = Path(tempfile.mkdtemp())
        self.origem = self.tmp / "2026-08_DAS_EXEMPLO.pdf"
        self.origem.write_text("guia", encoding="utf-8")
        self.fila = FilaEnvio(self.tmp / "envio.csv")
        self.cfg = {"modo": "lote_manual", "pasta_lote": str(self.tmp / "LOTE"),
                    "limite_por_rodada": 50, "horas_para_alerta": 4}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def item(self, hash_doc="abc", empresa="0001"):
        from docauto.envio import Item
        return Item(hash=hash_doc, arquivo=str(self.origem), nome=self.origem.name,
                    empresa_id=empresa, empresa="EMPRESA EXEMPLO", tipo="DAS",
                    competencia="2026-08", decisao=AUTOMATICO)

    def test_mesmo_documento_nao_entra_duas_vezes(self):
        self.assertEqual(self.fila.enfileirar(self.item()), "ENFILEIRADO")
        self.assertTrue(self.fila.enfileirar(self.item()).startswith("JA_NA_FILA"))
        self.assertEqual(len(self.fila.itens), 1)

    def test_filtro_de_empresa_piloto(self):
        self.fila.enfileirar(self.item("a", "0001"))
        self.fila.enfileirar(self.item("b", "0002"))
        self.assertEqual(len(self.fila.pendentes(["0001"])), 1)

    def test_limite_por_rodada(self):
        for i in range(5):
            self.fila.enfileirar(self.item(f"h{i}"))
        self.assertEqual(len(self.fila.pendentes(limite=2)), 2)

    def test_lote_manual_separa_por_competencia(self):
        self.fila.enfileirar(self.item())
        self.fila.enviar(self.cfg)
        self.assertTrue((self.tmp / "LOTE" / "2026-08" / self.origem.name).exists())

    def test_dry_run_nao_copia_nem_muda_estado(self):
        from docauto.envio import PENDENTE
        self.fila.enfileirar(self.item())
        self.fila.enviar(self.cfg, dry_run=True)
        self.assertFalse((self.tmp / "LOTE").exists())
        self.assertEqual(self.fila.itens[0].estado, PENDENTE)

    def test_enviado_nao_e_reenviado(self):
        self.fila.enviar(self.cfg)
        self.fila.enfileirar(self.item())
        self.fila.enviar(self.cfg)
        self.assertEqual(len(self.fila.enviar(self.cfg)), 0)

    def test_arquivo_sumido_do_servidor_bloqueia(self):
        from docauto.envio import BLOQUEADO
        self.fila.enfileirar(self.item())
        self.origem.unlink()
        self.fila.enviar(self.cfg)
        self.assertEqual(self.fila.itens[0].estado, BLOQUEADO)

    def test_conciliacao_marca_consumido_e_parado(self):
        from datetime import datetime, timedelta

        from docauto.envio import CONSUMIDO, PARADO
        cfg = {"modo": "pasta_monitorada",
               "pasta_monitorada": str(self.tmp / "UPLOAD"), "horas_para_alerta": 4}
        self.fila.enfileirar(self.item("a"))
        self.fila.enfileirar(self.item("b"))
        self.fila.itens[1].nome = "outro.pdf"
        self.fila.enviar(cfg)

        Path(self.fila.itens[0].destino_envio).unlink()      # Express consumiu
        self.fila.itens[1].enviado_em = (
            datetime.now() - timedelta(hours=9)).isoformat(timespec="seconds")
        self.fila.conciliar(cfg)

        self.assertEqual(self.fila.itens[0].estado, CONSUMIDO)
        self.assertEqual(self.fila.itens[1].estado, PARADO)

    def test_reenfileirar(self):
        from docauto.envio import PENDENTE
        self.fila.enfileirar(self.item())
        self.fila.enviar(self.cfg)
        self.assertTrue(self.fila.reenfileirar("abc"))
        self.assertEqual(self.fila.itens[0].estado, PENDENTE)


class TestEnvioNoPipeline(TestPipeline):
    """Herda o cenário do pipeline e liga o envio."""

    def setUp(self):
        super().setUp()
        self.proc.cfg["envio"] = {
            "habilitado": True, "modo": "lote_manual",
            "pasta_lote": str(self.tmp / "LOTE"), "fila": str(self.tmp / "envio.csv"),
            "empresas_piloto": [], "limite_por_rodada": 50, "incluir_revisao": True,
            "horas_para_alerta": 4}
        from docauto.envio import FilaEnvio
        self.proc.fila = FilaEnvio(self.tmp / "envio.csv")

    def test_pendencia_nunca_entra_na_fila_do_express(self):
        self.resultado("darf_ambiguo.txt")
        self.resultado("darf_empresa_desconhecida.txt")
        self.assertEqual(self.proc.fila.itens, [])

    def test_arquivado_entra_na_fila_uma_vez_so(self):
        self.resultado("das.txt")
        self.resultado("das.txt")
        self.assertEqual(len(self.proc.fila.itens), 1)
        self.assertEqual(self.proc.fila.itens[0].tipo, "DAS")

    def test_fora_do_piloto_nao_e_enfileirado(self):
        self.proc.cfg["envio"]["empresas_piloto"] = ["0002"]
        r = self.resultado("das.txt")            # empresa 0001
        self.assertEqual(r.envio, "NAO_ENVIADO:fora_do_piloto")
        self.assertEqual(self.proc.fila.itens, [])

    def test_envio_desligado_nao_enfileira(self):
        self.proc.cfg["envio"]["habilitado"] = False
        r = self.resultado("das.txt")
        self.assertEqual(r.envio, "")
        self.assertEqual(self.proc.fila.itens, [])


class TestConfirmacaoDoLote(unittest.TestCase):
    """Fecha o ciclo em produto web: quem diz se o Express vinculou é a pessoa,
    pela planilha. Sem isso a fila ficaria em ENVIADO para sempre."""

    def setUp(self):
        from docauto.envio import FilaEnvio, Item, escrever_conferencia
        self.tmp = Path(tempfile.mkdtemp())
        self.lote = self.tmp / "LOTE" / "2026-08"
        self.fila = FilaEnvio(self.tmp / "envio.csv")
        self.cfg = {"modo": "lote_manual", "pasta_lote": str(self.tmp / "LOTE")}
        self.itens = []
        for i, tipo in enumerate(("DAS", "PIS", "COFINS")):
            origem = self.tmp / f"2026-08_{tipo}_EXEMPLO.pdf"
            origem.write_text(tipo, encoding="utf-8")
            item = Item(hash=f"h{i}", arquivo=str(origem), nome=origem.name,
                        empresa_id="0001", empresa="EMPRESA EXEMPLO", tipo=tipo,
                        competencia="2026-08", decisao=AUTOMATICO)
            self.fila.enfileirar(item)
            self.itens.append(item)
        self.fila.enviar(self.cfg)
        escrever_conferencia(self.itens, self.lote)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def responder(self, respostas: list[str]):
        import csv as _csv
        planilha = self.lote / "_CONFERIR.csv"
        linhas = list(_csv.DictReader(
            planilha.read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))
        for linha, resposta in zip(linhas, respostas):
            linha["tarefa_vinculada"] = resposta
        with planilha.open("w", newline="", encoding="utf-8-sig") as f:
            w = _csv.DictWriter(f, fieldnames=linhas[0].keys(), delimiter=";")
            w.writeheader()
            w.writerows(linhas)

    def test_vinculada_vira_consumido_e_sai_da_pasta(self):
        from docauto.envio import CONSUMIDO
        self.responder(["SIM", "", ""])
        self.fila.confirmar_lote(self.lote)
        self.assertEqual(self.fila.itens[0].estado, CONSUMIDO)
        self.assertEqual(self.fila.itens[0].resultado_express, "VINCULADA")
        self.assertFalse((self.lote / self.itens[0].nome).exists())
        self.assertTrue((self.lote / "_ENVIADOS" / self.itens[0].nome).exists())

    def test_multipla_conta_como_vinculada_mas_fica_registrada(self):
        from docauto.envio import CONSUMIDO
        self.responder(["MULTIPLA", "", ""])
        self.fila.confirmar_lote(self.lote)
        self.assertEqual(self.fila.itens[0].estado, CONSUMIDO)
        self.assertEqual(self.fila.itens[0].resultado_express, "MULTIPLA")
        self.assertIn("escolha manual", self.fila.itens[0].observacao)

    def test_nao_encontrada_vira_parado_e_arquivo_permanece(self):
        from docauto.envio import PARADO
        self.responder(["NAO", "", ""])
        self.fila.confirmar_lote(self.lote)
        self.assertEqual(self.fila.itens[0].estado, PARADO)
        self.assertTrue((self.lote / self.itens[0].nome).exists())

    def test_linha_sem_resposta_nao_muda_nada(self):
        from docauto.envio import ENVIADO
        resultados = self.fila.confirmar_lote(self.lote)
        self.assertTrue(all(r == "SEM_RESPOSTA" for _, r in resultados))
        self.assertTrue(all(i.estado == ENVIADO for i in self.fila.itens))

    def test_resposta_nao_reconhecida_nao_altera_o_item(self):
        from docauto.envio import ENVIADO
        self.responder(["talvez", "", ""])
        resultados = self.fila.confirmar_lote(self.lote)
        self.assertTrue(resultados[0][1].startswith("RESPOSTA_NAO_RECONHECIDA"))
        self.assertEqual(self.fila.itens[0].estado, ENVIADO)

    def test_dry_run_nao_move_nem_grava(self):
        from docauto.envio import ENVIADO, FilaEnvio
        self.responder(["SIM", "SIM", "SIM"])
        self.fila.confirmar_lote(self.lote, dry_run=True)
        self.assertTrue((self.lote / self.itens[0].nome).exists())
        recarregada = FilaEnvio(self.tmp / "envio.csv")
        self.assertTrue(all(i.estado == ENVIADO for i in recarregada.itens))

    def test_planilha_ausente_avisa(self):
        (self.lote / "_CONFERIR.csv").unlink()
        with self.assertRaises(FileNotFoundError):
            self.fila.confirmar_lote(self.lote)

    def test_metricas(self):
        self.responder(["SIM", "MULTIPLA", "NAO"])
        self.fila.confirmar_lote(self.lote)
        m = self.fila.metricas_express()
        self.assertEqual((m["VINCULADA"], m["MULTIPLA"], m["NAO_ENCONTRADA"]), (1, 1, 1))

    def test_confirmar_duas_vezes_e_seguro(self):
        from docauto.envio import CONSUMIDO
        self.responder(["SIM", "SIM", "SIM"])
        self.fila.confirmar_lote(self.lote)
        self.fila.confirmar_lote(self.lote)
        self.assertTrue(all(i.estado == CONSUMIDO for i in self.fila.itens))


class TestRazaoSocialComRotulo(unittest.TestCase):
    def test_nome_atras_de_rotulo_de_campo(self):
        from docauto.normalize import extrair_razoes_sociais, normalizar
        texto = normalizar("01 NOME / TELEFONE: EMPRESA EXEMPLO COMERCIO DE ALIMENTOS LTDA")
        self.assertEqual(extrair_razoes_sociais(texto),
                         ["EMPRESA EXEMPLO COMERCIO DE ALIMENTOS LTDA"])

    def test_pessoa_fisica_nao_vira_razao_social(self):
        from docauto.normalize import extrair_razoes_sociais, normalizar
        self.assertEqual(extrair_razoes_sociais(normalizar("NOME: JOAO DA SILVA")), [])

    def test_identifica_empresa_em_darf_com_rotulo(self):
        cadastro = Cadastro.carregar(RAIZ / "data" / "empresas.exemplo.csv")
        ex = extrair_campos("01 NOME / TELEFONE: MODELO SERVICOS DE TECNOLOGIA LTDA")
        self.assertEqual(cadastro.resolver(ex).empresa.id, "0002")


class TestDestinosMultiplos(TestPipeline):
    """Servidor + Dropbox: a mesma estrutura de pastas nos dois."""

    def setUp(self):
        super().setUp()
        self.servidor = self.tmp / "CLIENTES"
        self.dropbox = self.tmp / "DROPBOX"
        self.proc.destinos = [
            {"nome": "SERVIDOR", "raiz": str(self.servidor), "principal": True},
            {"nome": "DROPBOX", "raiz": str(self.dropbox), "principal": False},
        ]

    def test_copia_para_os_dois_destinos(self):
        r = self.resultado("das.txt")
        self.assertEqual(r.decisao, AUTOMATICO)
        self.assertTrue(Path(r.destino).exists())
        self.assertTrue(str(r.destino).startswith(str(self.servidor)))
        self.assertEqual(len(r.copias), 1)
        copia = Path(r.copias[0].split("=", 1)[1])
        self.assertTrue(copia.exists())
        self.assertEqual(copia.relative_to(self.dropbox),
                         Path(r.destino).relative_to(self.servidor))

    def test_dropbox_indisponivel_nao_derruba_o_documento(self):
        from docauto.espelho import FilaEspelho
        self.proc.espelho = FilaEspelho(self.tmp / "espelho.csv")
        # Dropbox "fora do ar": o caminho existe como ARQUIVO, então criar
        # pasta dentro dele levanta OSError, igual a uma unidade desconectada.
        self.dropbox.write_text("nao sou uma pasta", encoding="utf-8")

        r = self.resultado("das.txt")
        self.assertEqual(r.decisao, AUTOMATICO)          # documento salvo no servidor
        self.assertTrue(Path(r.destino).exists())
        self.assertTrue(any("ESPELHO_PENDENTE" in a for a in r.avisos))
        self.assertEqual(len(self.proc.espelho.pendentes()), 1)

    def test_espelho_refeito_depois_que_o_destino_volta(self):
        from docauto.espelho import COPIADO, FilaEspelho
        self.proc.espelho = FilaEspelho(self.tmp / "espelho.csv")
        self.dropbox.write_text("nao sou uma pasta", encoding="utf-8")
        self.resultado("das.txt")

        self.dropbox.unlink()                            # Dropbox voltou
        fila = FilaEspelho(self.tmp / "espelho.csv")
        resultados = fila.refazer()
        self.assertEqual([s for _, s in resultados], ["ARQUIVADO"])
        self.assertEqual(fila.itens[0].estado, COPIADO)
        self.assertTrue(Path(fila.itens[0].pasta_destino, fila.itens[0].nome).exists())
        self.assertEqual(fila.pendentes(), [])


class TestVariasEntradas(TestPipeline):
    def test_processa_todas_as_pastas_de_entrada(self):
        from docauto.config import entradas
        segunda = self.tmp / "EXPRESS"
        segunda.mkdir()
        shutil.copy2(FIXTURES / "darf_cofins.txt", segunda / "darf_cofins.txt")
        self.proc.cfg["pastas"]["entrada"] = [str(self.tmp / "ENTRADA"), str(segunda)]
        self.assertEqual(len(entradas(self.proc.cfg)), 2)

        resultados = self.proc.processar_pasta(hoje=HOJE)
        origens = {Path(r.arquivo_origem).parent.name for r in resultados}
        self.assertIn("EXPRESS", origens)

    def test_pasta_de_entrada_inexistente_e_ignorada(self):
        self.proc.cfg["pastas"]["entrada"] = [str(self.tmp / "ENTRADA"),
                                              str(self.tmp / "NAO_EXISTE")]
        self.assertTrue(self.proc.processar_pasta(hoje=HOJE))

    def test_subpasta_enviados_nao_e_reprocessada(self):
        enviados = self.tmp / "ENTRADA" / "_ENVIADOS"
        enviados.mkdir()
        shutil.copy2(FIXTURES / "das.txt", enviados / "das.txt")
        resultados = self.proc.processar_pasta(hoje=HOJE)
        self.assertFalse(any("_ENVIADOS" in r.arquivo_origem for r in resultados))


class TestDiagnostico(unittest.TestCase):
    def test_pontuar_todos_devolve_todos_os_templates(self):
        from docauto.classify import pontuar_todos
        templates = carregar_templates(RAIZ / "config" / "templates")
        codigos = carregar_codigos(RAIZ / "config" / "codigos_receita.yaml")
        cands = pontuar_todos(extrair_campos(ler("darf_pis.txt")), templates, codigos)
        self.assertEqual(len(cands), len(templates))
        self.assertEqual(cands[0].tipo, "PIS")
        self.assertEqual(cands[0].relativo, 100)


class TestDoutor(unittest.TestCase):
    """O doutor precisa reprovar ambiente quebrado — é a única coisa que separa
    'configurei' de 'funciona'."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = yaml.safe_load((RAIZ / "config" / "config.example.yaml").read_text())
        self.cfg["_raiz"] = str(RAIZ)
        self.cfg["_arquivo"] = "teste"
        self.cfg["pastas"] = {"entrada": str(self.tmp / "ENTRADA"),
                              "processados": str(self.tmp / "PROC"),
                              "pendentes": str(self.tmp / "PEND"),
                              "base_clientes": str(self.tmp / "CLIENTES")}
        (self.tmp / "ENTRADA").mkdir()
        self.cfg["destinos"] = [{"nome": "SERVIDOR", "raiz": str(self.tmp / "CLIENTES"),
                                 "habilitado": True, "principal": True}]
        self.cfg["envio"]["habilitado"] = False

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def checar(self):
        from docauto.doutor import verificar
        return verificar(self.cfg)

    def item(self, checagens, prefixo):
        return next(c for c in checagens if c.item.startswith(prefixo))

    def test_entrada_inexistente_e_erro(self):
        from docauto.doutor import ERRO, resumo
        self.cfg["pastas"]["entrada"] = str(self.tmp / "NAO_EXISTE")
        checagens = self.checar()
        self.assertEqual(self.item(checagens, "entrada").nivel, ERRO)
        self.assertGreaterEqual(resumo(checagens)[0], 1)

    def test_destino_com_caminho_errado_nao_e_criado(self):
        from docauto.doutor import AVISO
        fantasma = self.tmp / "NAO_EXISTE" / "Dropbox" / "CLIENTES"
        self.cfg["destinos"].append({"nome": "DROPBOX", "raiz": str(fantasma),
                                     "habilitado": True, "principal": False})
        checagens = self.checar()
        self.assertEqual(self.item(checagens, "destino DROPBOX").nivel, AVISO)
        self.assertFalse(fantasma.exists())      # não pode criar pasta que não sincroniza

    def test_destino_principal_quebrado_e_erro(self):
        from docauto.doutor import ERRO
        self.cfg["destinos"][0]["raiz"] = str(self.tmp / "SEM_PAI" / "X" / "CLIENTES")
        self.assertEqual(self.item(self.checar(), "destino SERVIDOR").nivel, ERRO)

    def test_ambiente_sadio_so_tem_avisos(self):
        from docauto.doutor import ERRO
        erros = [c for c in self.checar() if c.nivel == ERRO]
        # o único erro possível neste ambiente de teste é a ausência de leitor de PDF
        self.assertTrue(all(c.item == "leitor de PDF" for c in erros), erros)

    def test_caminho_longo_reprova(self):
        from docauto.doutor import ERRO, verificar
        from docauto.pipeline import Processador
        self.cfg["cadastro"]["arquivo"] = "data/empresas.exemplo.csv"
        self.cfg["registro"] = {"csv": str(self.tmp / "r.csv"),
                                "jsonl": str(self.tmp / "r.jsonl")}
        self.cfg["envio"]["fila"] = str(self.tmp / "envio.csv")
        self.cfg["espelho"] = str(self.tmp / "espelho.csv")
        self.cfg["estrutura"]["limite_caminho"] = 40
        checagens = verificar(self.cfg, Processador(self.cfg))
        self.assertEqual(self.item(checagens, "limite de caminho").nivel, ERRO)


class TestConferenciaOnvio(unittest.TestCase):
    """Cruzamento entre a exportação do Onvio e o que a automação conhece."""

    ONVIO = FIXTURES / "onvio"

    @classmethod
    def setUpClass(cls):
        cls.cadastro = Cadastro.carregar(RAIZ / "data" / "empresas.exemplo.csv")
        cls.templates = carregar_templates(RAIZ / "config" / "templates")

    def empresas(self):
        from docauto.onvio import ler_planilha
        return ler_planilha(self.ONVIO / "empresas_onvio.csv")

    def test_reconhece_colunas_com_acento_e_nomes_diferentes(self):
        from docauto.onvio import mapear_colunas
        mapa = mapear_colunas(list(self.empresas()[0].keys()))
        self.assertEqual(mapa["cnpj"], "CNPJ")
        self.assertEqual(mapa["razao_social"], "Razão Social")
        self.assertEqual(mapa["codigo"], "Código")
        self.assertEqual(mapa["regime"], "Regime Tributário")

    def test_aponta_empresa_que_falta_dos_dois_lados(self):
        from docauto.onvio import conferir_empresas
        conf = conferir_empresas(self.empresas(), self.cadastro)
        tipos = {d.tipo for d in conf.divergencias}
        self.assertIn("FALTA_NO_CADASTRO", tipos)
        self.assertIn("FALTA_NO_ONVIO", tipos)
        self.assertEqual(conf.coincidentes, 2)

    def test_exportacao_sem_cnpj_avisa_em_vez_de_quebrar(self):
        from docauto.onvio import conferir_empresas
        with self.assertRaises(ValueError) as ctx:
            conferir_empresas([{"Empresa": "X", "Cidade": "Y"}], self.cadastro)
        self.assertIn("CNPJ", str(ctx.exception))

    def test_casa_obrigacao_do_onvio_com_template(self):
        from docauto.onvio import casar_tarefa
        self.assertEqual(casar_tarefa("DAS - Simples Nacional", self.templates), "DAS")
        self.assertEqual(casar_tarefa("DARF PIS/PASEP", self.templates), "PIS")
        self.assertEqual(casar_tarefa("DARF COFINS", self.templates), "COFINS")
        self.assertIsNone(casar_tarefa("Folha de pagamento", self.templates))

    def test_conferencia_de_tarefas_separa_os_dois_lados(self):
        from docauto.onvio import conferir_tarefas, ler_planilha
        conf = conferir_tarefas(ler_planilha(self.ONVIO / "tarefas_onvio.csv"),
                                self.templates)
        self.assertEqual(conf.por_template, {"DAS": 1, "PIS": 1, "COFINS": 1})
        self.assertEqual(conf.templates_sem_tarefa, ["CSLL", "IR"])
        self.assertIn("Folha de pagamento", conf.sem_template)

    def test_gera_cadastro_valido_a_partir_da_exportacao(self):
        from docauto.onvio import escrever_cadastro, gerar_cadastro
        tmp = Path(tempfile.mkdtemp())
        try:
            registros = gerar_cadastro(self.empresas())
            alvo = escrever_cadastro(registros, tmp / "empresas.csv")
            novo = Cadastro.carregar(alvo)
            self.assertEqual(novo.validar(), [])
            self.assertEqual(len(novo.empresas), 3)
            self.assertEqual(novo.empresas[0].codigo_dominio, "1001")
            self.assertTrue(all(e.nome_curto for e in novo.empresas))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_empresa_inativa_no_onvio_vira_ativa_nao(self):
        from docauto.onvio import gerar_cadastro
        linhas = [{"CNPJ": "11.222.333/0001-81", "Razão Social": "X LTDA",
                   "Situação": "Inativa"}]
        self.assertEqual(gerar_cadastro(linhas)[0]["ATIVA"], "NAO")

    def test_cnpj_invalido_na_exportacao_e_reportado(self):
        from docauto.onvio import conferir_empresas
        linhas = [{"CNPJ": "11.222.333/0001-82", "Razão Social": "ERRADA LTDA"}]
        conf = conferir_empresas(linhas, self.cadastro)
        self.assertEqual(conf.divergencias[0].tipo, "CNPJ_INVALIDO_NO_ONVIO")


class TestFolhaTeste(unittest.TestCase):
    """A folha de apuração é o que separa 'o Express não reconhece' de
    'a tarefa não existe' — precisa sair preenchida e com as colunas certas."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = yaml.safe_load((RAIZ / "config" / "config.example.yaml").read_text())
        self.cfg["_raiz"] = str(RAIZ)
        self.cfg["_arquivo"] = "teste"
        self.cfg["cadastro"]["arquivo"] = "data/empresas.exemplo.csv"
        self.cfg["processamento"]["extensoes"].append(".txt")
        self.cfg["registro"] = {"csv": str(self.tmp / "r.csv"),
                                "jsonl": str(self.tmp / "r.jsonl")}
        self.cfg["envio"]["fila"] = str(self.tmp / "envio.csv")
        self.cfg["espelho"] = str(self.tmp / "espelho.csv")
        self.cfg["pastas"]["base_clientes"] = str(self.tmp / "CLIENTES")
        self.saida = self.tmp / "apuracao.csv"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def gerar(self):
        import argparse
        from docauto.cli import cmd_folha_teste
        cfg_path = self.tmp / "config.yaml"
        cfg_path.write_text(yaml.safe_dump(self.cfg, allow_unicode=True))
        args = argparse.Namespace(config=str(cfg_path), entrada=str(FIXTURES),
                                  saida=str(self.saida))
        self.assertEqual(cmd_folha_teste(args), 0)
        import csv as _csv
        return list(_csv.DictReader(
            self.saida.read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))

    def test_uma_linha_por_documento_com_colunas_em_branco_para_o_express(self):
        linhas = self.gerar()
        self.assertEqual(len(linhas), len(list(FIXTURES.glob("*.txt"))))
        for linha in linhas:
            self.assertEqual(linha["tarefa_vinculada"], "")
            self.assertEqual(linha["tempo_seg"], "")

    def test_preenche_o_que_a_automacao_entendeu(self):
        linhas = {l["arquivo"]: l for l in self.gerar()}
        das = linhas["das.txt"]
        self.assertEqual(das["tipo_detectado"], "DAS")
        self.assertEqual(das["competencia"], "2026-08")
        self.assertEqual(das["decisao_automacao"], AUTOMATICO)
        self.assertIn("EXEMPLO", das["empresa_detectada"])

    def test_registra_o_motivo_da_pendencia(self):
        linhas = {l["arquivo"]: l for l in self.gerar()}
        self.assertEqual(linhas["darf_sem_competencia.txt"]["observacao"],
                         "COMPETENCIA_NAO_IDENTIFICADA")
        self.assertEqual(linhas["darf_empresa_desconhecida.txt"]["observacao"],
                         "EMPRESA_NAO_IDENTIFICADA")

    def test_nao_arquiva_nem_registra_nada(self):
        self.gerar()
        self.assertFalse((self.tmp / "CLIENTES").exists())
        self.assertFalse((self.tmp / "envio.csv").exists())
