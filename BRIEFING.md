# Automação documental contábil — Domínio/Onvio Processos Express
## Briefing completo do projeto

> **Como usar este arquivo:** cole o conteúdo inteiro no Claude da empresa (como
> conhecimento de projeto, skill ou primeira mensagem). Ele é autossuficiente:
> quem ler daqui em diante entende o contexto, as regras de negócio, as decisões
> já tomadas e o que ainda está em aberto, sem precisar do repositório.
>
> Repositório: `anthonymaiaxl-oss/Lucrattiva`, branch
> `claude/contabil-doc-automation-dominio-h3njpf`.
> Documentação detalhada em `docs/01` a `docs/16`.
> Atualizado em 01/09/2026.

---

# 1. CONTEXTO

Escritório de contabilidade recém-aberto, usuário do **Domínio Processos /
Onvio**, com a funcionalidade **Express** (upload de documento que o sistema
analisa e vincula à tarefa correspondente).

**Problema:** documentos tributários chegam avulsos e alguém precisa, para cada
um: descobrir de qual empresa é, qual imposto representa, de qual competência é,
vincular à tarefa no Processos e arquivar uma cópia na pasta certa do servidor.

**Objetivo:** automatizar identificação, arquivamento e registro, aproveitando o
Express para a vinculação da tarefa, com intervenção humana só onde há dúvida
real.

**Vantagem do escritório novo:** define-se o padrão **antes** de existir bagunça.
Escritório antigo gasta 70% do esforço migrando arquivo velho; aqui é 0%.

## Princípio que orienta toda decisão

> **Documento arquivado na empresa errada custa mais caro do que documento não
> arquivado. Na dúvida, para e pergunta.**

Ordem de prioridade, sempre: **1. Confiabilidade · 2. Simplicidade ·
3. Redução de trabalho manual · 4. Aproveitar o que o escritório já tem ·
5. Implantação gradual.**

---

# 2. DIVISÃO DE RESPONSABILIDADES

| Quem | Faz | Não faz |
|---|---|---|
| **Express (Domínio/Onvio)** | Recebe documento, analisa, encontra a tarefa, vincula, pede escolha quando há mais de uma | Não organiza o servidor, não garante nome padronizado, não devolve empresa/competência para o resto do fluxo |
| **Automação externa** | Lê, extrai, classifica, identifica empresa e competência, decide se tem confiança, nomeia, arquiva, registra, separa exceções | Não recria o Express, não simula cliques como primeira opção, não adivinha |
| **Pessoa (fiscal)** | Resolve a fila de pendências, confirma casos ambíguos, mantém o cadastro | Não fica renomeando e arrastando arquivo bom |

A automação complementa o Express nos dois pontos em que ele não atua: o
**antes** (padronizar e pré-identificar) e o **depois** (arquivar no servidor e
registrar).

---

# 3. FLUXO COMPLETO

```
/ENTRADA_DOCUMENTOS  (arquivo novo)
        |
   [1] LEITURA        PDF nativo -> texto | PDF imagem -> OCR (Fase 2)
                      XLSX/TXT -> texto  | DOC/DOCX -> pendência (Express não lê)
        |
   [2] EXTRAÇÃO       CNPJ (dígito verificador conferido), razão social,
                      competência, valor, vencimento, código de receita
        |
   [3] CLASSIFICAÇÃO  templates + tabela de códigos + desempate
                      -> DAS | PIS | COFINS | IR | CSLL
                      -> ou NECESSITA_VALIDACAO / DESCONHECIDO
        |
   [4] EMPRESA        CNPJ > razão social > nome fantasia > pasta de origem
        |
   [5] COMPETÊNCIA    campo explícito > período de apuração > inferida
                      (vencimento NUNCA vira competência)
        |
   [6] CONFIANÇA + TRAVAS
        |
   +----+--------------------------------+
   |                                     |
sem trava e score alto            qualquer trava
   |                                     |
[7] NOME PADRONIZADO           /PENDENTES_VALIDACAO/<MOTIVO>/
[8] ARQUIVAMENTO                + arquivo.laudo.json
    servidor + Dropbox            (motivo, candidatos, sugestões)
   |                                     |
[9] FILA DE ENVIO ao Express        pessoa resolve a CAUSA
   |                                     |
[10] REGISTRO em registro.csv <---------+
```

---

# 4. ESTRUTURA DE PASTAS

