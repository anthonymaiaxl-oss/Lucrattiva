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
