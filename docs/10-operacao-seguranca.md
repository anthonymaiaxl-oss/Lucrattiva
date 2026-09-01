# 10 — Operação, segurança e indicadores

## Regras de segurança implementadas no código

| Regra | Como está garantida |
|---|---|
| Não sobrescrever documento | `archive.py` nunca escreve por cima: arquivo diferente ganha sufixo `_02`; arquivo idêntico (hash SHA-256) é marcado `DUPLICADO` e ignorado. |
| Não apagar o original | `modo_original: "copiar"` é o padrão. `mover` só depois de 60 dias limpos. Nada é apagado, em nenhum modo. |
| Não arquivar em empresa com CNPJ não validado | Dígito verificador conferido; CNPJ inválido não identifica ninguém. CNPJ válido fora do cadastro vira pendência. |
| Vencimento não vira competência | Janela de leitura cortada antes de rótulos de vencimento; coberto por teste automatizado. |
| Não inventar classificação | Empate a menos de 15 pontos = `NECESSITA_VALIDACAO`. Score mínimo de 35. Código 5952 sempre para validação. |
| Na dúvida, pendência | Qualquer trava manda para `PENDENTES_VALIDACAO`, mesmo com score 100. |

## Rotina

**Diária (20 min, dono definido):** rodar a fila de pendências por motivo,
começando pelos mais frequentes; resolver a **causa** (cadastro, template) e
devolver o arquivo para a entrada.

**Semanal (15 min):** `python -m docauto relatorio`. Olhar dois números —
% automático (tem que subir) e erros de destino (tem que ser zero). Conferir por
amostragem 5 documentos arquivados como `AUTOMATICO`.

**Mensal (1 h):** recalibrar com os documentos do mês (`docs/07`); revisar a
tabela de códigos; conferir o cadastro contra a lista de clientes do Domínio.

## Backup — pré-requisito, não opcional

Antes de ligar `mover`:

- Cópia diária da pasta `CLIENTES` (o servidor já deve ter; confira que **restaura**, não só que roda).
- `data/registro/` junto do backup — é a auditoria do que a automação fez.
- `config/` versionado em Git. É o cérebro do processo; perder templates
  calibrados é perder meses de ajuste.
- Teste de restauração a cada trimestre. Backup não testado não é backup.

## LGPD e sigilo

- Documentos fiscais contêm dado de terceiro. A pasta `CLIENTES` deve ter
  permissão por grupo (fiscal vê fiscal, DP vê DP), não "todo mundo".
- `data/empresas.csv` **não vai para o repositório** — já está no `.gitignore`.
  Só o `empresas.exemplo.csv`, com CNPJs fictícios, é versionado.
- `registro.csv` guarda CNPJ e razão social: trate com o mesmo cuidado da pasta
  de clientes.
- Se um dia entrar IA em nuvem para classificação (Fase 2+), decida
  explicitamente o que pode sair do servidor. O MVP não envia nada para lugar
  nenhum — roda 100% local.

## Indicadores

| Indicador | Como medir | Meta mês 1 | Meta mês 6 |
|---|---|---|---|
| **Erro de destino** (documento na empresa/competência errada) | Conferência por amostragem | **0** | **0** |
| % automático | `relatorio` | 60–70% | 85–90% |
| % pendente | `relatorio` | 30–40% | 10–15% |
| Tempo por documento (manual) | Cronômetro, 10 documentos | — | < 30 s |
| Fila parada > 2 dias | Data do arquivo em PENDENTES | 0 | 0 |

O primeiro indicador é o único inegociável. Os outros são otimização.

## Suporte e continuidade

- Todo o comportamento do negócio está em `config/` (YAML e CSV), em português,
  editável por quem entende de contabilidade — não por quem entende de Python.
- `python -m unittest discover -s tests -t .` roda a suíte de testes: 30 testes
  cobrindo dígito verificador de CNPJ, prioridade de competência, PIS × COFINS,
  supressão do DAS, sanitização Windows e não sobrescrita. Rode depois de
  qualquer alteração em template ou código.
- O registro em `detalhado.jsonl` guarda, por documento, todos os motivos da
  decisão — dá para reconstruir **por que** a automação decidiu o que decidiu,
  meses depois.
