# 01 — Arquitetura do projeto

## Princípio que orienta todas as decisões

> A automação existe para **eliminar trabalho manual sem criar risco novo**.
> Documento arquivado na empresa errada custa mais caro do que documento não
> arquivado. Portanto: **na dúvida, para e pergunta.**

## Divisão de responsabilidades

| Quem | Faz | Não faz |
|---|---|---|
| **Domínio Processos / Express** | Recebe o documento, analisa, encontra a tarefa, vincula, pede escolha quando há mais de uma tarefa | Não organiza o servidor de arquivos do escritório, não garante nome padronizado, não devolve "empresa/competência" para o resto do fluxo |
| **Automação externa (este projeto)** | Lê, extrai, classifica, identifica empresa e competência, decide se tem confiança, nomeia, arquiva no servidor, registra tudo, separa exceções | Não tenta recriar o Express, não simula cliques como primeira opção, não adivinha |
| **Pessoa (fiscal)** | Resolve a fila de pendências, confirma casos ambíguos, mantém o cadastro de empresas | Não fica renomeando e arrastando arquivo bom |

A automação **complementa** o Express nos dois pontos em que ele não atua:
o **antes** (padronizar e pré-identificar o que entra) e o **depois**
(arquivar a cópia no lugar certo do servidor e registrar o que aconteceu).

## Componentes

```
config/          Regras do negócio em arquivos de texto (YAML/CSV).
                 Quem mexe: o contador. Não exige programador.
  templates/     Um arquivo por tipo de documento (DAS, PIS, COFINS, IR, CSLL)
  codigos_receita.yaml   Tabela código de receita -> tributo
  config.yaml    Caminhos, pesos, faixas de confiança

data/
  empresas.csv   Cadastro central das empresas (fonte única da verdade)
  registro/      registro.csv (para o escritório) + detalhado.jsonl (auditoria)

src/docauto/
  textio.py      Lê PDF / XLSX / TXT / imagem. OCR só na Fase 2.
  normalize.py   Extrai CNPJ, competência, valor, vencimento, código de receita
  templates.py   Carrega templates e a tabela de códigos
  classify.py    Decide o tipo do documento por múltiplos critérios
  empresas.py    Cadastro + resolução da empresa (CNPJ > razão > fantasia > pasta)
  confidence.py  Score de confiança + TRAVAS de segurança
  routing.py     Monta caminho de destino e nome padronizado (à prova de Windows)
  archive.py     Copia sem sobrescrever, detecta duplicado por hash
  ledger.py      Registro de tudo
  pipeline.py    Orquestra as etapas
  cli.py         Comandos: init, validar, estrutura, processar, relatorio
```

## Tecnologia — e por que esta e não outra

| Escolha | Motivo |
|---|---|
| **Python + biblioteca padrão** | Roda no servidor do escritório sem servidor web, sem banco, sem Docker. Instalação: Python + `pip install -r requirements.txt`. |
| **Regras em YAML/CSV, não no código** | O contador ajusta palavra-chave, código de receita e caminho de pasta sem depender de programador. É isso que faz a automação sobreviver ao primeiro mês. |
| **CSV para o cadastro no MVP** | Abre no Excel, versiona fácil, não quebra. Migrar para SQLite/Postgres quando passar de ~300 empresas ou quando duas pessoas precisarem editar ao mesmo tempo. Ver docs/05. |
| **Agendador do Windows (Tarefas Agendadas) a cada 10 min** | Mais simples e mais confiável do que serviço com watchdog. Watchdog perde evento se o processo cair; agendador sempre volta. |
| **n8n: só na Fase 4** | Ótimo para orquestrar avisos (e-mail/WhatsApp) e painel. Ruim para regra fiscal fina — regra fiscal fica em texto versionado, não dentro de nós de fluxo. |
| **OCR (Tesseract) só na Fase 2** | Metade dos DAS/DARF chega com texto nativo. Ligar OCR desde o dia 1 dobra a complexidade antes de o fluxo simples estar provado. |

## O que NÃO faz parte do MVP (de propósito)

- IA generativa classificando documento. Entra depois, e como **desempate**, nunca
  como primeira decisão — modelo que erra em silêncio é pior que fila de pendência.
- Integração automática com o Express (Fase 3 — depende de confirmação, ver docs/08).
- Departamento Pessoal, Contábil, Societário (estrutura já preparada, conteúdo depois).
- Mover/apagar o original. Nos primeiros 60 dias o fluxo só **copia**.
