# 06 — Lógica de classificação (árvore de decisão)

## Regra zero

**O nome do arquivo não classifica nada.** Nem é lido. Um arquivo chamado
`DAS_JULHO.pdf` que contém um DARF de COFINS será classificado como COFINS.
Nome de arquivo é a informação menos confiável que existe num escritório.

## Árvore de decisão do tipo de documento

```
Extraiu algum texto?
├── NÃO ──► SEM_TEXTO
│           PDF é imagem. Fase 1: pendência. Fase 2: OCR e recomeça.
│
└── SIM
    │
    ├─ Achou código de receita ANCORADO em rótulo ("CÓDIGO DA RECEITA: 8109")?
    │   ├── É 5952 (retenção conjunta) ──► RETENCAO_CONJUNTA ──► VALIDAÇÃO
    │   │      Uma guia, três tributos. Não existe resposta única.
    │   ├── Está na tabela ──► +30 no tributo do código, −35 nos concorrentes
    │   └── Não está na tabela ──► aviso CODIGO_RECEITA_FORA_DA_TABELA (0 ponto)
    │
    ├─ Pontua cada template:
    │     maior palavra-chave principal encontrada   (+18 a +45)
    │     palavras secundárias                       (+5 cada, teto +15)
    │     código compatível                          (+30)
    │     código de outro tributo                    (−35)
    │     anti-termos (tributo concorrente citado)   (−12 cada, teto −30)
    │
    ├─ Documento composto: se DAS pontuou ≥ 50,
    │     PIS, COFINS, IR e CSLL levam −60
    │     (o DAS contém todos eles na composição — sem esta regra,
    │      todo DAS seria ambíguo)
    │
    ├─ Melhor score < 35? ──────────────► DOCUMENTO_DESCONHECIDO ──► VALIDAÇÃO
    │
    ├─ (melhor − segundo) < 15? ────────► NECESSITA_VALIDACAO ──► VALIDAÇÃO
    │      Ex.: PIS 43 × COFINS 43 numa guia sem código legível.
    │
    ├─ Template exige subtipo (IR) e nenhum código reconhecido?
    │                        ────────────► IR + trava ──► VALIDAÇÃO
    │      IRPJ e IRRF têm destino e responsável diferentes.
    │
    └─ Caso contrário ──────────────────► TIPO DEFINIDO (+ subtipo pelo código)
```

### Em forma de regra, como você pediu

```
SE contém "SIMPLES NACIONAL" ou "DOCUMENTO DE ARRECADAÇÃO DO SIMPLES NACIONAL"
   ENTÃO DAS  (e ignore PIS/COFINS/IRPJ/CSLL citados na composição)

SE contém "PIS/PASEP" E código de receita ∈ {8109, 6912, 8301, 5979}
   ENTÃO PIS

SE contém "COFINS" E código de receita ∈ {2172, 5856, 5960}
   ENTÃO COFINS

SE contém "PIS" E contém "COFINS" E não há código legível
   ENTÃO NECESSITA_VALIDAÇÃO

SE código de receita = 5952
   ENTÃO RETENÇÃO_CONJUNTA → VALIDAÇÃO (sempre)

SE contém "IMPOSTO SOBRE A RENDA" mas nenhum código
   ENTÃO IR sem subtipo → VALIDAÇÃO

SE nenhum template chega a 35 pontos
   ENTÃO DOCUMENTO_DESCONHECIDO → VALIDAÇÃO
```

## Identificação da empresa

```
NÍVEL 1 — CNPJ  (método principal)
    Todo CNPJ do documento tem o dígito verificador conferido.
    CNPJ com DV inválido é DESCARTADO para identificação (quase sempre é
    erro de OCR) mas é REGISTRADO — é a explicação certa para o operador.
    ├── CNPJ válido e no cadastro, empresa ATIVA ──► identificada (+35)
    ├── CNPJ válido e no cadastro, empresa INATIVA ──► PENDÊNCIA
    └── CNPJ válido fora do cadastro ──► PENDÊNCIA
            "CNPJ 11.444.777/0001-61 não encontrado no cadastro"
            (cliente novo? filial? cadastrar e reprocessar)

NÍVEL 2 — RAZÃO SOCIAL   (só quando NÃO há nenhum CNPJ válido no documento)
    Compara por similaridade com razão social, fantasia, nome curto e apelidos.
    ├── ≥ 90% ──► identificada (+25)
    └── 82–90% ──► identificada porém TRAVADA: arquiva só depois de confirmação,
                   com até 3 sugestões no laudo

NÍVEL 3 — NOME FANTASIA   (mesma comparação, +15)

NÍVEL 4 — PASTA DE ORIGEM  (documento colocado à mão na pasta da empresa)
    Sempre travado. Vale como pista, nunca como prova. (+8)

NENHUM ──► EMPRESA_NAO_IDENTIFICADA
    O documento NUNCA é arquivado na pasta de uma empresa "parecida".
```

## Identificação da competência

```
PRIORIDADE 1 — campo explícito
    Rótulos: COMPETÊNCIA, MÊS/ANO, MÊS DE REFERÊNCIA, REFERÊNCIA
    Formatos: 08/2026 · 2026-08 · AGOSTO/2026 · 31/08/2026     (+20)

PRIORIDADE 2 — período de apuração
    Rótulos: PERÍODO DE APURAÇÃO, APURAÇÃO, P.A., PA           (+16)

PRIORIDADE 3 — inferida (MM/AAAA solto no documento)           (+8)
    Sempre travado: arquiva só depois de confirmação.

NÃO ENCONTRADA ──► PENDÊNCIA (COMPETENCIA_NAO_IDENTIFICADA)
```

Três proteções que já custaram caro para quem não as tinha:

1. **A data de vencimento nunca vira competência.** A janela de leitura depois do
   rótulo é cortada antes de qualquer "VENCIMENTO"/"PAGAR ATÉ". Guia de agosto
   vence em setembro; usar o vencimento erraria o mês em praticamente todo
   documento — e o erro só apareceria meses depois.
2. **Rótulo exige fronteira de palavra.** Sem isso, o rótulo `PA` casa dentro de
   `PIS/PASEP` e a automação lê a data errada da linha seguinte. Aconteceu na
   construção deste projeto; virou teste automatizado (`test_vencimento_nunca_vira_competencia`).
3. **Janela de plausibilidade** (`config.yaml`): competência mais de 60 meses no
   passado ou mais de 2 meses no futuro vai para validação. Pega erro de OCR de
   ano (2026 → 2020) e digitação.
