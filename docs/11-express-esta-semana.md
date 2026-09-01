# 11 — Express e envio funcionando esta semana

Este documento substitui o cronograma de Fase 3 do `docs/09` quando o prazo é
**esta semana**. A estratégia é simples: **o envio já está pronto e funciona nos
dois mecanismos possíveis**, então a descoberta de qual deles o Express usa
deixa de ser um bloqueio e vira uma configuração de uma linha.

```
                        envio.modo
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
  "lote_manual"                          "pasta_monitorada"
  funciona HOJE, sem depender            copia para a pasta que o
  de confirmação nenhuma                 Express varre sozinho
        │                                         │
        └──────────► mesma fila, mesmas travas ◄──┘
                     mesma idempotência por hash
```

**Comece pelo `lote_manual` na segunda-feira.** Ele não depende de nada, já
elimina a maior parte do trabalho e coloca o processo em produção no dia 1. Se
até quarta a pasta monitorada for confirmada, é uma linha do config para trocar,
e a fila continua de onde parou — nada é reenviado.

---

## SEGUNDA — colocar o envio em produção no modo lote

**1. Atualizar e conferir** (15 min)

```bat
git pull
python -m docauto validar
python -m unittest discover -s tests -t .
```

**2. Ligar o envio em modo lote** no `config/config.yaml`:

```yaml
envio:
  habilitado: true
  modo: "lote_manual"
  pasta_lote: "D:/CONTABIL/LOTE_EXPRESS"
  empresas_piloto: ["0001"]     # comece com UMA empresa
  limite_por_rodada: 50
  incluir_revisao: true
```

**3. Rodar o ciclo completo** (30 min)

```bat
python -m docauto processar --dry-run     REM confere antes
python -m docauto processar               REM arquiva e enfileira
python -m docauto enviar --dry-run        REM mostra o que sairia
python -m docauto enviar                  REM monta o lote
```

Sai uma pasta por competência, pronta para arrastar, com uma planilha
`_CONFERIR.csv` listando arquivo, empresa, CNPJ, tipo e competência, e colunas
vazias para `conferido` e `tarefa_vinculada`.

```
D:\CONTABIL\LOTE_EXPRESS\2026-08\
    2026-08_DAS_EXEMPLO.pdf
    2026-08_PIS_EXEMPLO.pdf
    2026-08_COFINS_MODELO.pdf
    _CONFERIR.csv
```

**4. Subir no Express** e preencher a coluna `tarefa_vinculada` da planilha com
`SIM`, `MULTIPLA` ou `NAO`; depois rodar
`python -m docauto envio-confirmar --lote <pasta da competência>` para fechar o
ciclo. O procedimento de tela está em [docs/12](12-runbook-onvio-express.md).
**Essa planilha é o dado mais valioso da semana** — é ela que diz se vale a pena automatizar o
upload ou se o gargalo real está na escolha da tarefa dentro do Domínio.

✅ *Fim de segunda: envio em produção, uma empresa, com medição.*

---

## TERÇA — descobrir o mecanismo real (protocolo de 30 minutos)

Não espere a resposta formal do chamado. Faça o teste você mesmo, nesta ordem:

> **Atualização:** o artigo oficial [Como utilizar Express? (9146)](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=9146)
> menciona **baixar e usar uma pasta local no computador** para envio automático
> ao Processos. Ou seja, o Cenário B tem respaldo oficial — o que falta é
> confirmar se está disponível na sua conta e como se instala. Procure por essa
> opção no passo 1.

**Passo 1 — procurar na própria tela (10 min).** Dentro do Domínio Processos,
com o Express aberto, procure por: *configurações*, *preferências*, *importação*,
*upload automático*, *monitoramento*, *pasta de origem*. Se existir campo para
apontar uma pasta, o Cenário B está confirmado — anote o caminho exato e siga
para quarta.

**Passo 2 — chat do suporte (10 min).** Abra o chat do Portal do Cliente e faça
**uma pergunta só**, curta e fechada — chat responde pergunta objetiva muito
melhor que pergunta longa:

> "O Domínio Processos Express possui configuração para monitorar uma pasta do
> computador e fazer upload automático dos documentos? Se sim, onde se
> configura?"

**Passo 3 — ler o artigo oficial (5 min).**
[Como utilizar Express? — Portal do Cliente (código 9146)](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=9146).
Anote: formatos aceitos, tamanho máximo e limite de arquivos por lote — esses
números vão direto para `limite_por_rodada`.

**Passo 4 — registrar a resposta.** Três resultados possíveis:

| Resposta | O que fazer |
|---|---|
| **Existe pasta monitorada** | Quarta liga o modo `pasta_monitorada` |
| **Não existe** | Continua no `lote_manual` — que já está em produção desde segunda. Sem retrabalho. |
| **Existe API para Processos** | Ótimo, mas **não é escopo desta semana**. Fica para o mês seguinte; o `lote_manual` sustenta a operação enquanto isso. |

