# 05 — Cadastro central de empresas

O cadastro é **a peça mais importante do projeto**. Um CNPJ errado aqui manda
documento para a empresa errada, e o erro só aparece na conferência. Corrigir o
cadastro é mais barato do que qualquer ajuste no código.

Arquivo: `data/empresas.csv` (modelo em `data/empresas.exemplo.csv`).

## Colunas

| Coluna | Obrigatória | Descrição |
|---|---|---|
| `ID_EMPRESA` | ✅ | Código interno de 4 dígitos (`0001`). Nunca muda, nunca é reaproveitado, mesmo se o cliente sair. É o nome da pasta e a chave do registro. |
| `CODIGO_DOMINIO` | recomendada | Código da empresa **dentro do Domínio**. Não é usado no MVP, mas é o que vai permitir conciliar a automação com o Domínio na Fase 3. Preencher desde já custa 10 segundos por cliente e economiza um retrabalho inteiro depois. |
| `RAZAO_SOCIAL` | ✅ | Exatamente como no cartão CNPJ. Vira o nome da pasta. |
| `NOME_FANTASIA` | | Usado no nível 3 de identificação. |
| `NOME_CURTO` | ✅ | Até 24 caracteres, sem espaço, para o nome do arquivo (`EXEMPLO`). Se ficar vazio, o sistema usa o fantasia ou a razão. |
| `CNPJ` | ✅ | Com ou sem máscara. **O dígito verificador é conferido**: CNPJ inválido barra a empresa na validação. |
| `REGIME_TRIBUTARIO` | ✅ | SIMPLES NACIONAL / LUCRO PRESUMIDO / LUCRO REAL / MEI. Serve para conferência de coerência (ver abaixo). |
| `CAMINHO_BASE` | | Só para empresa que já tem pasta fora do padrão. Vazio = o sistema monta `base_clientes/ID - RAZAO`. |
| `SETOR_PADRAO` | | FISCAL no MVP. |
| `ATIVA` | ✅ | SIM/NÃO. Empresa inativa **não recebe arquivo automático** — o documento vai para pendências com o motivo explícito. |
| `APELIDOS` | | Variações de escrita separadas por `\|`. É aqui que se resolve o cliente que assina de três jeitos diferentes. |

## Por que CSV no MVP

| Opção | Veredito |
|---|---|
| **CSV no servidor** ✅ | Abre no Excel, todo mundo sabe editar, versiona no Git, não corrompe, não depende de licença nem de internet. **Comece por aqui.** |
| Excel (.xlsx) | Mesma coisa, com risco de célula formatada como número comendo o zero à esquerda do ID e do CNPJ. Se usar, formate as colunas como TEXTO. |
| Google Sheets | Bom para preencher a muitas mãos, ruim como fonte de verdade de um processo que roda no servidor local (depende de internet e de credencial). Use para montar e **exporte para CSV**. |
| SQLite | Troque quando: passar de ~300 empresas, ou duas pessoas precisarem editar ao mesmo tempo, ou você quiser histórico de alteração. A migração é direta — o resto do código não muda. |
| Postgres/MySQL | Só quando a Central Inteligente tiver interface web própria. Não antes. |

## Conferência antes de rodar

```
python -m docauto validar
```

Acusa: CNPJ vazio, CNPJ com dígito verificador inválido, CNPJ duplicado entre
duas empresas, razão social vazia. **Nenhum documento deve ser processado
enquanto essa lista não estiver zerada.**

## Uso do regime tributário (coerência)

O regime não classifica documento, mas denuncia erro:

- DAS chegando para empresa marcada como LUCRO PRESUMIDO → algo está errado
  (ou o cadastro está desatualizado, ou o documento é de outro cliente).
- DARF de IRPJ estimativa para empresa do SIMPLES → idem.

Sugestão de evolução (Fase 2): transformar essas duas checagens em trava de
confiança. No MVP, elas aparecem no relatório mensal e são olhadas por gente.
