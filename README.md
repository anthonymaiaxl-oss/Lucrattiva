# Automação de documentos fiscais — Domínio Processos Express + arquivamento

Automação para escritório contábil: recebe documento tributário, identifica
**empresa**, **tributo** e **competência**, arquiva no caminho padronizado do
servidor, separa o que ficou duvidoso e registra tudo. Prepara — sem depender
dela — a integração com o **Domínio Processos Express**.

**Princípio:** documento arquivado na empresa errada custa mais caro que
documento não arquivado. **Na dúvida, para e pergunta.**

---

## Por onde começar

👉 **[docs/17 — Guia de campo: os 5 primeiros dias no Express](docs/17-guia-de-campo-express.md)** —
o que fazer hora a hora, na empresa, começando amanhã.
👉 **[docs/12 — Runbook: operar no Onvio Express](docs/12-runbook-onvio-express.md)** —
o passo a passo de execução, com a mão no Onvio.
👉 **[docs/11 — Express e envio funcionando esta semana](docs/11-express-esta-semana.md)** —
plano dia a dia quando o prazo é a semana corrente.
👉 **[docs/09 — Plano de implantação passo a passo](docs/09-plano-implementacao.md)** —
o roteiro completo, escrito para um escritório que começou agora.

| Doc | Conteúdo |
|---|---|
| [01 Arquitetura](docs/01-arquitetura.md) | Componentes, responsabilidades, tecnologias e o que ficou de fora |
| [02 Fluxo](docs/02-fluxo.md) | Diagrama textual e mermaid, do arquivo à tarefa |
| [03 Templates](docs/03-templates.md) | DAS, PIS, COFINS, IR, CSLL — critérios A a H |
| [04 Estrutura de pastas](docs/04-estrutura-pastas.md) | Árvore proposta, justificativas, nomenclatura |
| [05 Cadastro de empresas](docs/05-cadastro-empresas.md) | Colunas e por que CSV no MVP |
| [06 Classificação](docs/06-classificacao.md) | Árvore de decisão; empresa e competência |
| [07 Confiança](docs/07-score-confianca.md) | Pontos, faixas, travas e como calibrar |
| [08 Express](docs/08-integracao-express.md) | Cenários A/B/C e as 10 perguntas para a Thomson Reuters |
| [09 Implantação](docs/09-plano-implementacao.md) | Semana a semana, com comandos |
| [10 Operação](docs/10-operacao-seguranca.md) | Rotina, backup, LGPD, indicadores |
| [11 Express esta semana](docs/11-express-esta-semana.md) | Envio em produção em 5 dias, nos dois mecanismos possíveis |
| [12 Runbook Onvio](docs/12-runbook-onvio-express.md) | Rotina diária de execução no Onvio Express |
| [13 Calibrar templates](docs/13-calibrar-templates.md) | Ajustar os templates às suas guias, com `diagnosticar` |
| [14 Servidor + Dropbox](docs/14-copias-servidor-dropbox.md) | Cópias em vários destinos e a ordem correta do fluxo |
| [15 Acessos e instalação](docs/15-acessos-e-instalacao.md) | O que está automatizado e o que só você pode fazer |
| [16 Espelhar o Onvio](docs/16-espelhar-o-onvio.md) | Conferir cadastro e obrigações a partir da exportação do Onvio |
| [17 Guia de campo](docs/17-guia-de-campo-express.md) | Os 5 primeiros dias no Express, hora a hora |

---

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```bash
scripts\instalar.bat                   # Windows: instala tudo de uma vez
python -m docauto init                 # cria config.yaml, cadastro e pastas
python -m docauto doutor               # o que falta para funcionar NESTE computador
python -m docauto validar              # confere o cadastro (CNPJ, duplicados)
python -m docauto estrutura --ano 2026 # cria a árvore de pastas dos clientes
python -m docauto processar --dry-run  # simula: não copia nada
python -m docauto processar            # para valer
python -m docauto relatorio            # % automático, pendências por motivo

python -m docauto enviar --dry-run     # mostra o que iria para o Express
python -m docauto enviar               # monta o lote / copia para a pasta monitorada
python -m docauto envio-confirmar --lote D:/CONTABIL/LOTE_EXPRESS/2026-08
python -m docauto envio-status         # o que o Express consumiu e o que travou

python -m docauto diagnosticar --entrada C:/amostras --texto C:/amostras/_texto
python -m docauto espelhar             # refaz cópias que falharam (Dropbox fora do ar)
python -m docauto folha-teste --entrada C:/teste-lote --saida C:/teste-lote/apuracao.csv
python -m docauto onvio-conferir --empresas data/onvio/empresas.csv --tarefas data/onvio/tarefas.csv
python -m docauto prioridade --tarefas data/onvio/tarefas.csv   # qual template configurar em seguida
```

