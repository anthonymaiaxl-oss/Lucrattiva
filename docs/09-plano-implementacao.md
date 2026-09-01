# 09 — Plano de implantação, passo a passo

> Escrito para um escritório que **começou hoje**. Isso é uma vantagem enorme e
> tem prazo de validade: você vai definir o padrão **antes** de existir bagunça
> para arrumar. Todo escritório antigo que faz esse projeto gasta 70% do esforço
> migrando arquivo velho. Você gasta 0%. Não desperdice essa janela.

Regra que vale para todas as fases: **nada é ligado sem ter sido testado em
`--dry-run` com documento real.**

---

## SEMANA 1 — Decidir o padrão (sem escrever uma linha de código)

Esta semana não tem programação. Tem decisão. É a semana que determina se o
projeto funciona.

**Passo 1. Escolher o servidor e a raiz.**
Um caminho, um só, para todos: `\\SERVIDOR\CONTABIL\` (ou `D:\CONTABIL\` se por
enquanto for uma máquina só). Nunca a área de trabalho de alguém, nunca
"Documentos" de um usuário.

**Passo 2. Fechar a estrutura de pastas.** Leia `docs/04` e decida:
competência `2026-08` ou `08 - AGOSTO`? Subpasta por tributo, sim ou não
(recomendação: **não**). Escreva a decisão. Não mude depois sem migração.

**Passo 3. Fechar a nomenclatura.** Recomendado: `2026-08_DAS_EXEMPLO.pdf`.

**Passo 4. Criar o cadastro de empresas.** Com os clientes que você tem hoje —
sejam 3, sejam 10. Copie `data/empresas.exemplo.csv` para `data/empresas.csv` e
preencha. **Preencha `CODIGO_DOMINIO` desde o primeiro cliente**: é o que vai
permitir conciliar com o Domínio na Fase 3, e voltar atrás para preencher 200
cadastros depois é sofrimento evitável.

**Passo 5. Definir quem valida.** Uma pessoa (pode ser você) responsável pela
fila de pendências, com horário fixo — 20 minutos no fim do dia. Automação sem
dono da exceção morre no primeiro mês.

**Passo 6. Abrir o chamado na Thomson Reuters** com as 10 perguntas de
`docs/08`. Abra **agora**, na semana 1: a resposta demora e não bloqueia nada.

✅ *Fim da semana 1:* padrão escrito, cadastro preenchido, chamado aberto.

---

## SEMANA 2 — Fase 1: o fluxo básico rodando

**Passo 7. Instalar.** No servidor, Python 3.11 ou superior:

```bat
git clone <repo> C:\CONTABIL\docauto
cd C:\CONTABIL\docauto
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Passo 8. Criar config e pastas.**

```bat
python -m docauto init
```

Isso cria `config/config.yaml` e as pastas. Abra o `config.yaml` e ajuste os
caminhos para os do seu servidor. Confira que `modo_original: "copiar"` e
`ocr_habilitado: false` — é assim que se começa.

**Passo 9. Validar o cadastro.**

```bat
python -m docauto validar
```

**Não avance enquanto houver um erro na lista.** CNPJ com dígito errado aqui é
documento na empresa errada depois.

**Passo 10. Criar a árvore de pastas dos clientes.**

```bat
python -m docauto estrutura --ano 2026
```

**Passo 11. Conferir a tabela de códigos de receita.** Abra
`config/codigos_receita.yaml`, confira contra a tabela oficial da Receita
**apenas os códigos que a sua carteira usa**, apague o resto, preencha
`conferido_em`/`conferido_por` e mude o status para `CONFERIDA` (ver `docs/03`).

**Passo 12. Primeiro teste, em simulação.** Junte 20 a 30 documentos reais
(DAS e DARF que você já tem) numa pasta e:

```bat
python -m docauto processar --entrada C:\teste --dry-run
```

Saída real do projeto, para você saber o que esperar:

```
[OK ] darf_pis.txt  -> PIS 2026-08 EMPRESA EXEMPLO ... score=91
        -> ...\0001 - EMPRESA EXEMPLO...\FISCAL\2026\2026-08\GUIAS\2026-08_PIS_EXEMPLO.pdf
[PEN] darf_ambiguo.txt -> NECESSITA_VALIDACAO 2026-08 ... score=61
        ! CLASSIFICACAO_AMBIGUA: empate entre COFINS (43) e PIS (43)
[PEN] darf_empresa_desconhecida.txt -> CSLL 2026-08 (empresa não identificada)
        ! EMPRESA_NAO_IDENTIFICADA: CNPJ 11.444.777/0001-61 não encontrado no cadastro
```

**Passo 13. Conferir documento por documento.** Nesta primeira rodada, todos.
Cada `[PEN]` tem um motivo escrito — o motivo é a sua lista de ajuste:
cadastro incompleto, palavra-chave faltando no template, código de receita fora
da tabela. Ajuste `config/` e repita o passo 12 até **zero erro de destino**
(fila grande, tudo bem; destino errado, nunca).

✅ *Fim da semana 2:* simulação com zero erro de destino.

---

