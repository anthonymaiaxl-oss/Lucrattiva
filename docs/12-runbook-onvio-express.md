# 12 — Runbook: operar no Onvio Express

Passo a passo de execução. `docs/11` é o plano da semana; **este é o que se
executa todo dia**, com a mão no Onvio.

## Antes de tudo: qual caminho você vai usar

Onvio é produto **web**. Existem dois caminhos possíveis, e o código já suporta
os dois:

| Caminho | Como funciona | Quando usar |
|---|---|---|
| **B — pasta local do Express** | O artigo oficial [Como utilizar Express? (código 9146)](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=9146) descreve **baixar e usar uma pasta local no computador**: o documento colocado nela é enviado ao Processos. Se existir na sua conta, é o melhor caminho. | Confirme na tela do Express (Parte 1, passo 5). Config: `modo: "pasta_monitorada"` |
| **C — upload pelo navegador, em lote** | A automação monta a pasta da competência com nomes padronizados e planilha; a pessoa arrasta para o Express no navegador. | **Comece por aqui.** Funciona hoje, sem depender de nada. Config: `modo: "lote_manual"` |

> Não consegui abrir as páginas do Portal do Cliente a partir daqui — o proxy
> desta sessão bloqueia `suporte.dominioatendimento.com` na camada de rede (403
> no CONNECT), então nenhuma ferramenta acessa. Por isso **os nomes de menu e
> botão do Onvio não estão transcritos**: os passos descrevem a ação, e você
> confirma o rótulo na tela.
>
> **Para transformar isto em passo a passo literal:** cole o texto do artigo
> **12392 — Onvio Express** em `docs/fontes/express-12392.md` (instruções em
> `docs/fontes/README.md`). É o artigo mais completo sobre o Express.
>
> Cuidado para não confundir com o **Onvio Link**, que é o sincronizador do
> **Onvio Documentos** (Windows) — outro produto, outra finalidade. Não é o
> caminho do Express.

---

## PARTE 1 — Preparação (uma vez só, 40 minutos)

**1. Instalar e validar a automação**

```bat
cd C:\CONTABIL\docauto
.venv\Scripts\activate
python -m docauto validar
python -m unittest discover -s tests -t .
```

**2. Ligar o envio em modo lote**, em `config/config.yaml`:

```yaml
envio:
  habilitado: true
  modo: "lote_manual"
  pasta_lote: "D:/CONTABIL/LOTE_EXPRESS"
  empresas_piloto: ["0001"]     # UMA empresa no primeiro dia
  limite_por_rodada: 50
  incluir_revisao: true
```

**3. Abrir o Onvio** e localizar o Express dentro do Processos. Anote o caminho
de menu que você usou — vai no procedimento da equipe.

**4. Fazer um teste com UM documento**, à mão, sem automação: suba um PDF pelo
Express e veja o que acontece. Você precisa conhecer as três telas de resultado
(vinculou / múltiplas tarefas / não achou) **antes** de subir 50 de uma vez.

**5. Procurar a pasta local do Express.** Ainda no Express, procure opção de
**download/instalação de uma pasta local** para envio automático (é o recurso
descrito no artigo 9146). Três respostas possíveis:

- **Existe e você instalou** → anote o caminho da pasta que ela criou. Vai para
  a Parte 5.
- **Existe mas depende de liberação/licença** → abra chamado, siga no lote.
- **Não encontrou** → siga no lote e pergunte no chat do suporte:
  *"O Express possui pasta local para envio automático de documentos? Onde se baixa?"*

**6. Anotar os limites** do Express (tamanho máximo por arquivo e quantidade por
lote) e refletir em `limite_por_rodada`.

---

## PARTE 2 — Rotina diária (15 a 25 minutos)

### Passo 1 — Processar a entrada

```bat
python -m docauto processar
```

Sai a lista com `[OK ]` arquivado, `[REV]` arquivado para conferir e `[PEN]`
pendência. **O arquivamento no servidor já aconteceu aqui** — o Onvio é a etapa
seguinte, não a condição.

### Passo 2 — Resolver a fila de pendências (o trabalho de verdade)