No Windows, `scripts/processar.bat` e `scripts/enviar.bat` já estão prontos para
o Agendador de Tarefas — ver [scripts/agendar.md](scripts/agendar.md).

Saída real:

```
[OK ] darf_pis.txt -> PIS 2026-08 EMPRESA EXEMPLO ... score=91
        -> .../0001 - EMPRESA EXEMPLO .../FISCAL/2026/2026-08/GUIAS/2026-08_PIS_EXEMPLO.pdf
[PEN] darf_ambiguo.txt -> NECESSITA_VALIDACAO 2026-08 ... score=61
        ! CLASSIFICACAO_AMBIGUA: empate entre COFINS (43) e PIS (43)
        -> .../PENDENTES/CLASSIFICACAO_AMBIGUA/darf_ambiguo.txt
```

Cada pendência gera um `.laudo.json` ao lado do arquivo, com o motivo, os
candidatos e as sugestões de empresa — é o painel de exceções da Fase 1.

## Testes

```bash
python -m unittest discover -s tests -t .
```

113 testes cobrindo dígito verificador de CNPJ, prioridade da competência
(vencimento nunca vira competência), PIS × COFINS, supressão do DAS, retenção
conjunta, sanitização de nome no Windows, não sobrescrita, detecção de duplicado e a fila
de envio (idempotência, piloto, limite, conciliação, bloqueio) e o fechamento
do ciclo pela planilha de conferência, arquivamento em múltiplos destinos e a
fila de espelho, a verificação de ambiente e a conferência contra a exportação do Onvio.

## O que o escritório configura (sem programar)

| Arquivo | O quê |
|---|---|
| `config/config.yaml` | Caminhos, pesos de confiança, faixas, estrutura de pastas, nomenclatura |
| `config/templates/*.yaml` | Um arquivo por tipo de documento |
| `config/codigos_receita.yaml` | Código de receita → tributo (**conferir antes de usar em produção**) |
| `data/empresas.csv` | Cadastro central (não versionado) |
| `config/config.yaml` → `destinos:` | Servidor, Dropbox e o que mais houver — o documento vai para todos |
| `config/config.yaml` → `envio:` | Modo de envio ao Express, empresas piloto, limite por rodada |

## Estado atual

- ✅ **Fase 1** — entrada, leitura, extração, classificação, empresa, competência, caminho, arquivamento, log, fila de exceções
- 🔧 **Fase 2** — OCR e calibração: código pronto, desligado por padrão
- ✅ **Fase 3 — envio ao Express**: fila com idempotência por SHA-256, empresas
  piloto, limite por rodada e conciliação. Dois modos na mesma fila —
  `lote_manual` (funciona hoje, sem depender de confirmação) e
  `pasta_monitorada` (uma linha de config quando confirmado). O ciclo do lote
  fecha com `envio-confirmar`, que lê a planilha preenchida e mede quanto o
  Express vinculou sozinho. Rotina em [docs/12](docs/12-runbook-onvio-express.md);
  plano da semana em [docs/11](docs/11-express-esta-semana.md); cenários e
  perguntas para a Thomson Reuters em [docs/08](docs/08-integracao-express.md)
- 📋 **Fase 4** — painel de exceções: só quando a fila justificar

> **Antes de produção:** conferir `config/codigos_receita.yaml` contra a tabela
> oficial da Receita Federal. Enquanto o status for `NAO_CONFERIDA`, todo
> documento classificado por código recebe aviso no registro.
