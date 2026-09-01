# 03 — Templates de documento

Cada tipo de documento tem um arquivo em `config/templates/`. O contador edita;
ninguém precisa mexer em código. Toda alteração de template deve ser testada com
`python -m docauto processar --dry-run` antes de valer para valer.

## Estrutura de um template

| Campo | Para que serve |
|---|---|
| `id` | Nome curto usado no nome do arquivo e nas pastas (DAS, PIS, COFINS, IR, CSLL) |
| `nome` | Nome por extenso, para relatório |
| `setor` / `grupo` | Onde o documento será arquivado (FISCAL / GUIAS) |
| `precedencia` | Desempate quando dois templates empatam em pontos |
| `suprime` | Tributos que este documento **contém** (só o DAS usa) |
| `palavras_chave_principais` | Termo + peso. `caixa_alta: true` exige que o termo esteja em maiúsculas no documento original |
| `palavras_chave_secundarias` | Reforço, +5 cada, teto +15 |
| `anti_termos` | Termos de OUTRO tributo. Puxam o score para baixo e ajudam a detectar guia mista |
| `campos_obrigatorios` | Sem eles o documento vai para pendências, mesmo com score alto |
| `campos_opcionais` | Somam confiança, não travam |
| `criterios_confiavel` / `criterios_validacao_manual` | Documentação para o humano — o que aceitar e o que conferir |

Os **códigos de receita não ficam no template**: ficam em
`config/codigos_receita.yaml`, em um lugar só. Assim, quando a Receita muda um
código, você corrige uma linha e todos os templates acompanham.

## A. DAS — `config/templates/das.yaml`

- **Palavras principais:** "DOCUMENTO DE ARRECADAÇÃO DO SIMPLES NACIONAL" (45),
  "SIMPLES NACIONAL" (35), "PGDAS-D" (35), "DAS" em caixa alta (25).
- **Secundárias:** COMPOSIÇÃO DO DOCUMENTO DE ARRECADAÇÃO, PERÍODO DE APURAÇÃO,
  NÚMERO DO DOCUMENTO, CNPJ MATRIZ, RECEITA BRUTA, CPP, PAGAR ATÉ.
- **Códigos:** não se aplica (o DAS não usa código de receita do DARF).
- **Obrigatórios:** CNPJ, competência. **Opcionais:** valor, vencimento, razão social, número do documento.
- **Confiável quando:** CNPJ válido e cadastrado + termo do Simples Nacional +
  competência vinda de "Período de Apuração" ou "Competência".
- **Validação manual quando:** sem CNPJ; sem competência; documento com marcas de
  DARF junto de Simples Nacional (guia avulsa/parcelamento); sem valor total.

> **A regra mais importante deste template:** o DAS lista IRPJ, CSLL, COFINS,
> PIS, CPP e ICMS na composição. Sem a regra `suprime`, **todo DAS seria
> classificado como ambíguo**. Por isso o DAS suprime esses tributos quando seus
> próprios marcadores aparecem com força. É a diferença entre a automação
> funcionar e viver empacada.

## B. PIS — `config/templates/pis.yaml`

- **Principais:** PIS/PASEP, PIS-PASEP, PROGRAMA DE INTEGRAÇÃO SOCIAL,
  CONTRIBUIÇÃO PARA O PIS (40); "PIS" em caixa alta (28).
- **Secundárias:** DARF, DOCUMENTO DE ARRECADAÇÃO DE RECEITAS FEDERAIS,
  CÓDIGO DA RECEITA, PERÍODO DE APURAÇÃO, FATURAMENTO, NÃO CUMULATIVO, FOLHA DE SALÁRIOS.
- **Códigos (na tabela):** 8109 faturamento, 6912 não cumulativo, 8301 folha, 5979 retido.
- **Anti-termos:** COFINS, CONTRIBUIÇÃO SOCIAL SOBRE O LUCRO.
- **Obrigatórios:** CNPJ, competência, valor. **Opcionais:** vencimento, código, razão social.
- **Confiável quando:** código mapeado como PIS **ou** termo principal isolado, com CNPJ cadastrado e competência de rótulo.
- **Manual quando:** PIS e COFINS com força parecida e sem código legível; código 5952; código fora da tabela; competência apenas dedutível do vencimento.

## C. COFINS — `config/templates/cofins.yaml`