```
\\SERVIDOR\CONTABIL\CLIENTES\
├── 0001 - EMPRESA EXEMPLO COMERCIO DE ALIMENTOS LTDA\
│   ├── _PERMANENTE\              contrato social, cartão CNPJ, procuração
│   ├── FISCAL\
│   │   └── 2026\
│   │       └── 2026-08\
│   │           ├── GUIAS\        DAS, DARF, guias em geral
│   │           ├── DECLARACOES\  DCTF, EFD, PGDAS, recibos
│   │           └── NOTAS\
│   ├── CONTABIL\  DP\  SOCIETARIO\  FINANCEIRO\
└── 0002 - ...

\\SERVIDOR\CONTABIL\ENTRADA_DOCUMENTOS\    tudo entra aqui
\\SERVIDOR\CONTABIL\PENDENTES_VALIDACAO\   fila de exceções, por motivo
\\SERVIDOR\CONTABIL\LOTE_EXPRESS\          lotes prontos para subir no Onvio
```

Configurável: `caminho: "{base_empresa}/{setor}/{ano}/{competencia}/{grupo}"`.

## Justificativa de cada decisão

| Decisão | Por quê |
|---|---|
| Pasta = `ID - RAZÃO SOCIAL` | Empresa muda de nome; o ID nunca muda e é a chave do cadastro, do Domínio e do registro |
| Setor **antes** do ano | Setor é fixo (5 pastas); ano cresce sempre. Ano primeiro obrigaria a repetir os 5 setores todo ano |
| Competência `2026-08` | Ordena sozinha, curta, é a mesma chave do nome do arquivo |
| **Sem subpasta por tributo** | 300 empresas × 12 meses × 5 tributos = 18.000 pastas quase vazias. O tributo já está no nome do arquivo. Existe a opção `subpasta_por_tributo: true` se algum cliente justificar |
| Ano no caminho, mesmo com a competência contendo o ano | Permite mover um ano inteiro para storage frio |
| `DP` e não `DEPARTAMENTO PESSOAL` | Limite de 260 caracteres do Windows |

## Nomenclatura

```
AAAA-MM_TIPO_EMPRESA.ext      →  2026-08_DAS_EXEMPLO.pdf   (23 caracteres)
                                 2026-08_PIS_EXEMPLO_02.pdf (2ª guia da competência)
```

- Competência primeiro: ordenação cronológica na pasta.
- `EMPRESA` = `NOME_CURTO` do cadastro, até 24 caracteres. Parece redundante
  dentro da pasta da empresa, mas o arquivo vive fora dela o tempo todo
  (e-mail, WhatsApp, área de trabalho).
- Caracteres proibidos no Windows (`< > : " / \ | ? *`) viram `-`; acentos
  removidos; nomes reservados (`CON`, `LPT1`…) ganham `_` na frente.
- **Nunca sobrescreve:** arquivo diferente com mesmo nome ganha `_02`; arquivo
  idêntico (SHA-256) é `DUPLICADO` e não é copiado de novo.
- Comprimento total do caminho conferido antes de gravar (limite 240).

---

# 5. CADASTRO CENTRAL DE EMPRESAS

Arquivo: `data/empresas.csv` (CSV com `;`). **É a peça mais importante do
projeto** — CNPJ errado aqui manda documento para a empresa errada.

| Coluna | Obrigatória | Observação |
|---|---|---|
| `ID_EMPRESA` | ✅ | 4 dígitos. **Nunca muda, nunca é reaproveitado** |
| `CODIGO_DOMINIO` | recomendada | Código da empresa dentro do Domínio; é o que permite conciliar depois |
| `RAZAO_SOCIAL` | ✅ | Como no cartão CNPJ. Vira o nome da pasta |
| `NOME_FANTASIA` | | Nível 3 de identificação |
| `NOME_CURTO` | ✅ | Até 24 caracteres, para o nome do arquivo |
| `CNPJ` | ✅ | Dígito verificador é conferido |
| `REGIME_TRIBUTARIO` | ✅ | SIMPLES NACIONAL / LUCRO PRESUMIDO / LUCRO REAL / MEI |
| `CAMINHO_BASE` | | Só para empresa com pasta fora do padrão |
| `SETOR_PADRAO` | | FISCAL no MVP |
| `ATIVA` | ✅ | Inativa não recebe arquivo automático |
| `APELIDOS` | | Variações separadas por `\|` — resolve o cliente que assina de três jeitos |

**Por que CSV no MVP:** abre no Excel, todo mundo edita, versiona, não corrompe,
não depende de internet nem licença. Migrar para SQLite quando passar de ~300
empresas ou quando duas pessoas precisarem editar ao mesmo tempo.

Conferência obrigatória antes de rodar: `python -m docauto validar` — acusa CNPJ
vazio, inválido, duplicado e razão social vazia. **Não processe nada com essa
lista não zerada.**

---

# 6. CLASSIFICAÇÃO DO DOCUMENTO

