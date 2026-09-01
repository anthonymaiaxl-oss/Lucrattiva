# 16 — Enxergar o que já está no Onvio (sem senha)

Não é possível me dar acesso à sua conta do Onvio, e não é questão de
permissão: esta sessão roda num contêiner temporário na nuvem, sem rota até a
sua rede, e é descartada ao fim. Além disso, credencial do Onvio dá acesso aos
dados fiscais dos seus clientes — não deve ser compartilhada com ninguém, nem
comigo.

**Mas o objetivo é atingível por outro caminho:** o Onvio exporta as listas que
importam. Você exporta, eu leio, e o cruzamento — que é o trabalho de verdade —
está automatizado.

## O que exportar (10 minutos)

| Exportação | Colunas que importam | Para quê |
|---|---|---|
| **Empresas / clientes** | código, razão social, nome fantasia, CNPJ, regime, situação | Montar ou conferir `data/empresas.csv` |
| **Tarefas / obrigações** | empresa, obrigação, competência, setor | Saber quais obrigações existem — é o que o Express procura ao vincular |

CSV ou XLSX, colunas em qualquer ordem e com qualquer nome razoável: o leitor
reconhece variações (`Razão Social`, `Nome Empresarial`, `Cliente`; `CNPJ`,
`CPF/CNPJ`; `Obrigação`, `Tarefa`, `Serviço`). Salve em `data/onvio/`.

## Montar o cadastro a partir do Onvio

Se o cadastro ainda não existe, não digite nada à mão:

```bat
python -m docauto onvio-conferir --empresas data\onvio\empresas.csv ^
                                 --gerar-cadastro data\empresas.csv
```

Gera IDs sequenciais, traz o **código do Domínio** (que é o que permite conciliar
depois), deduz o `NOME_CURTO` e marca como inativa quem está baixada. Confira
`NOME_CURTO` e `REGIME_TRIBUTARIO` antes de usar — e lembre: **ID não muda mais**.

## Conferir os dois lados

```bat
python -m docauto onvio-conferir --empresas data\onvio\empresas.csv ^
                                 --tarefas  data\onvio\tarefas.csv
```

```
empresas: 3 no Onvio, 3 no cadastro, 2 conferem

2 divergência(s):
  [FALTA_NO_CADASTRO       ] 11.444.777/0001-61  NOVA EMPRESA ... LTDA
      -> acrescentar em data/empresas.csv — sem isso todo documento dessa empresa vira pendência
  [FALTA_NO_ONVIO          ] 34.028.316/0001-03  TESTE INDUSTRIA E COMERCIO S.A.
      -> empresa ativa no cadastro e ausente da exportação — o Express nunca vai achar tarefa para ela

tarefas/obrigações: 5 linha(s)
  DAS            1 obrigação(ões) no Onvio
  PIS            1
  COFINS         1

templates SEM obrigação correspondente no Onvio:
  CSLL
  IR
  -> documento desse tipo vai ser classificado certo, mas o Express devolve 'tarefa não encontrada'

obrigações do Onvio SEM template (2):
  Envio da EFD Contribuicoes
  Folha de pagamento
  -> são candidatas a template novo (docs/13), na ordem de volume
```

## O que cada divergência significa

| Divergência | Consequência prática |
|---|---|
| `FALTA_NO_CADASTRO` | Todo documento dessa empresa vira pendência. É a causa nº 1 de fila grande na primeira semana |
| `FALTA_NO_ONVIO` | A automação arquiva certo, mas o Express nunca acha tarefa |
| `RAZAO_DIFERENTE` | Identificação por nome (nível 2) falha. Resolva com `APELIDOS` |
| `CODIGO_DOMINIO_DIFERENTE` | Conciliação futura com o Domínio quebra |
| `CNPJ_INVALIDO_NO_ONVIO` | Erro no cadastro dentro do próprio Onvio — corrigir lá |
| `templates_sem_tarefa` | O Express vai devolver "não encontrada" para esse tributo. Ou a obrigação não está cadastrada, ou o escritório não a acompanha por tarefa |
| `sem_template` | Obrigação que o escritório acompanha e a automação ainda não classifica. Fila de trabalho para novos templates, em ordem de volume |

**Rode isto antes da primeira semana de operação.** As duas primeiras
divergências explicam a maior parte das pendências que apareceriam depois — e
custam minutos para corrigir agora.

## Se quiser mesmo alguém olhando por dentro

1. **Suporte da Thomson Reuters**, com acesso remoto agendado — é do produto
   deles e tem cobertura contratual.
2. **Chamada de tela**: você compartilha a tela e opera; eu digo o que olhar e
   por quê. Você mantém o controle da conta, sem credencial trocando de mãos.
