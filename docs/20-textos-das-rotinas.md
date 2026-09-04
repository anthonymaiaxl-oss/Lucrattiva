# 20 — O que preencher em cada rotina (com os textos prontos)

Os valores recomendados já estão em `config/portal/rotinas.csv`. Aqui está o
conteúdo: **assunto e corpo de cada mensagem**, prontos para colar, mais o que
conferir no teste de cada uma.

> `[EMPRESA]`, `[COMPETENCIA]` etc. são espaços reservados. **Troque pelos nomes
> reais das variáveis do Domínio** — e o primeiro teste é justamente ver se não
> saiu o colchete literal para o cliente.

---

## Cinco regras que valem para todas

**1. O e-mail avisa; o documento fica no portal.** Não anexe guia nem holerite
no e-mail. Dois motivos: e-mail encaminhado vaza (holerite anexado circula pelo
WhatsApp do time do cliente), e link para o portal é o que ensina o cliente a
usar o portal. Sem isso, você automatizou o e-mail e o portal continua vazio.

**2. Agregue.** Um e-mail por documento publicado significa 8 e-mails no dia do
fechamento. Toda rotina com `AGREGA = SIM` manda **um** e-mail com a lista do
dia. Só R09 (boas-vindas) não agrega — é individual por natureza.

**3. Assunto sempre com empresa e competência.** O cliente que tem duas empresas
precisa saber de qual é sem abrir.

**4. Nada dispara sexta depois das 15h, nem fim de semana.** Mensagem que pede
ação e chega sexta à noite gera ansiedade e nenhuma ação.

**5. Teto de 3 e-mails por cliente por semana**, fora as guias. Três rotinas
somadas viram spam sem ninguém perceber.

---

# ONDA 1 — primeira semana

## R07 — Aviso interno de tarefa atrasada

O ponto de partida: **não sai do escritório**. Você aprende o mecanismo de
rotina sem nenhum cliente envolvido.

| Campo | Valor |
|---|---|
| Gatilho | tarefa com prazo vencido e não concluída |
| Destinatário | equipe do escritório (interno) |
| Janela | dias úteis, 08h00 |
| Agrega | SIM — uma lista, não um e-mail por tarefa |

**Assunto:** `Tarefas em atraso — [DATA]`

```
Bom dia.

Tarefas com prazo vencido nesta manhã:

[LISTA: empresa | obrigação | competência | dias em atraso | responsável]

Total: [N] tarefa(s).

Atualize a situação no Processos até o fim do dia.
```

**No teste, confira:** a lista traz mesmo só o que está vencido; não repete
tarefa já concluída; chega às 08h e não à meia-noite.

---

## R09 — Boas-vindas e primeiro acesso

Sem esta rotina, todas as outras conversam com uma tela que o cliente nunca
abriu.

| Campo | Valor |
|---|---|
| Gatilho | usuário do cliente cadastrado no portal |
| Destinatário | SÓCIO do cliente |
| Janela | no ato do cadastro |
| Agrega | NÃO |

**Assunto:** `[EMPRESA] — seu acesso ao portal da Lucrattiva`

```
Olá, [NOME].

Criamos o seu acesso ao portal da Lucrattiva. A partir de agora, tudo da
[EMPRESA] fica em um lugar só:

- suas guias, disponíveis com pelo menos 5 dias de antecedência;
- seus documentos contábeis e fiscais, sempre acessíveis;
- um canal direto com a gente, sem depender de quem está online.

Para começar: [LINK DE ACESSO]
Seu usuário: [E-MAIL]

Leva dois minutos para criar a senha. Qualquer dúvida, é só responder este
e-mail ou falar com [RESPONSAVEL] no [TELEFONE].

Equipe Lucrattiva
```

**Repare no que o texto faz:** fala do que o cliente ganha, não de como o
sistema funciona. Cliente não quer aprender um portal; quer as guias no lugar
certo.

**No teste, confira:** o link abre e permite criar senha; funciona no celular
(a maioria vai abrir no celular); o nome da empresa aparece certo.

**Combinação obrigatória:** quem não acessar em 48h recebe uma ligação. Rotina
não substitui esse empurrão — e é ele que faz a meta de 80% de adoção.

---

## R01 — Documento novo no portal

| Campo | Valor |
|---|---|
| Gatilho | documento publicado no portal |
| Destinatário | perfil definido na matriz de publicação |
| Janela | dias úteis, 17h00 |
| Agrega | SIM |

**Assunto:** `[EMPRESA] — [N] novo(s) documento(s) no portal`

```
Olá, [NOME].

Publicamos hoje no portal da [EMPRESA]:

[LISTA: tipo do documento | competência]

Acesse: [LINK DO PORTAL]

Equipe Lucrattiva
```

Curto de propósito: é um aviso, não uma carta.

**No teste, confira:** só lista documentos que aquele perfil pode ver — este é
**o** teste que importa aqui; se o financeiro receber a lista de um holerite, a
configuração de perfil está errada.

---

## R02 — Guias do mês disponíveis

A rotina de maior valor percebido e a de maior risco: o cliente **paga** com
base nela.

| Campo | Valor |
|---|---|
| Gatilho | guias da competência publicadas **e conferidas** |
| Destinatário | FINANCEIRO do cliente |
| Janela | até 5 dias antes do vencimento, 09h00 |
| Agrega | SIM — todas as guias do mês num e-mail só |

**Assunto:** `[EMPRESA] — guias de [COMPETENCIA] disponíveis`

```
Olá, [NOME].

As guias da [EMPRESA] referentes a [COMPETENCIA] estão no portal:

[LISTA: tributo | vencimento | valor]

Acesse e baixe em: [LINK DO PORTAL]

Pague até a data de vencimento de cada guia. Se algum valor não fizer sentido,
fale com a gente antes de pagar — é mais fácil corrigir antes.

Equipe Lucrattiva
```