## Regra zero

**O nome do arquivo não classifica nada — nem é lido.** Um arquivo chamado
`DAS_JULHO.pdf` contendo um DARF de COFINS é classificado como COFINS.

## Árvore de decisão

```
Extraiu texto?
├── NÃO ──► SEM_TEXTO (PDF é imagem; Fase 1 pendência, Fase 2 OCR)
└── SIM
    ├─ Código de receita ANCORADO em rótulo ("CÓDIGO DA RECEITA: 8109")?
    │   ├── 5952 (retenção conjunta) ──► RETENCAO_CONJUNTA ──► VALIDAÇÃO sempre
    │   ├── Está na tabela ──► +30 no tributo do código, −35 nos concorrentes
    │   └── Fora da tabela ──► aviso, 0 ponto
    ├─ Pontua cada template:
    │     maior palavra-chave principal encontrada  (+18 a +45)
    │     palavras secundárias                      (+5 cada, teto +15)
    │     código compatível                         (+30)
    │     código de outro tributo                   (−35)
    │     anti-termos (tributo concorrente citado)  (−12 cada, teto −30)
    ├─ DAS pontuou ≥ 50 → PIS, COFINS, IR e CSLL levam −60
    │     (o DAS CONTÉM todos na composição; sem isso todo DAS seria ambíguo)
    ├─ Melhor score < 35 ──────────► DOCUMENTO_DESCONHECIDO ──► VALIDAÇÃO
    ├─ (melhor − segundo) < 15 ────► NECESSITA_VALIDACAO ──► VALIDAÇÃO
    ├─ IR sem código de receita ───► IR + trava ──► VALIDAÇÃO
    │     (IRPJ e IRRF têm destino e responsável diferentes)
    └─ Caso contrário ─────────────► TIPO DEFINIDO (+ subtipo pelo código)
```

## Em forma de regra

```
SE contém "SIMPLES NACIONAL" ou "DOCUMENTO DE ARRECADAÇÃO DO SIMPLES NACIONAL"
   ENTÃO DAS (e ignore PIS/COFINS/IRPJ/CSLL citados na composição)
SE contém "PIS/PASEP" E código ∈ {8109, 6912, 8301, 5979}   ENTÃO PIS
SE contém "COFINS"    E código ∈ {2172, 5856, 5960}         ENTÃO COFINS
SE contém "PIS" E "COFINS" E não há código legível          ENTÃO VALIDAÇÃO
SE código = 5952                                            ENTÃO VALIDAÇÃO sempre
SE contém "IMPOSTO SOBRE A RENDA" mas nenhum código         ENTÃO VALIDAÇÃO
SE nenhum template chega a 35 pontos                        ENTÃO DESCONHECIDO
```

## Identificação da empresa

```
NÍVEL 1 — CNPJ (principal). Dígito verificador conferido.
   CNPJ inválido é DESCARTADO para identificação (quase sempre erro de OCR)
   mas REGISTRADO — é a explicação certa para o operador.
   ├── válido, cadastrado, ATIVA ──► identificada          (+35)
   ├── válido, cadastrado, INATIVA ──► PENDÊNCIA
   └── válido fora do cadastro ──► PENDÊNCIA
NÍVEL 2 — RAZÃO SOCIAL (só quando NÃO há CNPJ válido no documento)
   ├── ≥ 90% de similaridade ──► identificada              (+25)
   └── 82–90% ──► identificada porém TRAVADA, com 3 sugestões no laudo
NÍVEL 3 — NOME FANTASIA                                     (+15)
NÍVEL 4 — PASTA DE ORIGEM (sempre travado; é pista, não prova) (+8)
NENHUM ──► EMPRESA_NAO_IDENTIFICADA
   O documento NUNCA é arquivado na pasta de uma empresa "parecida".
```

## Identificação da competência

```
1. Campo explícito  (COMPETÊNCIA, MÊS/ANO, REFERÊNCIA)      (+20)
2. Período de apuração (PERÍODO DE APURAÇÃO, APURAÇÃO, PA)  (+16)
3. Inferida (MM/AAAA solto) — sempre travada               (+8)
NÃO ENCONTRADA ──► PENDÊNCIA
```

Três proteções que já custaram caro a quem não as tinha:

1. **A data de vencimento nunca vira competência.** A janela de leitura é
   cortada antes de qualquer "VENCIMENTO"/"PAGAR ATÉ". Guia de agosto vence em
   setembro; usar o vencimento erraria o mês em quase todo documento — e o erro
   só apareceria meses depois.
2. **Rótulo exige fronteira de palavra.** Sem isso o rótulo `PA` casa dentro de
   `PIS/PASEP` e a automação lê a data errada. Aconteceu na construção; virou
   teste automatizado.
