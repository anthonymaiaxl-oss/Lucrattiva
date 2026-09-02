# 17 — Guia de campo: os 5 primeiros dias no Express

Para executar **na empresa**, 4h por dia, com o Claude aberto ao lado.
Complementa o `docs/12` (rotina) e o `docs/11` (plano da semana).

---

## Concordo com o plano. Três correções que mudam o resultado

### 1. Escolha o documento de teste a partir da TAREFA, não do documento

Esta é a correção mais importante do guia inteiro.

O instinto é pegar um DAS antigo qualquer e subir. O problema: se **não existir
tarefa aberta** para aquela empresa naquela competência, o Express vai devolver
"não encontrada" — e você vai passar três horas mexendo em template achando que
o problema é o documento, quando é o cadastro de tarefas.

**Faça o caminho inverso:**

```
1. Abra o Processos e ache uma TAREFA ABERTA de DAS, de uma empresa qualquer,
   de uma competência qualquer.
2. Anote: empresa, CNPJ, competência, nome exato da tarefa.
3. AGORA procure o DAS daquela empresa, daquela competência.
4. Suba esse.
```

Assim o primeiro teste é justo: se falhar, o problema está mesmo no
reconhecimento — que é o que você quer estudar. Você isolou a variável.

### 2. O Dia 1 pode terminar com o DAS funcionando

Seu Dia 1 reserva 4h para "entender como o Express está configurado hoje".
Boa parte disso sai de exportação, em 30 minutos, não em 4 horas:

```bat
python -m docauto onvio-conferir --empresas data\onvio\empresas.csv ^
                                 --tarefas  data\onvio\tarefas.csv
```

