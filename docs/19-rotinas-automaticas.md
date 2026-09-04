# 19 — Rotinas Automáticas: colocar no ar rápido, sem quebrar

> Mesma ressalva do `docs/18`: não tenho acesso à documentação da Domínio, então
> **não sei os nomes dos recursos**. O catálogo abaixo está organizado por
> **finalidade**. Confirme na sua versão qual recurso faz cada uma e anote na
> coluna `RECURSO_DOMINIO` de `config/portal/rotinas.csv`.

---

## A diferença entre rotina e automação

Rotina automática **fala com o cliente em nome do escritório**. Não é código:
é comunicação. Um erro aqui não é um arquivo no lugar errado — é um e-mail que
já saiu, para alguém que já leu.

Três consequências práticas:

1. **Toda rotina passa pela empresa de teste antes** (`docs/18`, Etapa 1).
2. **Uma rotina por vez.** Ativar cinco no mesmo dia significa não saber qual
   causou o problema — e clientes recebendo cinco e-mails novos de uma vez.
3. **Texto revisado por gente.** O texto padrão do sistema quase nunca soa como
   o escritório fala.

---

> **Os valores já vêm preenchidos** em `config/portal/rotinas.csv`, e os textos
> das mensagens estão em [docs/20](20-textos-das-rotinas.md). Este documento é o
> método; o docs/20 é o conteúdo.

## Catálogo por finalidade

Preencha `config/portal/rotinas.csv`. As dez linhas cobrem o que um escritório
contábil normalmente automatiza:

| ID | Finalidade | Onda | Risco |
|---|---|---|---|
| **R01** | Avisar que há documento novo no portal | 1 | MÉDIO |
| **R02** | Enviar guias do mês com prazo | 1 | **ALTO** |
| **R07** | Aviso interno de tarefa atrasada | 1 | BAIXO |
| **R09** | Boas-vindas / primeiro acesso | 1 | MÉDIO |
| R03 | Lembrete de vencimento (D-2) | 2 | MÉDIO |
| R04 | Solicitar documentos ao cliente | 2 | MÉDIO |
| R06 | Avisar obrigação cumprida | 2 | BAIXO |
| R05 | Cobrar pendência não atendida | 3 | **ALTO** |
| R08 | Aviso de certidão a vencer | 3 | BAIXO |
| R10 | Resumo mensal | 3 | BAIXO |

**Risco ALTO** significa que o cliente **age** com base na mensagem: paga uma
guia, ou é cobrado. Erro nessas duas custa dinheiro ou relação.

### Por que esta ordem

**R07 primeiro** (aviso interno de tarefa atrasada): é a única de risco baixo de
verdade — não sai do escritório. Serve para você aprender o mecanismo de rotina
sem nenhum cliente envolvido. É o "DAS" das rotinas.

**R01 e R09 em seguida**: alto valor, risco contido. R09 é o que faz o cliente
entrar no portal pela primeira vez — sem ela, todo o resto conversa com uma
tela vazia.

**R02 depois**: é a rotina de maior valor percebido ("minhas guias chegam
sozinhas") e a de maior risco. Só entra com o fluxo de conferência funcionando.

**R05 por último, se entrar**: cobrança automática de cliente exige que o
registro de pendências esteja **certo**. Cobrar quem já enviou é o jeito mais
rápido de queimar confiança conquistada.

---

## Os 7 campos que toda rotina precisa ter decididos

Antes de ativar qualquer uma, responda — está tudo em `rotinas.csv`:

1. **Gatilho** — o que exatamente dispara? (documento publicado? tarefa
   concluída? data?)
2. **Destinatário** — qual perfil, e **nunca** "todos os contatos".
3. **Conteúdo** — texto revisado, com as variáveis certas. Teste que
   `[NOME DA EMPRESA]` não sai literalmente assim.
4. **Janela** — dia e hora. Nada dispara sexta 18h nem fim de semana.
5. **Frequência máxima** — quantas mensagens no máximo por cliente por semana.
   Sem teto, três rotinas somadas viram spam.
6. **Falha** — se não disparar, quem descobre e como? Rotina que falha em
   silêncio é pior que rotina desligada, porque o escritório *acha* que o
   cliente foi avisado.
7. **Desligamento** — como parar rapidamente se algo der errado. Saiba onde
   fica **antes** de precisar.

O item 6 é o mais negligenciado. Combine uma conferência: toda segunda, alguém
olha se as rotinas da semana anterior dispararam.

---

## Protocolo de ativação (por rotina, ~40 minutos)

```
1. Preencher a linha da rotina em config/portal/rotinas.csv       (10 min)
2. Configurar no sistema, com ATIVA = só para a empresa de teste  (10 min)
3. Disparar e conferir:
   - chegou?
   - caixa de entrada ou spam?
   - texto correto, sem variável crua?
   - link leva ao lugar certo?
   - remetente e assinatura corretos?                             (10 min)
4. Ativar para 1 cliente piloto. Aguardar 1 semana.
5. Só então estender para a carteira. Marcar ATIVA = SIM.         (10 min)
```

**Nunca pule o passo 4 em rotina de risco ALTO.**

---

## Cronograma realista

Você pediu rápido. Isto é rápido **e** seguro:

| Dia | O quê | Resultado |
|---|---|---|
| **1** | Portal: perfis, matriz de publicação, empresa de teste | Base pronta |
| **2** | Publicação manual + 1 cliente piloto + teste de entregabilidade | Portal funcionando no manual |
| **3** | R07 (interna) e R09 (boas-vindas) na empresa de teste | Mecanismo de rotina dominado |
| **4** | R01 no piloto + onboarding do piloto | Cliente recebendo aviso de verdade |
| **5** | R02 (guias) na empresa de teste; piloto se estável | A rotina de maior valor, testada |
| **6–10** | Onda 2: 3 a 5 clientes; rotinas de onda 2 | Operação real |
| **11+** | Carteira toda; rotinas de onda 3 | Portal redondo |

Em **duas semanas** dá para ter portal e as quatro rotinas principais rodando na
carteira. Tentar fazer em três dias é o caminho para o incidente que atrasa tudo
em um mês.

---

## Como isso se conecta com a automação de documentos

A automação de arquivamento (o resto deste repositório) fica **esperando**, como
você decidiu — e isso é coerente: ela alimenta o portal, então o portal tem que
estar certo primeiro.

Quando voltar a ela, o encaixe é direto: a automação identifica empresa, tributo
e competência e arquiva; o portal publica o que a **matriz de publicação** manda
publicar; a rotina R01/R02 avisa. Os três campos que a matriz usa — tipo,
empresa, competência — são exatamente os que a automação já extrai.

Ou seja: preencher a matriz agora não é trabalho jogado fora. É a especificação
de que a automação vai precisar depois.

---

## Riscos, em ordem de gravidade

| Risco | Consequência | Prevenção |
|---|---|---|
| Cliente vê documento de outro | Incidente de LGPD, perda de contrato | Teste entrando como cliente, um usuário por empresa |
| Guia publicada com valor/competência errados | Cliente paga errado | Conferência antes de publicar, 90 dias |
| Rotina dispara em massa por engano | Spam, imagem queimada | Ativar por onda, teto de frequência |
| Aviso cai em spam | Todo mundo acha que avisou; ninguém recebeu | Teste de entregabilidade antes do go-live |
| Cobrança automática indevida | Relação desgastada | R05 só na onda 3, com registro confiável |
| Cliente escreve e ninguém responde | Portal abandonado | Dono e prazo de resposta definidos |
| Portal configurado e ninguém usa | Projeto invisível | Onboarding com meta de 80% em 30 dias |