3. **Janela de plausibilidade:** mais de 60 meses no passado ou 2 no futuro vai
   para validação. Pega erro de OCR de ano e digitação.

---

# 7. TEMPLATES

Um arquivo YAML por tipo em `config/templates/`. O contador edita; ninguém
precisa mexer em código.

| Campo | Serve para |
|---|---|
| `id` | Nome curto usado no arquivo e nas pastas |
| `setor` / `grupo` | Onde arquivar (FISCAL / GUIAS) |
| `precedencia` | Desempate quando dois templates empatam |
| `suprime` | Tributos que este documento contém (só o DAS usa) |
| `palavras_chave_principais` | Termo + peso; `caixa_alta: true` exige maiúscula no original |
| `palavras_chave_secundarias` | +5 cada, teto +15 |
| `anti_termos` | Termos de OUTRO tributo; puxam o score para baixo |
| `campos_obrigatorios` | Sem eles vai para pendência mesmo com score alto |
| `criterios_confiavel` / `criterios_validacao_manual` | Documentação para humano |

Os **códigos de receita ficam num arquivo só** (`config/codigos_receita.yaml`):
quando a Receita muda um código, corrige-se uma linha e todos os templates
acompanham.

## Os cinco templates

**DAS** — principais: "DOCUMENTO DE ARRECADAÇÃO DO SIMPLES NACIONAL" (45),
"SIMPLES NACIONAL" (35), "PGDAS-D" (35), "DAS" caixa alta (25). Secundárias:
composição do documento, período de apuração, número do documento, CNPJ matriz,
receita bruta, CPP. Obrigatórios: CNPJ, competência. **Regra decisiva:**
`suprime: [PIS, COFINS, IR, CSLL]`.

**PIS** — principais: PIS/PASEP, PIS-PASEP, PROGRAMA DE INTEGRAÇÃO SOCIAL,
CONTRIBUIÇÃO PARA O PIS (40); "PIS" caixa alta (28). Anti-termos: COFINS, CSLL.
Códigos: 8109 faturamento, 6912 não cumulativo, 8301 folha, 5979 retido.
Obrigatórios: CNPJ, competência, valor.

**COFINS** — principais: CONTRIBUIÇÃO PARA O FINANCIAMENTO DA SEGURIDADE SOCIAL
(45), COFINS (40). Anti-termos: PIS/PASEP, CSLL. Códigos: 2172, 5856, 5960.

**IR** — principais: IMPOSTO SOBRE A RENDA / DE RENDA (40), IRPJ e IRRF caixa
alta (40), "IR" caixa alta (18 — sigla curta demais). Códigos IRPJ: 2089, 2362,
0220, 5625; IRRF: 0561, 0588, 1708, 3208. **`exige_subtipo: true`** — sem código
legível não se separa IRPJ de IRRF, e vai para validação mesmo com score alto.

**CSLL** — principais: CONTRIBUIÇÃO SOCIAL SOBRE O LUCRO LÍQUIDO (45), CSLL
caixa alta (40). Anti-termos: IMPOSTO SOBRE A RENDA, COFINS, PIS. Códigos: 2372,
2484, 6012, 5987. Erro mais comum na prática: IRPJ e CSLL na mesma guia sem
código legível.

## Como PIS e COFINS deixam de se confundir

Três camadas, nesta ordem: (1) **código de receita ancorado** — número de 4
dígitos solto (ano, CEP, agência) é ignorado de propósito; (2) **anti-termos**;
(3) **margem de desempate** — a menos de 15 pontos, resultado é
`NECESSITA_VALIDACAO`. Nunca se escolhe "o mais provável".

## Calibrar com as suas guias

Cada emissor formata diferente. O comando `diagnosticar` mostra **por que** cada
documento foi classificado assim, e `--texto` salva o texto normalizado — é dele
que saem as palavras-chave (você lê o que o robô lê, não o que o PDF aparenta).

Ciclo: 10 amostras reais por tipo → `diagnosticar` → ajustar o YAML → repetir
até acertar os 10. Ordem sugerida: DAS primeiro (maior volume, mais fácil),
depois PIS e COFINS **em par** (o anti-termo de um é o principal do outro), IR e
CSLL por último.

Regras que evitam estrago:
1. **Termo curto exige `caixa_alta: true`.** "DAS", "PIS", "IR", "ME" aparecem
   como palavra comum em português; sem isso, *todo* documento "contém DAS".
2. **Não suba peso para resolver empate** — a saída certa é anti-termo ou código.
3. **Não crie template novo para variação do mesmo tributo** — PIS faturamento e
   PIS folha são o mesmo template, separados por subtipo via código.