Isso te dá, de uma vez: quantas empresas existem, quais obrigações estão
cadastradas, quais tributos **não têm tarefa nenhuma** (esses vão devolver "não
encontrada" sempre — e não é culpa do template). Sobram ~3h do Dia 1 para
atacar o DAS. Ou seja: **o seu "cenário mais rápido" de 2 dias é o cenário
normal**, se você começar pela exportação.

### 3. Registre o estado ANTES de mexer em qualquer configuração

Você entrou agora. Se mexer num template que já existe e o reconhecimento piorar
na semana seguinte, ninguém vai saber o que mudou — e a conta vai sobrar para
você.

Antes de alterar qualquer coisa: print da tela, ou anote em texto a configuração
atual. Prefira **criar novo** a **editar existente**. Se precisar editar, uma
alteração por vez, com um teste entre elas.

### E uma quarta, que não é técnica

**Combine a meta antes de começar.** Diga ao escritório, no Dia 1:

> "Vou medir quanto o Express reconhece hoje, sem mudar nada. Esse número é o
> ponto de partida. Se vier baixo, é diagnóstico, não defeito."

Sem isso, um resultado de 40% no Dia 5 parece fracasso seu. Com isso, o mesmo
40% vira "descobrimos que 60% das obrigações não estão cadastradas como tarefa"
— que é um achado valioso e não é problema seu para resolver sozinho.

---

## DIA 1 — Terreno + primeiro DAS (4h)

| Tempo | O quê | Entregável |
|---|---|---|
| 0:00–0:20 | Exportar do Onvio: **empresas** e **tarefas/obrigações**. Salvar em `data\onvio\` | 2 arquivos |
| 0:20–0:40 | `onvio-conferir --empresas ... --tarefas ...` | Mapa: empresas, obrigações por tributo, tributos sem tarefa |
| 0:40–1:00 | Abrir o Express. **Sem subir nada.** Só ver a tela: onde se sobe, o que aparece depois, onde se vê o resultado | Print / anotação do caminho de menu |
| 1:00–1:20 | Achar **uma tarefa aberta de DAS** e anotar empresa, CNPJ, competência, nome da tarefa | A tarefa-alvo |
| 1:20–1:40 | Achar o DAS correspondente. Se não houver, emitir/baixar do e-CAC | 1 PDF |
| 1:40–2:40 | **Subir esse único documento.** Observar o que acontece | O primeiro resultado real |
| 2:40–3:30 | Se vinculou: repita com mais 2 DAS de empresas diferentes. Se não: árvore de diagnóstico abaixo | 3 DAS testados |
| 3:30–4:00 | Anotar o que aprendeu. Colar o artigo 12392 em `docs/fontes/express-12392.md` | Registro do dia |

**Critério de parada do dia:** 1 DAS entrou numa tarefa. Se conseguir isso na
primeira hora, o resto do dia é repetição para confirmar que não foi sorte.

### Se o DAS não vincular — árvore de diagnóstico

Não mexa em template antes de passar por aqui. Na ordem:

```
O Express leu o documento? (mostrou CNPJ, competência, valor?)
├── NÃO leu nada
│   └── É PDF imagem/escaneado, ou protegido por senha.
│       Teste com um PDF que abre e permite selecionar o texto.
│       → problema é o DOCUMENTO, não a configuração
│
├── Leu, mas não achou tarefa
│   ├── A tarefa está ABERTA? (não concluída, não cancelada)
│   ├── A competência da tarefa é a MESMA do documento?
│   ├── A empresa da tarefa tem o MESMO CNPJ do documento?
│   │      (matriz x filial é a pegadinha clássica)
│   └── Se tudo isso confere → aí sim é reconhecimento: template
│
├── Achou VÁRIAS tarefas
│   └── Não é erro. Existem duas tarefas plausíveis para a mesma
│       obrigação/competência. Anote quais — é achado de CADASTRO,
│       para levar ao escritório, não para consertar no template
│
└── Vinculou na tarefa ERRADA
    └── Pare tudo e anote. Este é o único resultado grave da semana.
        Documento na tarefa errada é pior que documento não vinculado.
```

**Pergunte ao Claude assim** (com o `BRIEFING.md` carregado):

> "Subi um DAS de 08/2026 da empresa X no Express. Ele leu CNPJ e competência
> certos mas devolveu 'nenhuma tarefa encontrada'. Confirmei que existe tarefa
> aberta de DAS para essa empresa nessa competência. O que investigo agora?"

Informar sempre: **o que subiu, o que saiu, o que deveria sair.**

---

## DIA 2 — DAS de verdade (4h)

Não é "configurar o DAS". É **provar que o DAS funciona em empresas
diferentes**, que é outra coisa.

1. **5 a 8 DAS de empresas diferentes**, todos com tarefa aberta confirmada.
2. Suba um por um, anotando o resultado de cada um.
3. Só depois de ver o padrão dos erros, ajuste alguma coisa.

**A pergunta do dia:** os que falharam falharam pelo mesmo motivo? Se sim, é uma
correção só. Se cada um falhou de um jeito, você ainda não entendeu o ambiente —
suba mais documentos antes de mexer em qualquer configuração.

**Entregável:** você consegue dizer "DAS funciona em X de 8 casos, e os que
falham falham por [motivo]".

---

### Antes de sair do DAS: as três variações que derrubam a comemoração

Um DAS que vinculou prova que o caminho existe. Não prova que o DAS funciona.
Teste estes três casos antes de mudar de tributo — cada um leva 10 minutos:

| Caso | Por que importa |
|---|---|
| **Filial** (CNPJ com final diferente de 0001) | O documento pode trazer o CNPJ da filial e a tarefa estar na matriz. É a pegadinha mais comum |
| **Competência antiga** (3–6 meses atrás) | Tarefa antiga pode estar concluída; o comportamento muda |
| **DAS de parcelamento** | É um DAS, casa com o template, **mas a tarefa é outra**. Se vincular na tarefa do DAS mensal, você achou um erro grave cedo — que é o melhor momento para achar |

---

## Qual template configurar em seguida

Não siga uma lista genérica. A ordem correta sai da sua carteira:

```bat
python -m docauto prioridade --tarefas data\onvio\tarefas.csv
```

```
carteira: 3 empresa(s) ativa(s)
  SIMPLES          1    33%
  PRESUMIDO        1    33%
  REAL             1    33%

ordem sugerida:
  tipo        empresas  docs/mês  tarefas   situação
  PIS                2       2.0        1   template pronto
  COFINS             2       2.0        1   template pronto
  DAS                1       1.0        1   template pronto
  CSLL               2       1.3        0   template pronto
       -> nenhuma obrigação cadastrada no Onvio — Express devolverá 'não encontrada'
```

**Por que isso não é detalhe:** a lista original (DAS → PIS → COFINS → IR →
CSLL) assume carteira de Lucro Presumido/Real. Num escritório majoritariamente
**Simples Nacional**, PIS e COFINS têm volume próximo de zero — e um dia inteiro
neles seria um dia gasto num template que quase nunca roda. Nesse caso o próximo
ganho real costuma estar em INSS/FGTS, notas fiscais ou declarações, que o
próprio comando aponta na lista de "obrigações do Onvio sem template".

A coluna `tarefas` manda mais que `docs/mês`: obrigação cadastrada é fato,
estimativa por regime é aproximação. Tributo com **0 tarefas** não deve ser o
próximo — por melhor que fique o template, o Express vai devolver "não
encontrada".

---

## DIA 3 — PIS e COFINS (4h)

Os dois **juntos**, nunca separados: eles se confundem entre si, e testar um
sozinho esconde o erro que só aparece quando o outro entra.

1. 4 documentos de PIS + 4 de COFINS, com tarefa aberta.
2. Suba **alternando**: PIS, COFINS, PIS, COFINS.
3. Procure o erro específico: **PIS vinculado em tarefa de COFINS** ou vice-versa.

Esse é o erro caro do projeto inteiro — e o único jeito de vê-lo é alternar.
Se aparecer, o desempate é o **código de receita**: PIS 8109/6912/8301,
COFINS 2172/5856 (confira na tabela oficial da RFB, `config/codigos_receita.yaml`
ainda está `NAO_CONFERIDA`).

**Entregável:** 3 tipos funcionando e **zero troca entre PIS e COFINS**.

---

## DIA 4 — IRPJ e CSLL (4h)

Aqui muda o jogo: **IRPJ e CSLL vêm com frequência na mesma guia**, e IRPJ ainda
se divide entre IRPJ e IRRF, que têm tarefas e responsáveis diferentes.

1. Antes de subir, olhe 3 documentos e responda: **dá para saber pelo documento
   se é IRPJ ou IRRF sem olhar o código de receita?** Quase sempre a resposta é
   não — e é por isso que o código de receita manda.
2. Teste 3 de cada, de empresas em regimes diferentes (presumido x real).
3. Anote quais caem em "várias tarefas" — provavelmente serão vários.

**Entregável:** os 5 tipos testados, com a lista honesta do que não dá para
separar automaticamente. **"Este tipo precisa de conferência humana" é um
resultado legítimo**, não uma falha.

---

## DIA 5 — Teste em lote e a apresentação (4h)

É o dia que vira número, e número é o que convence.

**1. Junte 20 documentos reais** numa pasta (`C:\teste-lote`), misturando os 5
tipos, empresas diferentes, todos com tarefa aberta confirmada.

**2. Gere a folha de apuração** — isso preenche sozinho o que a *automação*
entendeu de cada documento:

```bat
python -m docauto folha-teste --entrada C:\teste-lote --saida C:\teste-lote\apuracao.csv
```

```
20 documento(s) -> C:\teste-lote\apuracao.csv

o que a AUTOMAÇÃO entendeu:
  DAS      8    PIS      4    COFINS   4    IR       2    CSLL     2
  AUTOMATICO   15   75%
  PENDENTE_VALIDACAO   5   25%
```

**3. Suba os 20 no Express** e preencha, por linha, só três colunas:
`tarefa_vinculada` (SIM / MULTIPLA / NAO), `tempo_seg` e `observacao`.

**4. Você terá as duas leituras lado a lado** — e é aí que está o valor:

| Automação diz | Express diz | Leitura |
|---|---|---|
| tipo certo | SIM | Caminho limpo — é o que se quer maximizar |
| tipo certo | MULTIPLA | Reconhecimento OK, **cadastro de tarefas duplicado** |
| tipo certo | NAO | Reconhecimento OK, **falta tarefa cadastrada** |
| PENDENTE | NAO | Documento ruim (imagem, ilegível) ou empresa fora do cadastro |
| tipo errado | qualquer | **Prioridade máxima:** template a corrigir |

Repare: **três das cinco linhas não são problema de template** — são de cadastro
de tarefas ou de qualidade do PDF. Sem essa tabela, tudo pareceria "o Express
não reconhece bem".

**5. A apresentação, em 5 linhas:**

```
20 documentos reais, 5 tipos, N empresas.

  X vincularam automaticamente ......... X%
  Y exigiram escolher a tarefa ......... Y%   (cadastro de tarefas)
  Z não encontraram tarefa ............. Z%   (obrigação não cadastrada)
  W não foram lidos .................... W%   (PDF imagem)

Tempo médio por documento: N segundos, contra M minutos no processo manual.
Próximo passo: [o maior bloco acima], que é onde está o ganho.
```

Diga o que **não** foi feito com a mesma clareza. Quem apresenta só o número bom
perde a confiança na semana seguinte, quando o número real aparecer.

---

## O que NÃO fazer nesta semana

1. **Não configure cinco impostos no Dia 1.** Um DAS ponta a ponta ensina mais
   sobre o ambiente do que cinco templates pela metade.
2. **Não mexa em template de produção sem registrar o estado anterior.**
3. **Não ligue o arquivamento automático ainda.** É a Entrega 3 e depende do
   Express estar entendido. Rodar os dois juntos faz você não saber qual dos
   dois causou o problema.
4. **Não teste com documento sem tarefa aberta.** Metade das horas perdidas
   nesse tipo de projeto vai embora assim.
5. **Não prometa prazo do arquivamento automático** antes de ver a qualidade
   real dos PDFs. Se muitos forem imagem, entra OCR e o prazo muda.
6. **Não deixe de anotar.** Toda quinta-feira você não vai lembrar por que
   mexeu naquele campo na segunda.

---

## Os prazos, revisados

Concordo com os seus, com uma diferença e um alerta:

| Etapa | Sua estimativa | Minha leitura |
|---|---|---|
| Express MVP (DAS + PIS + COFINS) | 2–3 dias | **Concordo.** Pode ser 1,5 se a exportação adiantar o Dia 1 |
| Express completo (5 tipos) | 5 dias | **Concordo** |
| Arquivamento automático | 3–7 dias | **O código já está pronto e testado.** O prazo real é de *configuração e conferência*: 2–4 dias. O que pode estourar é OCR, se os PDFs forem imagem |
| Primeira rotina automática | 3–5 dias | Concordo, e manteria depois do Express |
| Projeto integrado | 2–4 semanas | Concordo |

**O alerta:** os prazos do Express dependem de uma coisa que não está nas suas
mãos — **o cadastro de tarefas do escritório**. Se as obrigações não estiverem
cadastradas por empresa e competência, nenhum ajuste de template resolve, e o
prazo vira o do escritório organizar isso. Por isso o `onvio-conferir` do Dia 1
é tão importante: ele te diz, **no primeiro dia**, se esse risco existe — em vez
de você descobrir no Dia 5.

---

## Amanhã, uma frase só

> **Fazer 1 DAS real entrar automaticamente na tarefa correta.**

Se conseguir isso e mais nada, o dia foi bom: você aprendeu a lógica real do
ambiente, que é o que trava todo o resto. O que vier além é bônus.
