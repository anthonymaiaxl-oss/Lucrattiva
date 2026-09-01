# Automação de documentos fiscais — Domínio Processos Express + arquivamento

Automação para escritório contábil: recebe documento tributário, identifica
**empresa**, **tributo** e **competência**, arquiva no caminho padronizado do
servidor, separa o que ficou duvidoso e registra tudo. Prepara — sem depender
dela — a integração com o **Domínio Processos Express**.

**Princípio:** documento arquivado na empresa errada custa mais caro que
documento não arquivado. **Na dúvida, para e pergunta.**

---

## Por onde começar

👉 **[docs/09 — Plano de implantação passo a passo](docs/09-plano-implementacao.md)** —
é o documento principal, escrito para um escritório que começou agora.

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

---

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```bash
python -m docauto init                 # cria config.yaml, cadastro e pastas
python -m docauto validar              # confere o cadastro (CNPJ, duplicados)
python -m docauto estrutura --ano 2026 # cria a árvore de pastas dos clientes
python -m docauto processar --dry-run  # simula: não copia nada
python -m docauto processar            # para valer
python -m docauto relatorio            # % automático, pendências por motivo
```

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

30 testes cobrindo dígito verificador de CNPJ, prioridade da competência
(vencimento nunca vira competência), PIS × COFINS, supressão do DAS, retenção
conjunta, sanitização de nome no Windows, não sobrescrita e detecção de duplicado.

## O que o escritório configura (sem programar)

| Arquivo | O quê |
|---|---|
| `config/config.yaml` | Caminhos, pesos de confiança, faixas, estrutura de pastas, nomenclatura |
| `config/templates/*.yaml` | Um arquivo por tipo de documento |
| `config/codigos_receita.yaml` | Código de receita → tributo (**conferir antes de usar em produção**) |
| `data/empresas.csv` | Cadastro central (não versionado) |

## Estado atual

- ✅ **Fase 1** — entrada, leitura, extração, classificação, empresa, competência, caminho, arquivamento, log, fila de exceções
- 🔧 **Fase 2** — OCR e calibração: código pronto, desligado por padrão
- ⏸️ **Fase 3** — Express: implementado como cópia para pasta monitorada, **desligado até confirmação com a Thomson Reuters** ([docs/08](docs/08-integracao-express.md))
- 📋 **Fase 4** — painel de exceções: só quando a fila justificar

> **Antes de produção:** conferir `config/codigos_receita.yaml` contra a tabela
> oficial da Receita Federal. Enquanto o status for `NAO_CONFERIDA`, todo
> documento classificado por código recebe aviso no registro.