Em `PENDENTES_VALIDACAO\<MOTIVO>\`, cada arquivo tem um `.laudo.json` ao lado
dizendo o que faltou. Resolva **a causa**, não o arquivo:

| Motivo | O que fazer |
|---|---|
| `EMPRESA_NAO_IDENTIFICADA` | Cadastrar a empresa em `data/empresas.csv` (ou corrigir o CNPJ) |
| `CLASSIFICACAO_AMBIGUA` | Ver os candidatos no laudo; se for padrão recorrente, ajustar o template |
| `COMPETENCIA_NAO_IDENTIFICADA` | Documento sem rótulo de competência: subir manualmente no Onvio e arquivar à mão |
| `SEM_TEXTO` | PDF é imagem: ligar OCR (Fase 2) ou tratar manualmente |
| `FORMATO_NAO_ACEITO_PELO_EXPRESS` | Converter `.doc/.docx` em PDF e devolver à entrada |

Devolva o arquivo corrigido para `ENTRADA_DOCUMENTOS` — ele reprocessa e o
duplicado é detectado por hash, então não há risco de repetir.

### Passo 3 — Montar o lote

```bat
python -m docauto enviar --dry-run
python -m docauto enviar
```

Resultado:

```
D:\CONTABIL\LOTE_EXPRESS\2026-08\
    2026-08_DAS_EXEMPLO.pdf
    2026-08_PIS_EXEMPLO.pdf
    2026-08_COFINS_MODELO.pdf
    _CONFERIR.csv
```

### Passo 4 — Subir no Onvio Express

1. Abrir o Onvio → Processos → Express.
2. Selecionar **todos os arquivos da pasta da competência** (não o
   `_CONFERIR.csv`, e não a subpasta `_ENVIADOS`) e arrastar / usar o botão de
   upload.
3. Aguardar a análise.
4. Tratar cada resultado conforme a Parte 3.

> Respeite o `limite_por_rodada`. Se o Express aceita 20 por vez, configure 20 —
> subir 200 e ver metade falhar custa mais tempo que fazer 10 lotes.

### Passo 5 — Preencher a planilha de conferência

Abra `_CONFERIR.csv` no Excel e preencha a coluna **`tarefa_vinculada`** com uma
destas três respostas (é só isso que o sistema lê):

| Resposta | Significa |
|---|---|
| `SIM` | O Express achou a tarefa e vinculou sozinho |
| `MULTIPLA` | Apareceram várias tarefas e você escolheu |
| `NAO` | Não achou tarefa nenhuma |

Use `observacao` para o que for fora da curva. **Salve mantendo CSV com ponto e
vírgula** — o Excel costuma perguntar; responda que sim, manter o formato.

### Passo 6 — Fechar o ciclo

```bat
python -m docauto envio-confirmar --lote D:\CONTABIL\LOTE_EXPRESS\2026-08
```

O que acontece:

- `SIM` e `MULTIPLA` → item vira **CONSUMIDO** e o arquivo sai da pasta do lote
  para `_ENVIADOS\` (o que sobrou na pasta é exatamente o que ainda falta);
- `NAO` → item vira **PARADO**, com o motivo, e o arquivo **fica** na pasta;
- linha em branco → nada muda (você ainda não conferiu aquele documento).

Rodar duas vezes é seguro — nada é reenviado nem duplicado.

### Passo 7 — Olhar o placar

```bat
python -m docauto envio-status
```

```
fila de envio: 3 documento(s)
  CONSUMIDO        2   66.7%
  PARADO           1   33.3%

resultado no Express (dos que voltaram conferidos):
  VINCULADA            1   33.3%
  MULTIPLA             1   33.3%
  NAO_ENCONTRADA       1   33.3%
  (MULTIPLA alto = o gargalo é escolher a tarefa, não subir o arquivo)

PARADOS — exigem ação dentro do Onvio:
  2026-08_COFINS_MODELO.txt  (Express não encontrou tarefa — tratar dentro do Onvio)