4. Mexeu no template, rode os testes.

Um tipo está calibrado quando, nas 10 amostras: **nenhuma** foi classificada
como tributo errado (inegociável), pelo menos 8 saíram com tipo e competência
certos, e as que caíram em validação caíram por motivo explicável.

---

# 8. SISTEMA DE CONFIANÇA

Duas camadas **independentes**: score (prioriza a fila) e travas (bloqueiam).
**Score alto nunca compra o direito de arquivar com dúvida.**

| Evidência | Pontos |
|---|---|
| Empresa por **CNPJ** válido e cadastrado | **+35** |
| Empresa por razão social ≥ 90% | +25 |
| Empresa por nome fantasia | +15 |
| Empresa por razão social 82–90% | +12 |
| Empresa por pasta de origem | +8 |
| CNPJ válido fora do cadastro | +5 |
| **Tipo do documento** (proporcional ao score do template) | **até +30** |
| Competência de campo explícito | +20 |
| Competência de período de apuração | +16 |
| Competência inferida | +8 |
| Valor total localizado | +6 |
| Vencimento localizado | +4 |
| _Multiplicador:_ texto por OCR | ×0,85 |
| _Multiplicador:_ texto com menos de 200 caracteres | ×0,70 |

| Score | Decisão |
|---|---|
| **≥ 85** | `AUTOMATICO` — arquiva; conferência por amostragem |
| **65–84** | `ARQUIVADO_COM_REVISAO` — arquiva **e** entra na lista da semana |
| **< 65** | `PENDENTE_VALIDACAO` — não arquiva na empresa |

## Travas (passam por cima do score)

`EMPRESA_NAO_IDENTIFICADA` · `EMPRESA_POR_SEMELHANCA_FRACA` ·
`EMPRESA_APENAS_PELA_PASTA` · `CLASSIFICACAO_AMBIGUA` · `DOCUMENTO_DESCONHECIDO` ·
`RETENCAO_CONJUNTA` · `COMPETENCIA_NAO_IDENTIFICADA` · `COMPETENCIA_INFERIDA` ·
`COMPETENCIA_FORA_DA_JANELA` · `CAMPOS_OBRIGATORIOS_AUSENTES` · `SEM_TEXTO` ·
`FORMATO_NAO_ACEITO_PELO_EXPRESS` · `CAMINHO_MUITO_LONGO` · `DESTINO_INDISPONIVEL`

## Calibração do score

Com 50 documentos já conferidos, meça em ordem de importância:
**falso positivo** (arquivou errado) — meta **zero**, um único caso já é motivo
para apertar; **falso negativo** (mandou para pendência algo certo) — tolerável,
é trabalho manual, não erro.

**Primeiro zero erro, depois menos fila.** Um fluxo que manda 30% para pendência
e nunca erra já economiza 70% do trabalho e mantém a confiança da equipe. Um que
automatiza 100% e erra 2% destrói a confiança na primeira semana — e aí ninguém
mais usa.

---

# 9. ENVIO AO EXPRESS (ONVIO)

## Dois modos, a mesma fila

| Modo | Como funciona | Quando |
|---|---|---|
| `lote_manual` | Monta pasta por competência + planilha `_CONFERIR.csv`; a pessoa arrasta para o Express no navegador | **Comece por aqui** — funciona hoje, sem depender de confirmação |
| `pasta_monitorada` | Copia para a pasta local que o Express varre | Quando confirmado que o recurso existe na sua conta |

Trocar de um para o outro é **uma linha de config**; a fila continua de onde
parou e nada é reenviado.

## Estados da fila

`PENDENTE` → `ENVIADO` → `CONSUMIDO` (Express pegou) · `PARADO` (passou do
prazo ou não achou tarefa) · `BLOQUEADO` (arquivo sumiu do servidor).

## Travas do envio (no código, não dependem de disciplina)

- **Só documento arquivado entra na fila.** Pendência nunca é enviada — o
  Express receberia algo que o escritório ainda não confirmou de quem é.
- **Idempotência por SHA-256.** O mesmo documento nunca entra duas vezes, por
  mais que a pasta de entrada seja reprocessada.
- `empresas_piloto` limita o alcance sem tocar em código.
- `limite_por_rodada` respeita o limite de lote do Express.
- `enviar --dry-run` testa toda mudança antes de valer.

## Rotina diária (15–25 min)