Aquela penúltima frase não é gentileza: é o que transforma o cliente na sua
última linha de conferência. Um cliente que estranha um valor evita um erro que
custaria retificação.

**No teste, confira** — este é o mais rigoroso de todos:
- valores e vencimentos batem com as guias publicadas;
- não entrou guia de outra empresa na lista;
- não entrou guia de outra competência;
- o link leva para a guia certa;
- dispara com pelo menos 5 dias de folga do vencimento.

**Não ative para cliente real** sem uma competência inteira conferida à mão na
empresa de teste.

---

# ONDA 2 — depois da onda 1 estável

## R03 — Lembrete de vencimento (D-2)

| Campo | Valor |
|---|---|
| Gatilho | guia publicada e **não baixada** até D-2 |
| Destinatário | FINANCEIRO |
| Janela | D-2, 08h00, dias úteis |

**Assunto:** `[EMPRESA] — guia vence em 2 dias`

```
Olá, [NOME].

Lembrete: [TRIBUTO] da [EMPRESA], competência [COMPETENCIA], vence em
[DATA_VENCIMENTO].

Guia no portal: [LINK]

Se já pagou, pode ignorar.
```

O gatilho **"não baixada"** é o que evita irritar quem já resolveu. Se o sistema
não souber informar isso, prefira não ativar esta rotina a mandar para todos.

---

## R04 — Solicitação mensal de documentos

| Campo | Valor |
|---|---|
| Gatilho | início da competência |
| Destinatário | SÓCIO |
| Janela | dia 5, 09h00 |

**Assunto:** `[EMPRESA] — documentos de [COMPETENCIA]`

```
Olá, [NOME].

Para fechar a competência [COMPETENCIA] da [EMPRESA], precisamos de:

[LISTA DE DOCUMENTOS PENDENTES]

Envie pelo portal: [LINK]
Prazo: [DATA]

Se já enviou algum destes, desconsidere — e nos avise para corrigirmos o
controle.

Equipe Lucrattiva
```

A última frase existe porque pedir o que já foi enviado é o jeito mais rápido de
o cliente perder a confiança na automação.

---

## R06 — Obrigação cumprida

| Campo | Valor |
|---|---|
| Gatilho | tarefa de obrigação concluída |
| Destinatário | SÓCIO |
| Janela | dias úteis, 17h00 · agrega |

**Assunto:** `[EMPRESA] — obrigações entregues`

```
Olá, [NOME].

Entregamos hoje, referente à [EMPRESA]:

[LISTA: obrigação | competência | data de entrega]

Comprovantes no portal: [LINK]

Equipe Lucrattiva
```

Rotina de risco baixo e retorno alto: é o que torna visível um trabalho que o
cliente não vê acontecer. Escritório que não comunica entrega parece que não
entrega.

---

# ONDA 3 — por último

## R08 — Certidão a vencer

**Assunto:** `[EMPRESA] — certidão vence em 30 dias`

```
Olá, [NOME].

A [TIPO DE CERTIDAO] da [EMPRESA] vence em [DATA].

[Vamos providenciar a renovação / Precisamos de [DOCUMENTO] para renovar].

Equipe Lucrattiva
```

Escolha **uma** das duas frases entre colchetes e apague a outra — depende de
quem renova ser você ou o cliente. Deixar a decisão para depois faz a mensagem
sair ambígua.

## R05 — Cobrança de pendência

Só ative quando o registro de pendências estiver confiável.

| Campo | Valor |
|---|---|
| Gatilho | solicitação sem resposta há 7 dias |
| Janela | terças, 10h00 |

**Assunto:** `[EMPRESA] — pendência de [COMPETENCIA]`

```
Olá, [NOME].

Ainda estamos aguardando, referente à [EMPRESA]:

[LISTA]

Sem esses documentos não conseguimos fechar a competência [COMPETENCIA], e
isso pode gerar atraso em obrigações com prazo legal.

Envie pelo portal: [LINK]
Qualquer dificuldade, fale com [RESPONSAVEL] no [TELEFONE].

Equipe Lucrattiva
```

Tom firme sem ser ríspido, e com uma saída humana no fim. **Máximo duas
cobranças automáticas**; da terceira em diante é telefone, não e-mail.

## R10 — Resumo mensal

**Assunto:** `[EMPRESA] — resumo de [COMPETENCIA]`

```
Olá, [NOME].

Resumo da [EMPRESA] em [COMPETENCIA]:

- Obrigações entregues: [N]
- Total de tributos apurados: [VALOR]
- Documentos disponíveis no portal: [N]

Detalhes: [LINK]

Equipe Lucrattiva
```

---

## Antes de ativar qualquer uma — o teste de 10 minutos

Na empresa de teste, para cada rotina:

- [ ] chegou;
- [ ] **caixa de entrada**, não spam (Gmail, Outlook e corporativo);
- [ ] nenhum `[COLCHETE]` literal no texto;
- [ ] nome da empresa e competência corretos;
- [ ] o link abre e leva ao lugar certo;
- [ ] abre bem no celular;
- [ ] remetente e assinatura corretos;
- [ ] horário de disparo é o configurado.

O terceiro item reprova com mais frequência do que se imagina, e é o que faz a
mensagem parecer amadora — o cliente lê `Olá, [NOME]` e entende na hora que
ninguém revisou.

## Ordem de ativação, em uma linha

**R07** (interna, sem risco) → **R09** (traz o cliente para o portal) →
**R01** (avisa) → **R02** (a de maior valor) → onda 2 → onda 3.