```

---

## PARTE 3 — Os três resultados no Express

**A tarefa foi vinculada sozinha.** Nada a fazer. Marque `SIM`. É o caso que
você quer maximizar.

**Apareceram várias tarefas possíveis.** Escolha a correta na tela do Onvio.
Marque `MULTIPLA`. Se um mesmo tributo cai sempre em múltiplas tarefas, o
problema não é do arquivo — é de como as tarefas estão cadastradas no Processos
(duas tarefas abertas para a mesma obrigação e competência, por exemplo).
Anote na `observacao`: são esses casos que se resolvem **dentro do Domínio**,
não na automação.

**Não encontrou tarefa.** Marque `NAO`. Causas mais comuns, nesta ordem:
a tarefa daquela obrigação não existe/não está aberta para a competência; a
empresa não está no Processos com o mesmo CNPJ; o documento é de um tipo que
aquele escritório não acompanha por tarefa. O arquivo continua no lote e o
documento **já está arquivado no servidor** — não se perde nada.

---

## PARTE 4 — Fechamento da semana

```bat
python -m docauto relatorio
python -m docauto envio-status
```

Quatro respostas, por escrito:

1. **Algum documento foi arquivado na empresa errada?** Tem que ser zero. Se não
   for, volte o piloto para uma empresa e corrija a causa antes de seguir.
2. % automático × % pendência.
3. `VINCULADA` × `MULTIPLA` × `NAO_ENCONTRADA`.
4. Tempo gasto por dia no ciclo todo.

**O número 3 decide o mês seguinte:**

- **`VINCULADA` alto** → o processo está redondo; o próximo ganho é eliminar o
  upload manual (Parte 5).
- **`MULTIPLA` alto** → o gargalo **não é o upload**, é a escolha da tarefa.
  Automatizar upload aqui rende pouco. O caminho é arrumar o cadastro de tarefas
  no Processos e, depois, a pergunta 3 do `docs/08` (consultar tarefas em aberto
  por API para pré-identificar).
- **`NAO_ENCONTRADA` alto** → faltam tarefas cadastradas no Processos para as
  obrigações e competências. Isso se resolve dentro do Domínio, e nenhuma
  automação externa substitui.

---

## PARTE 5 — Migrar para a pasta local do Express

Quando confirmar que o recurso existe e instalar:

```yaml
envio:
  modo: "pasta_monitorada"
  pasta_monitorada: "C:/Users/<usuario>/<pasta criada pelo Express>"
  horas_para_alerta: 4
```

```bat
python -m docauto enviar --dry-run
python -m docauto enviar
python -m docauto envio-status
```

A fila continua de onde parou — o que já foi enviado não é reenviado. Daí em
diante os passos 4, 5 e 6 da rotina somem: a conciliação passa a ser automática
(arquivo que some da pasta = consumido; arquivo que fica além do prazo vira
`PARADO` e aparece nomeado no status).

**Antes de confiar nisso, uma resposta é obrigatória: o Express REMOVE o arquivo
da pasta depois de processar?** Se não remover, a conciliação por sumiço não
vale — permaneça no lote. Pasta que só acumula vira reenvio.

Agende então `scripts/enviar.bat` a cada 15 minutos (`scripts/agendar.md`).

---

## Erros comuns

| Sintoma | Causa | Correção |
|---|---|---|
| `envio desligado (envio.habilitado: false)` | Config não ligado | `habilitado: true` |
| `nada pendente para enviar` | Tudo já enviado, ou nada foi arquivado hoje | Confira `relatorio`; pendência nunca entra na fila, por segurança |
| Planilha não encontrada no `envio-confirmar` | Apontou para a pasta errada | O `--lote` é a pasta **da competência**, não a raiz do `LOTE_EXPRESS` |
| Excel destruiu o CSV | Salvou como xlsx ou trocou o separador | Salvar como CSV com `;`, UTF-8 |
| Subiu o `_CONFERIR.csv` no Express por engano | Selecionou a pasta inteira | Selecione só os PDFs; o Express vai marcar como não identificado |
| Tarefa agendada não roda | Conta do agendador sem acesso ao `\\SERVIDOR` | Rodar o `.bat` com a mesma conta antes de agendar |

---
Fonte: [Como utilizar Express? — Portal do Cliente (9146)](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=9146) · [Onvio Processos (7462)](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=7462) · [Integração Domínio Processos para Onvio (12304)](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=12304) · [Onvio Link (Onvio Documentos — não confundir)](https://www.thomsonreuters.com/pt-br/help/onvio/documents/onvio-link)