```
1. processar                 arquiva no servidor (+ Dropbox) e enfileira
2. resolver pendências       corrige a CAUSA, devolve o arquivo à entrada
3. enviar                    monta a pasta da competência + _CONFERIR.csv
4. subir no Onvio Express    arrasta só os PDFs, respeitando o limite de lote
5. preencher a planilha      SIM | MULTIPLA | NAO na coluna tarefa_vinculada
6. envio-confirmar --lote    fecha o ciclo
7. envio-status              placar
```

`envio-confirmar` existe porque em produto **web** não há pasta para observar:
quem sabe se o Express vinculou é a pessoa que subiu. `SIM`/`MULTIPLA` viram
CONSUMIDO e o arquivo sai para `_ENVIADOS` (o que sobra na pasta é o que ainda
falta); `NAO` vira PARADO com o motivo e o arquivo fica. Rodar duas vezes é
seguro.

## Os três resultados no Express

- **Vinculou sozinho** → `SIM`. É o que se quer maximizar.
- **Várias tarefas possíveis** → escolha na tela, marque `MULTIPLA`. Se um mesmo
  tributo sempre cai aqui, o problema é o **cadastro de tarefas no Processos**
  (duas tarefas abertas para a mesma obrigação e competência, por exemplo).
- **Não achou tarefa** → `NAO`. Causas: tarefa não existe/não está aberta para a
  competência; empresa não está no Processos com o mesmo CNPJ; tipo que o
  escritório não acompanha por tarefa. **O documento já está arquivado no
  servidor — nada se perde.**

## O número que decide o mês seguinte

- **`VINCULADA` alto** → processo redondo; próximo ganho é eliminar o upload manual.
- **`MULTIPLA` alto** → o gargalo **não é o upload**, é escolher a tarefa.
  Automatizar upload rende pouco; arrume o cadastro de tarefas no Processos.
- **`NAO_ENCONTRADA` alto** → faltam tarefas cadastradas. Resolve-se dentro do
  Domínio; nenhuma automação externa substitui.

---

# 10. CÓPIAS: SERVIDOR + DROPBOX

O Dropbox instalado é uma pasta local comum — a automação copia como copia para
o servidor, e quem sincroniza é o Dropbox.

```yaml
destinos:
  - nome: "SERVIDOR"
    raiz: "D:/CONTABIL/CLIENTES"
    principal: true
  - nome: "DROPBOX"
    raiz: "C:/Users/SEU_USUARIO/Dropbox/CONTABIL/CLIENTES"
    principal: false
```

Mesma estrutura e nome nos dois. **Se o Dropbox estiver fora do ar o documento
não vira pendência** — já está no servidor; a cópia entra na fila de espelho e
`docauto espelhar` refaz.

## A ordem importa

Se a **pasta do Express for o ponto de entrada** e o Express apagar o arquivo
após subir, abre-se uma corrida:

```
09:00:00  pessoa solta a guia na pasta do Express
09:00:20  Express sobe e APAGA o arquivo
09:02:00  automação roda e não encontra nada
          → vinculado no Onvio e NUNCA arquivado no servidor
```

E **ninguém fica sabendo** — não se registra a falta de um arquivo que nunca se
viu. **Ordem correta:**

```
ENTRADA_DOCUMENTOS → servidor → Dropbox → pasta do Express → Onvio
```

Truque prático: se a equipe já se acostumou com a "pasta do Express", crie um
**atalho chamado "Express" apontando para `ENTRADA_DOCUMENTOS`**.

Vigiar a pasta do Express é suportado (`pastas.entrada` aceita lista), mas só
faça isso se confirmar que o Express **não apaga** os arquivos.

## Cuidados antes de ligar o Dropbox

1. **Caminho longo** — `C:\Users\Fulano\Dropbox\...` chega mais rápido ao limite
   de 260 do Windows. Prefira raiz curta (`C:\Dropbox\CONTABIL`).
2. **Espaço e plano** — confira antes.
3. **LGPD** — guia fiscal tem dado de terceiro: conta **do escritório**, com
   compartilhamento controlado, nunca conta pessoal de funcionário.

---

# 11. CONFERIR CONTRA O ONVIO (SEM SENHA)

Não é possível dar acesso à conta do Onvio a uma IA, e credencial do Onvio dá
acesso aos dados fiscais dos clientes — não deve ser compartilhada. **Mas o
objetivo é atingível:** o Onvio exporta as listas, e o cruzamento está
automatizado.

Exporte **empresas** (código, razão, fantasia, CNPJ, regime, situação) e
**tarefas/obrigações** (empresa, obrigação, competência, setor), em CSV ou XLSX.
Colunas em qualquer ordem e nome razoável — o leitor reconhece variações.