✅ *Fim de terça: mecanismo conhecido, por escrito.*

---

## QUARTA — ligar a pasta monitorada (só se confirmada)

```yaml
envio:
  modo: "pasta_monitorada"
  pasta_monitorada: "D:/CONTABIL/EXPRESS_UPLOAD"
  empresas_piloto: ["0001"]
  horas_para_alerta: 4
```

```bat
python -m docauto enviar --dry-run
python -m docauto enviar
python -m docauto envio-status
```

**Fique olhando a pasta.** O comportamento correto é o arquivo **sumir** dela em
poucos minutos — foi consumido pelo Express. O `envio-status` traduz isso:

```
fila de envio: 2 documento(s)
  CONSUMIDO        1   50.0%
  ENVIADO          1   50.0%
```

Se depois de 4 horas o arquivo continuar lá, ele vira `PARADO` e aparece
nomeado no status. É assim que você descobre que o Express deixou de varrer —
em vez de descobrir no fim do mês.

**As três perguntas que precisam de resposta ainda na quarta:**

1. O Express **remove** o arquivo da pasta depois de processar? Se **não**
   remover, a conciliação por sumiço não vale: nesse caso mantenha
   `modo: lote_manual` e mova os arquivos já subidos para uma subpasta
   `_ENVIADOS` manualmente, ou peça ao suporte como configurar a remoção.
   **Pasta monitorada que só acumula = reenvio infinito.**
2. Qual o limite de arquivos por varredura? → `limite_por_rodada`.
3. De quanto em quanto tempo ele varre? → intervalo da tarefa agendada.

✅ *Fim de quarta: upload automático rodando para uma empresa.*

---

## QUINTA — agendar e abrir para as demais empresas

**1. Agendar** as duas tarefas do Windows conforme `scripts/agendar.md`
(`processar` a cada 10 min, `enviar` a cada 15 min ou 1x/dia no modo lote).
Rode os `.bat` na mão primeiro, **com a conta que vai executar a tarefa** — o
erro mais comum é a conta do agendador não ter acesso ao `\\SERVIDOR`.

**2. Abrir para as demais empresas**, esvaziando o piloto:

```yaml
  empresas_piloto: []      # todas
```

**3. Conferir o dia inteiro:** `envio-status` de manhã, depois do almoço e no
fim do dia.

✅ *Fim de quinta: rodando sozinho para toda a carteira.*

---

## SEXTA — fechar a semana com número

```bat
python -m docauto relatorio
python -m docauto envio-status
```

Responda por escrito, com os números na mão:

- Quantos documentos entraram, quantos foram arquivados sozinhos, quantos ficaram em pendência?
- **Algum foi arquivado na empresa errada?** (tem que ser zero — se não for, o piloto volta para uma empresa na segunda)
- Dos enviados, quantos o Express vinculou sozinho? Quantos exigiram escolher a tarefa?
- Quanto tempo a fila de pendências consumiu por dia?

Esse último dado decide o mês seguinte: se o gargalo virou *escolher a tarefa
dentro do Domínio*, o próximo passo é a API (pergunta 3 do `docs/08` — consultar
tarefas em aberto e pré-identificar), não mais automação de upload.

---

## Travas que já estão no código (não precisam de disciplina humana)

| Trava | Por quê |
|---|---|
| **Só documento arquivado entra na fila** | Documento em pendência nunca é enviado — o Express receberia algo que o próprio escritório ainda não confirmou de quem é. |
| **Idempotência por SHA-256** | O mesmo documento nunca entra duas vezes, por mais que a pasta de entrada seja reprocessada. É o que impede a mesma guia de chegar cinco vezes no Domínio. |
| **`empresas_piloto`** | Limita o alcance sem tocar em código. Piloto de verdade, não "cuidado ao rodar". |
| **`limite_por_rodada`** | Respeita o limite de lote do Express em vez de descobrir o limite na marra. |
| **Arquivo sumido do servidor → `BLOQUEADO`** | Nunca envia caminho quebrado. |
| **`PARADO` após N horas** | Detecta Express que parou de varrer. |
| **`enviar --dry-run`** | Toda mudança de config é testada antes de valer. |

## Se der errado no meio da semana

- **Desligar o envio:** `envio.habilitado: false`. O arquivamento continua
  funcionando — os dois caminhos são independentes de propósito.
- **Documento enviado errado:** corrija a causa (cadastro ou template), depois
  reenfileire — a fila é um CSV: mude o `estado` da linha para `PENDENTE`,
  apague `enviado_em` e `destino_envio`, e rode `enviar`.
- **Fila de pendências crescendo:** é sintoma, não causa. Rode `relatorio` e
  ataque o motivo mais frequente. **Nunca** relaxe uma trava para diminuir fila.