- **Principais:** CONTRIBUIÇÃO PARA O FINANCIAMENTO DA SEGURIDADE SOCIAL (45), COFINS (40).
- **Secundárias:** as mesmas do PIS + NÃO CUMULATIVA.
- **Códigos:** 2172 faturamento, 5856 não cumulativa, 5960 retida.
- **Anti-termos:** PIS/PASEP, PROGRAMA DE INTEGRAÇÃO SOCIAL, CSLL.
- **Confiável / manual:** mesmos critérios do PIS, invertidos.

### Como PIS e COFINS deixam de se confundir

Três camadas, nesta ordem:

1. **Código de receita ancorado** — só conta código de 4 dígitos que apareça logo
   após "CÓDIGO DA RECEITA" ou equivalente. Número solto de 4 dígitos (ano, CEP,
   agência) é ignorado de propósito.
2. **Anti-termos** — o COFINS citado numa guia de PIS derruba pontos do PIS e vice-versa.
3. **Margem de desempate** — se os dois ficarem a menos de 15 pontos um do outro,
   o resultado é `NECESSITA_VALIDACAO`. Nunca se escolhe "o mais provável".

O código 5952 (CSLL/COFINS/PIS retidos em conjunto) é tratado como
`RETENCAO_CONJUNTA` e vai **sempre** para validação: uma guia só, três tributos —
não existe resposta única, e fingir que existe é criar erro.

## D. IR — `config/templates/ir.yaml`

- **Principais:** IMPOSTO SOBRE A RENDA / IMPOSTO DE RENDA (40), IRPJ e IRRF em
  caixa alta (40), "IR" em caixa alta (18 — peso baixo de propósito, é sigla curta demais).
- **Códigos:** IRPJ 2089 presumido, 2362 estimativa, 0220, 5625 arbitrado;
  IRRF 0561 assalariado, 0588 sem vínculo, 1708 serviços PJ, 3208 aluguéis.
- **`exige_subtipo: true`** — sem código de receita legível, não dá para separar
  IRPJ de IRRF, e os dois têm responsável e destino diferentes. Sem subtipo, vai
  para validação mesmo com score alto. Este é o único template com essa exigência.
- **Obrigatórios:** CNPJ, competência, valor, código de receita.
- **Manual quando:** sem código legível; código fora da tabela; IRPJ e CSLL na
  mesma guia; informe de rendimentos (não é guia — vai para DECLARACOES, não GUIAS).

## E. CSLL — `config/templates/csll.yaml`

- **Principais:** CONTRIBUIÇÃO SOCIAL SOBRE O LUCRO LÍQUIDO (45), sem "LÍQUIDO" (42), CSLL em caixa alta (40).
- **Códigos:** 2372 presumido, 2484 estimativa, 6012 lucro real trimestral, 5987 retida.
- **Anti-termos:** IMPOSTO SOBRE A RENDA, COFINS, PIS/PASEP.
- **Manual quando:** IRPJ e CSLL na mesma guia sem código legível (é o erro mais
  comum na prática); código 5952; apuração trimestral cuja competência precisa ser
  confirmada (03, 06, 09, 12).

## ⚠️ Antes de ligar o arquivamento automático

`config/codigos_receita.yaml` está marcado como **`NAO_CONFERIDA`**. Os códigos
vieram de uso corrente de mercado e **não foram conferidos contra a tabela
oficial da Receita Federal**. Enquanto estiver assim, todo documento classificado
por código recebe o aviso `TABELA_CODIGOS_NAO_CONFERIDA` no registro — de
propósito, para não deixar você esquecer.

Passo obrigatório: abrir a tabela de códigos de receita vigente, conferir
**apenas os códigos que a sua carteira usa**, apagar o resto (menos código =
menos chance de erro), preencher `conferido_em` / `conferido_por` e mudar o
status para `CONFERIDA`.

## Criando um novo template (ex.: INSS, ICMS, FGTS)

1. Copie `config/templates/csll.yaml` para `config/templates/inss.yaml`.
2. Troque `id`, `nome`, palavras-chave e anti-termos.
3. Se o tributo tiver código próprio, acrescente em `codigos_receita.yaml`.
4. Junte 10 documentos reais desse tipo numa pasta e rode
   `python -m docauto processar --entrada <pasta> --dry-run`.
5. Ajuste pesos até os 10 saírem certos. Só então use para valer.