## SEMANA 3 — Ligar para valer, em produção pequena

**Passo 14. Definir a entrada única.** `\\SERVIDOR\CONTABIL\ENTRADA_DOCUMENTOS`.
Combine com a equipe: **todo documento tributário passa por aqui**. E-mail,
portal, WhatsApp — tudo desemboca nessa pasta. Se existirem duas entradas, o
projeto falha por fora do software.

**Passo 15. Rodar sem `--dry-run`, uma vez por dia, você mesmo:**

```bat
python -m docauto processar
```

Os originais **continuam na entrada** (`modo_original: "copiar"`). Nada é perdido.

**Passo 16. Rotina diária de 20 minutos** com a fila de pendências. Cada arquivo
em `PENDENTES_VALIDACAO\<MOTIVO>\` tem um `.laudo.json` do lado explicando o que
faltou, os candidatos e as sugestões de empresa. Resolva a **causa** (cadastrar a
empresa, ajustar o template) e devolva o arquivo para a entrada — ele reprocessa
sozinho, e o duplicado é detectado por hash, então não há risco de duplicar.

**Passo 17. Agendar.** Tarefas Agendadas do Windows, a cada 10 minutos, com
`processar`. Use o agendador, não um serviço com watchdog: se o processo cair, o
agendador simplesmente volta na próxima rodada.

**Passo 18. Acompanhar o número.**

```bat
python -m docauto relatorio
```

```
documentos processados: 6
  AUTOMATICO                   3   50.0%
  PENDENTE_VALIDACAO           3   50.0%

motivos de pendência (atacar de cima para baixo):
  CLASSIFICACAO_AMBIGUA           1
  EMPRESA_NAO_IDENTIFICADA        1
```

Meta realista do primeiro mês: **60–70% automático, zero erro de destino**.
Quem promete 95% no primeiro mês está escondendo os erros dentro do automático.

✅ *Fim da semana 3:* rodando sozinho, fila com dono, número medido.

---

## SEMANA 4 e MÊS 2 — Fase 2: OCR e cobertura

**Passo 19. Ligar o OCR** — só agora, e só se houver documento escaneado.

```bat
pip install pytesseract pdf2image
```
mais os binários **Tesseract** (com idioma `por`) e **Poppler**. Depois
`ocr_habilitado: true` no config. Documento lido por OCR já entra com
multiplicador 0,85 na confiança, ou seja, cai mais em revisão — de propósito.

**Passo 20. Ampliar os tipos** conforme aparecerem: INSS/GPS, FGTS, ICMS, ISS,
DCTF. Um template novo por vez, com 10 documentos de teste cada (receita em
`docs/03`).

**Passo 21. Calibrar** com 50 documentos já conferidos (receita em `docs/07`).

**Passo 22. Trocar `copiar` por `mover`** — só depois de 60 dias de operação
limpa, e com backup funcionando.

---

## MÊS 3 — Fase 3: Express

> **Com prazo para esta semana, use [docs/11](11-express-esta-semana.md)**: o
> envio já está implementado nos dois mecanismos possíveis e o modo `lote_manual`
> entra em produção no dia 1, sem depender de confirmação nenhuma.

**Passo 23. Com a resposta do chamado em mãos**, escolha o cenário de `docs/08`
(A: API · B: pasta monitorada · C: lote manual).

**Passo 24. Piloto com UMA empresa, por uma semana.** Em `config.yaml`,
`envio.habilitado: true` e `envio.empresas_piloto: ["0001"]`. Confira todo dia
com `python -m docauto envio-status`: a tarefa foi vinculada? o arquivo saiu da
pasta monitorada? Roteiro detalhado em [docs/11](11-express-esta-semana.md).

**Passo 25. Estender** só depois da semana limpa.

---

## MÊS 4 — Fase 4: painel de exceções

**Passo 26.** Enquanto a fila couber em pastas + laudo JSON, **não construa
painel**. Painel bonito com fila pequena é desperdício.

**Passo 27.** Quando passar de ~30 pendências por dia, o painel mínimo é: lista
com documento, empresa provável, tipo provável, competência provável, motivo, e
dois botões — *confirmar* e *corrigir*. `registro.csv` e os `.laudo.json` já
contêm exatamente esses campos: o painel lê deles, não precisa de banco novo.

**Passo 28.** Aviso automático (e-mail/WhatsApp) quando a fila passar de X
documentos ou quando um documento ficar mais de 2 dias parado. É aqui que o
**n8n** entra bem — orquestrando aviso, não regra fiscal.

---

## Os cinco erros que matam esse tipo de projeto

1. **Ligar tudo de uma vez.** Uma fase por vez, com número medido.
2. **Deixar a fila de pendências sem dono.** Ela cresce, viram 300 arquivos,
   ninguém olha mais, o projeto morre — mesmo funcionando.
3. **Relaxar trava para reduzir fila.** A fila é sintoma; a causa está no
   cadastro ou no template.
4. **Mudar o padrão de pastas depois de 6 meses.** Decida na semana 1.
5. **Depender da integração com o Express para começar.** O arquivamento vale
   por si só, desde o primeiro dia.
