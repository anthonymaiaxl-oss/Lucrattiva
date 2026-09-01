# 04 — Estrutura de pastas e nomenclatura

## A estrutura proposta

```
\\SERVIDOR\CONTABIL\CLIENTES\
│
├── 0001 - EMPRESA EXEMPLO COMERCIO DE ALIMENTOS LTDA\
│   ├── _PERMANENTE\                 ← não tem competência: contrato social,
│   │                                  cartão CNPJ, procuração, certificado
│   ├── FISCAL\
│   │   └── 2026\
│   │       ├── 2026-07\
│   │       │   ├── GUIAS\           ← DAS, DARF, guias em geral
│   │       │   ├── DECLARACOES\     ← DCTF, EFD, PGDAS, recibos de entrega
│   │       │   └── NOTAS\           ← notas de entrada/saída, relatórios
│   │       └── 2026-08\
│   ├── CONTABIL\
│   ├── DP\
│   ├── SOCIETARIO\
│   └── FINANCEIRO\
│
├── 0002 - MODELO SERVICOS DE TECNOLOGIA LTDA\
└── ...

\\SERVIDOR\CONTABIL\ENTRADA_DOCUMENTOS\      ← tudo entra aqui
\\SERVIDOR\CONTABIL\PENDENTES_VALIDACAO\     ← fila de exceções, por motivo
\\SERVIDOR\CONTABIL\_REGISTRO\               ← registro.csv, logs
```

Configurável em `config.yaml`:
`caminho: "{base_empresa}/{setor}/{ano}/{competencia}/{grupo}"`.

## Por que assim, e não como no rascunho original

| Decisão | Por quê |
|---|---|
| **Pasta da empresa = `ID - RAZÃO SOCIAL`** | Empresa muda de nome (e muda mesmo). O ID nunca muda e é a chave do cadastro, do Domínio e do registro. Com o nome junto, o humano continua achando pela busca do Windows. |
| **Setor ANTES do ano** | O setor é fixo (5 pastas para sempre); o ano cresce indefinidamente. Setor primeiro = quem trabalha no fiscal abre uma pasta e vê só o que interessa. Ano primeiro obrigaria a repetir os 5 setores a cada ano. |
| **Competência como `2026-08`, não `08 - AGOSTO`** | Ordena sozinha em qualquer sistema, é curta (7 caracteres contra 12) e é exatamente o que vai no nome do arquivo — busca e pasta usam a mesma chave. Se o escritório preferir o nome por extenso, troque para `{mes} - {mes_extenso}` no config; o código já suporta. |
| **Sem subpasta por tributo** | Este é o ponto onde o rascunho original quebraria. `.../FISCAL/TRIBUTOS FEDERAIS/PIS/` significa, com 300 empresas × 12 meses × 5 tributos, **18.000 pastas**, quase todas com um arquivo dentro ou vazias. Backup mais lento, navegação pior, e o tributo já está no nome do arquivo. Se algum cliente tiver volume que justifique, ligue `subpasta_por_tributo: true` — a opção existe. |
| **Ano no caminho mesmo com a competência já contendo o ano** | Permite arquivar/mover um ano inteiro para o storage frio sem tocar no resto. |
| **`_PERMANENTE` com underscore** | Sobe para o topo da listagem e deixa claro que ali não entra documento com competência. |
| **DP, não "DEPARTAMENTO PESSOAL"** | Caminho do Windows tem limite de 260 caracteres. Nome de empresa longo + setor longo + arquivo longo estoura. A automação bloqueia (`CAMINHO_MUITO_LONGO`) antes de gravar, mas é melhor não chegar perto. |

## Nomenclatura dos arquivos

```
AAAA-MM_TIPO_EMPRESA.ext
```

| Exemplo | |
|---|---|
| `2026-08_DAS_EXEMPLO.pdf` | 23 caracteres |
| `2026-08_PIS_EXEMPLO.pdf` | |
| `2026-08_COFINS_MODELO.pdf` | |
| `2026-08_PIS_EXEMPLO_02.pdf` | segunda guia da mesma competência (parcelamento, retificadora) |

Regras aplicadas automaticamente:

- **Competência primeiro** — ordenação cronológica dentro da pasta, sem esforço.
- **`EMPRESA` é o `NOME_CURTO` do cadastro**, no máximo 24 caracteres. Repetir a
  empresa no nome parece redundante dentro da pasta dela, mas o arquivo vive
  fora dela o tempo todo: anexado em e-mail, no WhatsApp, na área de trabalho de
  alguém. Sem a empresa no nome, ninguém sabe de quem é.
- **Caracteres proibidos no Windows** (`< > : " / \ | ? *`) viram `-`; acentos são
  removidos; nomes reservados (`CON`, `PRN`, `LPT1`…) ganham `_` na frente.
- **Nunca sobrescreve.** Arquivo diferente com o mesmo nome ganha sufixo `_02`.
  Arquivo **idêntico** (mesmo hash SHA-256) é detectado como `DUPLICADO` e
  simplesmente não é copiado de novo — reprocessar a mesma pasta duas vezes não
  polui nada.
- **Comprimento total do caminho** conferido antes de gravar (limite 240 em
  `config.yaml`). Se estourar, vai para pendências em vez de falhar no meio.

## Nomes que foram descartados

| Proposta | Problema |
|---|---|
| `2026-08_EMPRESA-XYZ_PIS_GUIA_001.pdf` | 40+ caracteres, `GUIA` não informa nada (já está na pasta GUIAS), o sequencial só faz sentido quando existe repetição. |
| `PIS_2026-08_EXEMPLO.pdf` | Ordena por tributo, não por data. Numa pasta de competência, o que se quer é a data primeiro. |
| `DAS EMPRESA EXEMPLO AGOSTO.pdf` | Espaço quebra script, mês por extenso não ordena, sem o ano é ambíguo. |