```bat
REM montar o cadastro a partir do Onvio, sem digitar nada
python -m docauto onvio-conferir --empresas data\onvio\empresas.csv ^
                                 --gerar-cadastro data\empresas.csv

REM conferir os dois lados
python -m docauto onvio-conferir --empresas data\onvio\empresas.csv ^
                                 --tarefas  data\onvio\tarefas.csv
```

| Divergência | Consequência |
|---|---|
| `FALTA_NO_CADASTRO` | Todo documento dessa empresa vira pendência — causa nº 1 de fila grande |
| `FALTA_NO_ONVIO` | Arquiva certo, mas o Express nunca acha tarefa |
| `RAZAO_DIFERENTE` | Identificação por nome falha; resolva com `APELIDOS` |
| `CODIGO_DOMINIO_DIFERENTE` | Conciliação futura com o Domínio quebra |
| `CNPJ_INVALIDO_NO_ONVIO` | Erro dentro do próprio Onvio — corrigir lá |
| `templates_sem_tarefa` | O Express devolverá "não encontrada" para esse tributo |
| `sem_template` | Obrigação que a automação ainda não classifica — fila de templates novos, por volume |

**Rode isso antes da primeira semana de operação.**

---

# 12. COMANDOS

```bat
scripts\instalar.bat                   REM Windows: ambiente, dependências, config, pastas
python -m docauto doutor                REM o que falta para funcionar NESTE computador
python -m docauto validar               REM confere o cadastro
python -m docauto estrutura --ano 2026  REM cria a árvore de pastas
python -m docauto diagnosticar --entrada C:\amostras --texto C:\amostras\_texto
python -m docauto processar --dry-run   REM simula, não copia nada
python -m docauto processar             REM para valer
python -m docauto relatorio             REM % automático, pendências por motivo
python -m docauto enviar --dry-run
python -m docauto enviar                REM monta o lote / copia para a pasta monitorada
python -m docauto envio-confirmar --lote D:\CONTABIL\LOTE_EXPRESS\2026-08
python -m docauto envio-status          REM o que o Express consumiu e o que travou
python -m docauto espelhar              REM refaz cópias que falharam
python -m docauto onvio-conferir --empresas ... [--tarefas ...] [--gerar-cadastro ...]
scripts\agendar.bat                     REM tarefas do Windows (como administrador)
python -m unittest discover -s tests -t .   REM 99 testes
```

`doutor` confere cadastro, templates, tabela de códigos, leitor de PDF e
planilha, OCR, cada pasta de entrada, cada destino com espaço livre, o pior caso
do limite de caminho e a configuração de envio — **testando escrita de verdade**,
não permissão declarada. Reprova o ambiente (saída 1) enquanto houver erro.

---

# 13. TECNOLOGIA E POR QUE ESTA

| Escolha | Motivo |
|---|---|
| **Python + biblioteca padrão** | Roda no servidor sem servidor web, banco ou Docker |
| **Regras em YAML/CSV, não no código** | O contador ajusta palavra-chave, código e caminho sem programador. É isso que faz a automação sobreviver ao primeiro mês |
| **CSV para o cadastro no MVP** | Excel abre, versiona, não corrompe |
| **Agendador do Windows a cada 10 min** | Mais confiável que serviço com watchdog: se cair, o agendador volta |
| **n8n só na Fase 4** | Ótimo para avisos; ruim para regra fiscal fina, que fica em texto versionado |
| **OCR só na Fase 2** | Metade dos DAS/DARF tem texto nativo; ligar OCR no dia 1 dobra a complexidade antes de o simples estar provado |

**Fora do MVP de propósito:** IA generativa classificando documento (entra
depois, como **desempate**, nunca como primeira decisão — modelo que erra em
silêncio é pior que fila de pendência); DP, Contábil e Societário (estrutura
pronta, conteúdo depois); mover ou apagar o original (nos primeiros 60 dias só
copia).

---

# 14. REGRAS INVIOLÁVEIS

1. Nunca sobrescrever documento.
2. Nunca apagar o original (`modo_original: copiar` nos primeiros 60 dias).
3. Nunca arquivar em empresa cujo CNPJ não foi validado e encontrado.
4. Vencimento nunca vira competência.
5. Nunca inventar classificação — empate vai para validação.
6. Na dúvida, `PENDENTE_VALIDACAO`.
7. Nunca relaxar uma trava para reduzir fila — a fila é sintoma; a causa está no
   cadastro ou no template.
8. Nunca pular a conferência da tabela de códigos antes de abrir para a carteira.
9. Nunca compartilhar credencial do Onvio.
10. Backup testado antes de trocar `copiar` por `mover`.

---

# 15. PENDÊNCIAS E DECISÕES EM ABERTO

