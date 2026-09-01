# 13 — Calibrar os templates com as suas guias

Os templates que vieram no projeto são um ponto de partida genérico. Cada
emissor formata a guia do seu jeito — Sicalc, PGDAS-D, sistema do contador,
portal do banco — e é isso que faz um template acertar 100% num escritório e
70% em outro. Este documento é o procedimento para fechar essa diferença.

**A ferramenta é o `diagnosticar`.** Ele não arquiva nem envia nada: só mostra
**por que** cada documento foi classificado como foi.

---

## O ciclo de calibração

```
1. juntar amostras reais      →  10 por tipo de guia
2. python -m docauto diagnosticar --entrada <amostras> --texto <saida>
3. ler o que faltou            →  termo ausente? código não ancorado? sem texto?
4. ajustar config/templates/<tipo>.yaml
5. repetir 2 e 3 até acertar os 10
6. só então usar em produção
```

## Passo 1 — Juntar as amostras

Uma pasta por tipo, com **10 documentos reais de emissores diferentes**:

```
C:\amostras\DAS\
C:\amostras\PIS\
C:\amostras\COFINS\
C:\amostras\IR\
C:\amostras\CSLL\
```

Dez é o número mínimo que revela variação de formato. Com três você calibra
para um emissor só e descobre o problema em produção.

## Passo 2 — Rodar o diagnóstico

```bat
python -m docauto diagnosticar --entrada C:\amostras\PIS --texto C:\amostras\_texto
```

Saída, por documento:

```
==============================================================================
darf_cofins.pdf
  texto......: NATIVO, 412 caracteres
  cnpj.......: 04.252.011/0001-10
  competência: 2026-08 (APURACAO)
  valor......: 987.65   vencimento: 2026-09-25
  códigos....: ['2172']  -> ['COFINS']
  razões.....: ['MODELO SERVICOS DE TECNOLOGIA LTDA']
  templates:
    COFINS    90/ 90 (100%)
       . termo principal 'COFINS' (+40)
       . termo principal 'CONTRIBUICAO PARA O FINANCIAMENTO DA SEGURIDADE SOCIAL' (+45)
       . 4 termo(s) secundário(s) (+15)
       . código de receita 2172 = COFINS (+30)
    DAS        0/ 60 (  0%)
       . código 2172 pertence a COFINS (-35)
       - principais ausentes: DOCUMENTO DE ARRECADACAO DO SIMPLES NACIONAL, ...
  => tipo COFINS/FATURAMENTO_CUMULATIVO   empresa: 0002 (CNPJ)
```

`--texto` salva o **texto normalizado** de cada documento numa pasta. É de lá
que saem as palavras-chave: você lê o que o robô lê, não o que o PDF aparenta.

## Passo 3 — Diagnóstico por sintoma

| O que você vê | Significa | O que ajustar |
|---|---|---|
| `texto: VAZIO, 0 caracteres` | PDF é imagem | OCR (Fase 2). **Não adianta mexer no template** — não há texto para casar |
| `códigos....: -` numa guia que tem código | O código existe mas não está **ancorado** num rótulo conhecido | Abra o `--texto` e veja como o rótulo aparece; acrescente a variação em `ROTULOS` de `extrair_codigos_receita` (é o único ajuste que hoje exige mexer no código — vale um chamado se for recorrente) |
| `principais ausentes: ...` e score baixo | O emissor escreve o tributo de outro jeito | Acrescente o termo real em `palavras_chave_principais` |
| Dois templates empatados | Guia cita os dois tributos e não há código legível | Acrescente **anti-termos**, ou aceite que este formato vai para validação (às vezes é o certo) |
| `competência: - (NAO_ENCONTRADA)` | O rótulo de competência do emissor é diferente | Acrescente a variação em `ROTULOS_COMPETENCIA`/`ROTULOS_APURACAO` |
| `cnpj: -` mas o PDF tem CNPJ | Erro de leitura (OCR) ou máscara incomum | Confira no `--texto`; se o dígito veio errado, é qualidade de digitalização |
| `razões: -` | Nome não reconhecido | Só importa quando **não há CNPJ**. Use `APELIDOS` no cadastro |
| Score certo mas subtipo vazio no IR | Sem código de receita legível | É intencional: IRPJ e IRRF não se separam sem o código |

## Passo 4 — O que mexer em cada caso

```yaml
# Termo que IDENTIFICA o tributo. Peso alto (35-45).
palavras_chave_principais:
  - termo: "PIS/PASEP"
    peso: 40
  - termo: "PIS"
    peso: 28
    caixa_alta: true      # exige maiúscula no documento original

# Reforço de contexto. +5 cada, teto +15. Não identificam sozinhas.
palavras_chave_secundarias:
  - "PERIODO DE APURACAO"

# Termo de OUTRO tributo. Puxa o score para baixo e ajuda no desempate.
anti_termos:
  - "COFINS"
```

**Regras que evitam estrago:**

1. **Termo curto exige `caixa_alta: true`.** "DAS", "PIS", "IR" e "ME" aparecem
   como palavra comum em texto em português. Sem a exigência de maiúscula,
   *todo* documento "contém DAS".
2. **Não suba peso para resolver empate.** Empate significa que a evidência é
   ambígua de verdade; a saída certa é anti-termo ou código, não peso maior.
3. **Não crie template novo para variação do mesmo tributo.** PIS faturamento e
   PIS folha são o mesmo template, separados por **subtipo** via código.
4. **Mexeu no template, rode os testes:** `python -m unittest discover -s tests -t .`
   Eles protegem os casos que já funcionam (DAS vs. tributos internos,
   PIS vs. COFINS, vencimento vs. competência).

## Passo 5 — Fechar o ciclo

Um tipo está calibrado quando, nas 10 amostras:

- **nenhuma** foi classificada como tributo errado (isto é inegociável);
- pelo menos 8 saíram com o tipo certo e competência certa;
- as que caíram em validação caíram por motivo **explicável** (guia mista de
  verdade, PDF sem texto, documento fora do escopo).

Registre no próprio template, no campo `criterios_validacao_manual`, o que você
aprendeu — daqui a seis meses ninguém lembra por que aquele peso é 28.

## Ordem sugerida

DAS primeiro (é o de maior volume e o mais fácil de acertar), depois PIS e
COFINS juntos — eles se calibram em par, porque o anti-termo de um é o principal
do outro. IR e CSLL por último, que dependem mais do código de receita.

Antes de abrir para a carteira toda, confira `config/codigos_receita.yaml`
contra a tabela oficial da RFB e mude o status para `CONFERIDA`.
