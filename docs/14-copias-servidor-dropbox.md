# 14 — Cópias no servidor e no Dropbox, e a ordem do fluxo

## Resposta curta

**Sim, é possível, e é simples.** O Dropbox instalado no computador é uma pasta
local comum: a automação copia para ela como copia para o servidor, e quem
sincroniza com a nuvem é o próprio Dropbox. Basta apontar o caminho.

```yaml
destinos:
  - nome: "SERVIDOR"
    raiz: "D:/CONTABIL/CLIENTES"
    habilitado: true
    principal: true
  - nome: "DROPBOX"
    raiz: "C:/Users/SEU_USUARIO/Dropbox/CONTABIL/CLIENTES"
    habilitado: true
    principal: false
```

O documento vai para **os dois**, com a mesma estrutura de pastas e o mesmo
nome. O `principal` é o que vale como destino oficial no registro e na fila de
envio ao Express.

**Se o Dropbox estiver fora do ar**, o documento **não** vai para pendências —
ele já está salvo no servidor. A cópia que faltou entra numa fila e é refeita
depois:

```bat
python -m docauto espelhar
```

Isso é proposital: sincronização de nuvem cai, e um documento arquivado
corretamente no servidor não pode virar exceção por causa disso. O que não pode
é ninguém ficar sabendo — por isso a fila existe, e a linha só sai dela quando a
cópia é feita de verdade.

---

## A parte que precisa de atenção: a ORDEM

Você descreveu assim: *"ao fazer upload na pasta Express, ele já faz uma cópia
para o servidor e o Dropbox"*. Isso funciona, mas tem um risco real.

### O problema

Se a **pasta do Express for o ponto de entrada**, e o Express **apagar** o
arquivo depois de subir (que é o comportamento esperado de uma pasta de envio
automático), abre-se uma corrida:

```
09:00:00  pessoa solta a guia na pasta do Express
09:00:20  Express varre, sobe e APAGA o arquivo
09:02:00  automação roda ... e não encontra nada
          → documento vinculado no Onvio e NUNCA arquivado no servidor
```

E o pior: **você não fica sabendo.** A automação não pode registrar a falta de
um arquivo que nunca viu. Não existe conferência que pegue isso depois — a única
pista seria alguém procurar a guia no servidor daqui a três meses e não achar.

### A ordem correta

Inverta: **uma porta de entrada só, e o Express é o último da fila.**

```
pessoa solta a guia em ENTRADA_DOCUMENTOS
        ↓
automação lê, identifica e classifica
        ↓
copia para o SERVIDOR      ← acontece primeiro
copia para o DROPBOX       ← e aqui
        ↓
copia para a pasta do EXPRESS (ou monta o lote)
        ↓
Express sobe e vincula
```

O resultado para quem opera é idêntico — solta o arquivo numa pasta e some —
mas o documento só chega ao Express **depois** de já estar guardado nos dois
lugares. Nenhuma corrida, nenhuma perda silenciosa.

**Truque prático para a equipe:** se as pessoas já se acostumaram a soltar na
"pasta do Express", crie um **atalho na área de trabalho chamado "Express"
apontando para `ENTRADA_DOCUMENTOS`**. O hábito continua o mesmo e o fluxo fica
certo.

### Se ainda assim quiser vigiar a pasta do Express

É suportado — `pastas.entrada` aceita uma lista:

```yaml
pastas:
  entrada:
    - "D:/CONTABIL/ENTRADA_DOCUMENTOS"
    - "C:/Users/SEU_USUARIO/Express"
```

Faça isso **apenas** se uma destas for verdade:

- o Express **não apaga** o arquivo depois de subir (confirme — é a mesma
  pergunta do `docs/11`); ou
- é uma pasta onde as pessoas soltam documentos que **você também** quer
  arquivar, e o envio ao Express é feito por outro caminho.

Se for vigiar mesmo assim, reduza a janela: agende `processar` a cada **1 ou 2
minutos** em vez de 10, e mantenha `modo_original: "copiar"`. Isso encurta a
corrida, mas não a elimina.

---

## Como fica a estrutura nos dois destinos

Idêntica, o que torna a busca previsível em qualquer um deles:

```
D:\CONTABIL\CLIENTES\0001 - EMPRESA EXEMPLO LTDA\FISCAL\2026\2026-08\GUIAS\
    2026-08_DAS_EXEMPLO.pdf

C:\Users\...\Dropbox\CONTABIL\CLIENTES\0001 - EMPRESA EXEMPLO LTDA\FISCAL\2026\2026-08\GUIAS\
    2026-08_DAS_EXEMPLO.pdf
```

## Antes de ligar o Dropbox — três cuidados

1. **Caminho longo.** O caminho do Dropbox costuma ser mais fundo que o do
   servidor (`C:\Users\Fulano\Dropbox\...`). O limite de 260 caracteres do
   Windows chega mais rápido. A automação confere antes de gravar
   (`limite_caminho: 240`); se acusar, encurte a raiz — `C:\Dropbox\CONTABIL`
   em vez de `C:\Users\Fulano\Dropbox\CONTABIL\CLIENTES\ARQUIVO MORTO`.
2. **Espaço e plano.** Documento fiscal de uma carteira inteira cresce rápido.
   Confira o espaço da conta antes, não depois.
3. **LGPD.** Guia fiscal tem dado de terceiro. Se for para o Dropbox, a pasta
   deve ser da **conta do escritório**, com compartilhamento controlado — não a
   conta pessoal de um funcionário. Vale registrar essa decisão por escrito
   (`docs/10`).

## Ligar por etapas

Não ligue os dois destinos no mesmo dia em que começa a operar.

1. **Semana 1:** só `SERVIDOR`. Prove que a classificação e o caminho estão certos.
2. **Semana 2:** ligue `DROPBOX` com `habilitado: true` e rode um dia. Confira
   que os dois lados têm os mesmos arquivos e rode `espelhar` no fim do dia.
3. **Depois:** inclua `espelhar` no `scripts/enviar.bat`, para que qualquer
   cópia perdida seja refeita sozinha na próxima rodada.

## Comandos

```bat
python -m docauto processar          REM arquiva em todos os destinos habilitados
python -m docauto espelhar --dry-run REM o que está pendente de cópia
python -m docauto espelhar           REM refaz as cópias que faltaram
```

A coluna `copias` do `registro.csv` mostra, por documento, para onde ele foi
além do principal.