| Item | Situação | Quem resolve |
|---|---|---|
| **Tabela de códigos de receita** | `NAO_CONFERIDA` — códigos de uso corrente, não conferidos contra a tabela oficial da RFB. Enquanto assim, todo documento classificado por código recebe aviso no registro | Escritório, antes de abrir para a carteira |
| **Pasta local do Express** | O artigo oficial 9146 do Portal do Cliente menciona **baixar e usar uma pasta local** para envio automático. Falta confirmar se está disponível na conta e como se instala | Escritório, na tela ou no chat do suporte |
| **Express remove o arquivo após subir?** | Não confirmado. **Decisivo:** se não remover, a conciliação por sumiço não vale e deve-se ficar no lote | Suporte Thomson Reuters |
| **API para Processos/Express** | Existe Central do Desenvolvedor e Onvio BR Accounting API, mas a documentação pública trata de documentos fiscais de ERP (XML/TXT) e folha. **Não há confirmação de endpoint para vincular documento a tarefa** | Chamado na Thomson Reuters |
| **Limites do Express** | Tamanho máximo e nº de arquivos por lote — vão direto para `limite_por_rodada` | Artigo 9146 |
| **Rótulos de tela do Onvio** | Não transcritos. O ambiente onde esta documentação foi escrita não tem acesso de rede a `suporte.dominioatendimento.com` (bloqueio de saída, 403 no CONNECT). O artigo mais completo é o **12392 — Onvio Express** | Colar o texto do artigo em `docs/fontes/express-12392.md` (ver `docs/fontes/README.md`) e o passo a passo vira literal |

## Perguntas para o chamado na Thomson Reuters

1. Existe API oficial para **enviar documento e vinculá-lo a uma tarefa** do
   Domínio Processos? Qual documentação e como obter credencial?
2. A Onvio BR Accounting API cobre **Processos/Express** ou só documentos
   fiscais de ERP e folha?
3. É possível **consultar por API as tarefas em aberto** de uma empresa
   (competência, obrigação, situação)?
4. Existe ambiente de **homologação**?
5. O Express possui **monitoramento de pasta local**? Como se configura, qual a
   frequência de varredura, o limite por lote, e **o arquivo é removido** após o
   processamento?
6. Existe **importação em lote** por planilha ou arquivo de índice?
7. Enviar metadados (CNPJ, competência, código de receita) **melhora** a
   identificação da tarefa?
8. Lista oficial de **formatos e limites** aceitos (tamanho, páginas, PDF com
   senha, PDF assinado)?
9. Dá para **consultar o resultado** do processamento fora da tela?
10. Há **parceiro homologado** para esse tipo de integração, e integração
    própria fere alguma cláusula contratual ou de suporte?

**Registre a resposta por escrito.** Decisão de arquitetura tomada por telefone
é decisão que ninguém consegue defender seis meses depois.

---

# 16. INDICADORES

| Indicador | Meta mês 1 | Meta mês 6 |
|---|---|---|
| **Erro de destino** (empresa/competência errada) | **0** | **0** |
| % automático | 60–70% | 85–90% |
| % pendente | 30–40% | 10–15% |
| Tempo por documento (manual) | — | < 30 s |
| Fila parada > 2 dias | 0 | 0 |

O primeiro é o único inegociável. Os outros são otimização.

## Os cinco erros que matam esse tipo de projeto

1. Ligar tudo de uma vez.
2. Deixar a fila de pendências sem dono — ela cresce, viram 300 arquivos,
   ninguém olha mais, e o projeto morre mesmo funcionando.
3. Relaxar trava para reduzir fila.
4. Mudar o padrão de pastas depois de 6 meses.
5. Depender da integração com o Express para começar — o arquivamento vale por
   si só desde o primeiro dia.

---

# 17. COMO PEDIR AJUDA A PARTIR DAQUI

Prompts que funcionam bem com este contexto carregado:

- *"Crie o template do INSS/GPS seguindo o padrão dos cinco existentes, com
  palavras-chave principais, secundárias, anti-termos e critérios de validação."*
- *"Estou com 40% de pendências por `CLASSIFICACAO_AMBIGUA` entre IRPJ e CSLL.
  Que ajuste você faria nos templates?"*
- *"Escreva o procedimento de uma página para a equipe, só a rotina diária."*
- *"Revise minha estrutura de pastas para incluir Departamento Pessoal sem
  quebrar o limite de caminho do Windows."*
- *"Monte o texto do chamado para a Thomson Reuters sobre a pasta local do
  Express."*

**Ao pedir mudança de regra, informe sempre:** qual documento real motivou, o
que saiu, o que deveria sair. Regra fiscal ajustada no abstrato é regra que
quebra outro caso.
